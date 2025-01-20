"Websocket Stream"

import typing as t
import base64
import os
from asyncio import (
    WriteTransport,
    Protocol,
    StreamReader,
    ensure_future,
)
from loguru import logger

from xypro.context import StreamABC

BUFF_SIZE = 32768


class WebsocketStreamError(Exception):
    "Websocket stream error."


OPCODE_CONT = 0x2
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


class WebsocketOutboundProtocol(Protocol, StreamABC):
    "Websocket outbound protocol."

    # data length threshold.
    LENGTH_7 = 0x7E
    LENGTH_16 = 1 << 16
    LENGTH_63 = 1 << 63

    handshaked = False
    transport: WriteTransport

    _buffer: StreamReader
    _closed = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._buffer = StreamReader()

    def _handshake(self):
        path = self.context.config.ws_opts.path
        sec_ws_key = base64.b64encode(os.urandom(16)).decode()
        headers = {
            "Host": "localhost",
            "User-Agent": "Safewoo",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": sec_ws_key,
            "Sec-WebSocket-Version": "13",
            "Upgrade": "websocket",
        }
        header_str = "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
        raw_http = f"GET {path} HTTP/1.1\r\n{header_str}\r\n\r\n"
        logger.debug(raw_http)
        self.transport.write(raw_http.encode())

    def _upgrade(self, data: bytes):
        if self.handshaked:
            raise WebsocketStreamError("Already handshaked")

        try:
            ws_resp = data.decode("utf-8")
        except UnicodeDecodeError as err:
            raise WebsocketStreamError("Invalid websocket response") from err
        logger.debug(ws_resp)
        if "connection: upgrade" not in ws_resp.lower():
            raise WebsocketStreamError("Invalid websocket response")

        self.handshaked = True
        self.context.outbound_connected.set_result(1)

    async def _parse_frame(self):
        "read a frame from the buffer."
        first, second = await self._buffer.readexactly(2)
        payload_length = second & 0x7F
        if payload_length == 126:
            # Read the next 2 bytes for the extended payload length
            extended_payload_length = await self._buffer.readexactly(2)
            payload_length = int.from_bytes(extended_payload_length, byteorder="big")
        elif payload_length == 127:
            # Read the next 8 bytes for the extended payload length
            extended_payload_length = await self._buffer.readexactly(8)
            payload_length = int.from_bytes(extended_payload_length, byteorder="big")

        fin = (first & 0x80) >> 7
        opcode = first & 0x0F
        payload_data = await self._buffer.readexactly(payload_length)
        return fin, opcode, payload_data

    def _create_frame(self, payload: bytes, opcode=OPCODE_BINARY, fin=1) -> bytes:
        # Create the first byte of the frame
        first_byte = (fin << 7) | opcode

        # Determine the payload length and create the second byte
        payload_length = len(payload)
        if payload_length <= 125:
            second_byte = 0x80 | payload_length  # Set the mask bit to 1
            extended_payload_length = b""
        elif payload_length <= 65535:
            second_byte = 0x80 | 126  # Set the mask bit to 1
            extended_payload_length = payload_length.to_bytes(2, byteorder="big")
        else:
            second_byte = 0x80 | 127  # Set the mask bit to 1
            extended_payload_length = payload_length.to_bytes(8, byteorder="big")

        # Create the frame header
        frame_header = bytes([first_byte, second_byte]) + extended_payload_length

        # Generate a masking key
        masking_key = os.urandom(4)

        # Mask the payload
        masked_payload = bytearray(payload)
        for i in range(payload_length):
            masked_payload[i] ^= masking_key[i % 4]

        # Combine the frame header, masking key, and masked payload
        frame = frame_header + masking_key + masked_payload

        return frame

    async def _process_buffer(self):
        while self._closed is False:
            _fin, opcode, payload = await self._parse_frame()
            if opcode == OPCODE_BINARY:
                proto_data = self.context.adapter.inbound_process(payload)
                if self.context.source:
                    self.context.inbound.write(proto_data, self.context.source)
                else:
                    self.context.inbound.write(proto_data)
            elif opcode == OPCODE_TEXT:
                raise NotImplementedError
            elif opcode == OPCODE_CLOSE:
                self.context.close()
                break
            elif opcode == OPCODE_PING:
                self.write(b"", opcode=OPCODE_PONG)
            else:
                ...
        logger.debug("Process buffer finished")

    def connection_made(self, transport: WriteTransport):
        self.transport = transport
        self._handshake()
        ensure_future(self._process_buffer())

    def data_received(self, data: bytes):
        if not self.handshaked:
            self._upgrade(data)
            return
        self._buffer.feed_data(data)

    def connection_lost(self, exc: t.Optional[Exception]):
        logger.debug("Connection lost")
        self.close()

    def write(self, data: bytes, fin=1, opcode=OPCODE_BINARY):
        frame_data = self._create_frame(data, opcode, fin)
        self.transport.write(frame_data)

    def close(self):
        self._closed = True
        if self.transport:
            self.transport.close()

        logger.debug("Websocket outbound closed")
