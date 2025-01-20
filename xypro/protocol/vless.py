""" 
Vless protocol implementation.
"""

import struct
import socket
from asyncio import StreamReader
from dataclasses import dataclass

from loguru import logger

from xypro.context import ProxyContext, AdapterABC
from xypro.types import AtypAddress

VLESS_VER = 0
BUFF_SIZE = 65535
UDP_MAX_LEN = 65507


class VlessOutboundErrorMsg:

    UNKNOW_ERROR = 0x00
    CONNECT_ERROR = 0x01
    CONNECT_TIMEOUT = 0x02
    INVALID_VERSION = 0x03
    INVALID_NETWORK = 0x04
    INVALID_STREAM = 0x05


class VlessOutboundException(Exception):
    pass


class VlessCommand:
    """Vless command."""

    TCP = 0x01
    UDP = 0x02
    MUX = 0x03


@dataclass
class VlessRequest:
    """The request structure of VLESS.
    | 1 byte           | 16 bytes        | 1 byte                          | M bytes                         | 1 byte      | 2 bytes | 1 byte       | S bytes | X bytes      |
    | ---------------- | --------------- | ------------------------------- | ------------------------------- | ----------- | ------- | ------------ | ------- | ------------ |
    | Protocol Version | Equivalent UUID | Additional Information Length M | Additional Information ProtoBuf | Instruction | Port    | Address Type | Address | request Data |
    VLESS had the aforementioned structure as early as the second alpha test version (ALPHA 2), with BETA being the fifth test version.
    """

    ver: int
    uuid: str
    ext_len: int
    ext: bytes
    cmd: int
    port: int
    atyp: int
    addr: bytes
    payload: bytes | None = None

    def pack_head(self: "VlessRequest") -> bytes:
        "Pack the request head into bytes."
        fmt = f"!B16sB{self.ext_len}sBHB{len(self.addr)}s"
        uuid_hex = bytes.fromhex(self.uuid.replace("-", ""))
        bs = struct.pack(
            fmt,
            self.ver,
            uuid_hex,
            self.ext_len,
            self.ext,
            self.cmd,
            self.port,
            self.atyp,
            self.addr,
        )
        return bs

    def pack(self: "VlessRequest") -> bytes:
        "Pack the request into bytes."
        head = self.pack_head()
        return head + self.payload

    def __str__(self) -> str:
        return f"VlessRequest(ver={self.ver}, uuid={self.uuid}, ext_len={self.ext_len}, ext={self.ext}, cmd={self.cmd}, port={self.port}, adty={self.atyp}, addr={socket.inet_ntoa(self.addr)})"


@dataclass
class VlessResponse:
    """The response structure of VLESS.
    | 1 Byte                                        | 1 Byte                             | N Bytes                            | Y Bytes       |
    | --------------------------------------------- | ---------------------------------- | ---------------------------------- | ------------- |
    | Protocol Version, consistent with the request | Length of additional information N | Additional information in ProtoBuf | Response data |
    """

    ver: int
    ext_len: int
    ext: bytes
    payload: bytes | None = None


class Adapter(AdapterABC):
    """Vless adapter"""

    context: ProxyContext

    head_received = False
    head_sent = False
    uuid: str
    reader: StreamReader

    def __init__(self, context: ProxyContext):
        self.reader = StreamReader()
        self.context = context

    def inbound_process(self, data: bytes) -> bytes:
        "Handle the incoming stream, decap a vless head if not received"

        if self.head_received:
            return data

        if len(data) < 2:
            logger.error("Invalid data length")
            return

        ver, ext_len = data[:2]
        if ver != VLESS_VER:
            raise VlessOutboundException(VlessOutboundErrorMsg.INVALID_VERSION)

        if len(data) < 2 + ext_len:
            raise VlessOutboundException(VlessOutboundErrorMsg.INVALID_STREAM)

        payload = data[2 + ext_len :]
        self.head_received = True
        return payload

    def outbound_process(
        self, data: bytes, udp=False, dst: AtypAddress | None = None
    ) -> bytes:
        "Handle the outgoing stream, wrap a vless head if not sent"

        if self.head_sent:
            return data

        if not self.context.destination:
            raise ValueError("Missing destination")

        if udp:
            if not dst:
                raise ValueError("UDP outbound requires `dst`")
            cmd = VlessCommand.UDP
            payload_len = len(data)
            data = struct.pack("!H", payload_len) + data
        else:
            cmd = VlessCommand.TCP
            dst = self.context.destination

        atyp, addr, port = dst

        head = VlessRequest(
            ver=VLESS_VER,
            uuid=self.context.config.uuid,
            ext_len=0,
            ext=b"",
            cmd=cmd,
            port=port,
            atyp=atyp,
            addr=addr,
        ).pack_head()

        data = head + data
        self.head_sent = True
        return data
