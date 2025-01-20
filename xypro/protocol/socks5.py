""" 
Sock5 inbound protocol implementation
"""

import struct
import asyncio
import socket
import typing as t
from dataclasses import dataclass
from loguru import logger
from xypro.context import ProxyContext, StreamABC
from xypro.config import ProxyConfig
from xypro.outbound import create_outbound_connection
from xypro import types

BUFF_SIZE = 65535

RetAddress = t.Tuple[str, int]
ProxyNetworkAddress = t.Tuple[int, bytes, int]


class Socks5ExceptionMsg:
    "Socks5 exception message"
    HANDSHAKE_FAILED = 0x01
    INVALID_ATYP = 0x02
    PACK_ERROR = 0x03
    ENCAPSULATION_ERROR = 0x04


class Socks5Exception(Exception):
    "Socks5 exception"
    pass


class Socks5Msg:
    "Socks5 message"
    VER = 0x05
    CMD_CONNECT = 0x01
    CMD_BIND = 0x02
    CMD_UDP = 0x03
    RSV = 0x00
    ATYP_IPV4 = 0x01
    ATYP_DOMAIN = 0x03
    ATYP_IPV6 = 0x04
    SUCCESS = 0x00
    COMMAND_NOT_SUPPORTED = 0x07


# class Socks5Error:
#     GENERAL_SOCKS_SERVER_FAILURE = 1
#     CONNECTION_NOT_ALLOWED_BY_RULESET = 2
#     NETWORK_UNREACHABLE = 3
#     HOST_UNREACHABLE = 4
#     CONNECTION_REFUSED = 5
#     TTL_EXPIRED = 6
#     COMMAND_NOT_SUPPORTED = 7
#     ADDRESS_TYPE_NOT_SUPPORTED = 8


@dataclass
class Socks5Replies:
    ver: int
    reply_code: t.Literal[
        0, 1, 2, 3, 4, 5, 6, 7, 8
    ]  # 0x00: succeeded, 0x01: general SOCKS server failure, 0x02: connection not allowed by ruleset, 0x03: Network unreachable, 0x04: Host unreachable, 0x05: Connection refused, 0x06: TTL expired, 0x07: Command not supported, 0x08: Address type not supported
    reserved: int
    atyp: t.Literal[
        1, 3, 4
    ]  # 0x01: IPv4 address, 0x03: Domain name, 0x04: IPv6 address
    bind_addr: bytes
    bind_port: int

    def pack(self) -> bytes:

        if self.atyp == Socks5Msg.ATYP_IPV4:
            _format = "!BBBB4sH"
        elif self.atyp == Socks5Msg.ATYP_DOMAIN:
            _format = f"!BBBBb{len(self.bind_addr)}sH"
        elif self.atyp == Socks5Msg.ATYP_IPV6:
            _format = "!BBBB16sH"
        else:
            raise Socks5Exception(Socks5ExceptionMsg.INVALID_ATYP)

        return struct.pack(
            _format,
            self.ver,
            self.reply_code,
            self.reserved,
            self.atyp,
            self.bind_addr,
            self.bind_port,
        )


@dataclass
class UDPEncapsulation:
    reserved: int  # Reserved 0x0000, 2 bytes
    fragment: int  # 1 byte
    atyp: int  # 1 byte
    dst_addr: bytes  # 4 bytes for IPv4, 16 bytes for IPv6
    dst_port: int  # 2 bytes
    payload: bytes | None  # payload

    def pack(self) -> bytes:
        "Pack the UDP encapsulation"
        if self.atyp == Socks5Msg.ATYP_IPV4:
            fmt = "!2BBB4sH"
        elif self.atyp == Socks5Msg.ATYP_DOMAIN:
            fmt = f"!2BBBb{len(self.dst_addr)}sH"
        elif self.atyp == Socks5Msg.ATYP_IPV6:
            fmt = "!2BBB16sH"
        else:
            raise Socks5Exception(Socks5ExceptionMsg.INVALID_ATYP)

        return (
            struct.pack(
                fmt,
                self.reserved,
                self.fragment,
                self.atyp,
                self.dst_addr,
                self.dst_port,
            )
            + self.payload
        )

    @classmethod
    def unpack(cls, data: bytes):
        "Unpack the UDP encapsulation"

        if len(data) < 10:
            raise Socks5Exception(Socks5ExceptionMsg.ENCAPSULATION_ERROR)

        rsv, frag, atyp = struct.unpack("!HBB", data[:4])

        if atyp == Socks5Msg.ATYP_IPV4:
            dst_addr, dst_port = struct.unpack("!4sH", data[4:10])
            head_len = 10
        elif atyp == Socks5Msg.ATYP_DOMAIN:
            domain_len = struct.unpack("!B", data[4:5])[0]
            dst_addr, dst_port = struct.unpack(
                f"!{domain_len}sH", data[5 : 5 + domain_len + 2]
            )
            head_len = 5 + domain_len + 2
        elif atyp == Socks5Msg.ATYP_IPV6:
            dst_addr, dst_port = struct.unpack("!16sH", data[4:24])
            head_len = 24
        else:
            raise Socks5Exception(Socks5ExceptionMsg.INVALID_ATYP)
        payload = data[head_len:]
        return cls(
            reserved=rsv,
            fragment=frag,
            atyp=atyp,
            dst_addr=dst_addr,
            dst_port=dst_port,
            payload=payload,
        )


async def read_network_address(reader: asyncio.StreamReader) -> ProxyNetworkAddress:
    "read socks network address from stream buffer"

    atyp = await reader.readexactly(1)
    if atyp == Socks5Msg.ATYP_IPV4:
        addr = await reader.readexactly(4)
        port = await reader.readexactly(2)
    elif atyp == Socks5Msg.ATYP_IPV6:
        addr = await reader.readexactly(16)
        port = await reader.readexactly(2)
    elif atyp == Socks5Msg.ATYP_DOMAIN:
        al = await reader.readexactly(1)
        addr = await reader.readexactly(al)
        port = await reader.readexactly(2)
    else:
        raise ValueError("Invalid address type")

    return atyp, addr, port


class UDPAssociatorError(Exception):
    pass


class UDPAssociatorInbound(asyncio.DatagramProtocol):
    """
    UDP relay associator protocol
    """

    loop = asyncio.AbstractEventLoop
    context: ProxyContext
    transport: asyncio.DatagramTransport
    peer_addr: types.NetAddress

    _buffer: asyncio.StreamReader
    _fragment_count: int = 0
    _outbounds: t.Dict[types.NetAddress, StreamABC]

    def __init__(self, context: ProxyContext, loop=None):
        self.context = context
        if not loop:
            loop = asyncio.get_running_loop()
        self.loop = loop
        self._outbounds = {}
        self.context.closed.add_done_callback(lambda _fut: self.close())

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        self._buffer = asyncio.StreamReader()

    def _process_diagram(self, data: bytes, ctx: ProxyContext) -> bytes:

        encap = UDPEncapsulation.unpack(data)
        dst = (encap.atyp, encap.dst_addr, encap.dst_port)
        ctx.destination = dst
        ho = encap.fragment & 0x80

        if ho > 127:
            raise ValueError("Invalid fragment")

        if ho == 0:
            payload = ctx.adapter.outbound_process(encap.payload, udp=True, dst=dst)
            return payload
        else:
            raise NotImplementedError

    async def _create_outbound(self, src: RetAddress, data: bytes):

        if self._outbounds.get(src):
            raise UDPAssociatorError("The peer is exsits")

        ctx = ProxyContext(config=self.context.config)
        ctx.source = src
        _tp, protocol = await create_outbound_connection(ctx)
        ctx.inbound = self
        ctx.outbound = protocol
        self._outbounds[src] = protocol

        payload = self._process_diagram(data, ctx)
        protocol.write(payload)

    def write(self, data: bytes, addr: RetAddress):
        "write data to the udp relay peer"
        self.transport.sendto(data, addr)

    def datagram_received(self, data: bytes, addr: RetAddress):
        logger.debug(f"Received {len(data)} bytes from {addr}")

        outbound = self._outbounds.get(addr)
        if not outbound:
            self.loop.create_task(self._create_outbound(addr, data))
        else:
            payload = self._process_diagram(data, outbound.context)
            outbound.write(payload)

    def error_received(self, exc):
        print(f"Error received: {exc}")

    def connection_lost(self, exc):
        print("Socket closed")
        self.close()

    def close(self):
        "close the udp inbound and all relay outbouns"

        for k, v in self._outbounds.items():
            v.close()

        if self.transport:
            self.transport.close()

        logger.debug("UDP inbound closed")


class Socks5InboundProtocol(asyncio.Protocol, StreamABC):
    "Socks5 inbound protocol"
    config: ProxyConfig
    context: ProxyContext

    _handshaked = False

    version: int | None = None
    command: int | None = None

    transport: asyncio.DatagramTransport
    udp_inbound: UDPAssociatorInbound | None = None
    _buffer: asyncio.StreamReader

    def __init__(
        self,
        config: ProxyConfig,
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self.config = config
        if not loop:
            loop = asyncio.get_running_loop()
        self.loop = loop
        context = ProxyContext(config=config)
        self.context = context
        self.context.closed.add_done_callback(lambda _fut: self.close())

    def _connect(self):
        "socks5 connect command"
        self.context.outbound_connected.add_done_callback(self._on_outbound_connected)
        if self.context.outbound_connected.done():
            return

        logger.debug("connect to outbound")
        self.loop.create_task(create_outbound_connection(self.context))

    def _handshake(self, data: bytes):

        ver, nmethods = data[:2]
        if ver != Socks5Msg.VER:
            raise Socks5Exception(Socks5ExceptionMsg.HANDSHAKE_FAILED)

        self.version = ver

        if nmethods > 0:
            methods = data[2 : 2 + nmethods]
            if 0 in methods:
                self.transport.write(bytes([Socks5Msg.VER, 0]))
                self._handshaked = True
            else:
                raise Socks5Exception(Socks5ExceptionMsg.HANDSHAKE_FAILED)
        logger.debug("socks5 handshake")

    def _recv_request(self, data: bytes):
        ver, cmd, rsv, atyp = data[:4]
        self.command = cmd

        if ver != Socks5Msg.VER or rsv != Socks5Msg.RSV:
            self.transport.write(
                bytes([Socks5Msg.VER, Socks5Msg.COMMAND_NOT_SUPPORTED])
            )
            raise Socks5Exception(Socks5ExceptionMsg.HANDSHAKE_FAILED)

        match atyp:
            case Socks5Msg.ATYP_IPV4:
                addr, port = data[4:8], data[8:10]
            case Socks5Msg.ATYP_IPV6:
                raise NotImplementedError
            case Socks5Msg.ATYP_DOMAIN:
                offset = len(data[4])
                addr = data[5 : 5 + offset]
                port = data[5 + offset, 5 + offset + 2]
            case _:
                raise Socks5Exception(Socks5ExceptionMsg.INVALID_ATYP)

        port = struct.unpack("!H", port)[0]

        self.context.destination = (atyp, addr, port)
        logger.debug("socks5 request receviced")

    def _on_outbound_connected(self, _fut):

        logger.debug("outbound connected")
        if self.command == Socks5Msg.CMD_CONNECT:
            self._reply(
                Socks5Msg.ATYP_IPV4,
                socket.inet_aton(self.context.config.server),
                self.context.config.port,
            )
            self.context.inbound = self.transport

    def _reply(self, bnd_atyp: int, bnd_addr: bytes, bnd_port: int):
        "Reply to the client"
        logger.debug(f"reply to socks5 client: {bnd_addr}:{bnd_port}")
        reply = Socks5Replies(
            ver=Socks5Msg.VER,
            reply_code=Socks5Msg.SUCCESS,
            reserved=Socks5Msg.RSV,
            atyp=bnd_atyp,
            bind_addr=bnd_addr,
            bind_port=bnd_port,
        ).pack()
        self.transport.write(reply)
        logger.debug("socks5 replied")

    def _udp_associate(self):

        async def _():

            transport, protocol = await self.loop.create_datagram_endpoint(
                lambda: UDPAssociatorInbound(self.context),
                local_addr=("0.0.0.0", 0),
            )
            self.udp_inbound = protocol
            self.context.inbound = protocol
            addr, port = transport.get_extra_info("sockname")
            self._reply(Socks5Msg.ATYP_IPV4, socket.inet_aton(addr), port)

        self.loop.create_task(_())

    def data_received(self, data: bytes):
        if not self.version:
            self._handshake(data)
            return
        if self.command is None:
            self._recv_request(data)
            match self.command:
                case Socks5Msg.CMD_CONNECT:
                    self._connect()
                case Socks5Msg.CMD_UDP:
                    self._udp_associate()
                case _:
                    raise NotImplementedError
            return

        proto_data = self.context.adapter.outbound_process(data)
        self.context.outbound.write(proto_data)

    def write(self, data: bytes):
        self._write_inbound(data)

    def connection_made(self, transport: asyncio.Transport):
        logger.debug("new socks5 connection")
        self.transport = transport

    def connection_lost(self, exc):
        logger.debug("connection lost")
        self.close()

    def close(self):
        if self.transport:
            self.transport.close()
        if self.udp_inbound:
            self.udp_inbound.close()

        logger.debug("socks5 inbound closed")
