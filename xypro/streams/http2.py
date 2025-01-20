import asyncio as aio

from h2 import connection, events

from xypro.context import ProxyContext, StreamABC
from xypro import types


class HTTP2OutboundProtocol(aio.Protocol, StreamABC):

    transport: aio.Transport
    context: ProxyContext
    loop: aio.AbstractEventLoop
    h2_conn: connection.H2Connection

    def __init__(
        self, context: ProxyContext, loop: aio.AbstractEventLoop | None = None
    ) -> None:
        self.context = context
        if not loop:
            loop = aio.get_running_loop()
        self.loop = loop
        self._buffer = aio.StreamReader()
        self.h2_conn = connection.H2Connection()

    def _send_headers(self):
        headers = {
            ":method": "GET",
            ":scheme": "https",
            ":path": "/",
            ":authority": self.context.config.servername,
            "user-agent": "v2rapy",
        }
        self.h2_conn.initiate_connection()
        self.transport.write(self.h2_conn.data_to_send())

        stream_id = self.h2_conn.get_next_available_stream_id()
        self.h2_conn.send_headers(stream_id, [(k, v) for k, v in headers.items()])
        self.transport.write(self.h2_conn.data_to_send())

    def data_received(self, data):
        events = self.h2_conn.receive_data(data)

    def write(self, data: bytes, addr: types.NetAddress | None = None):
        stream_id = self.h2_conn.get_next_available_stream_id()
        self.h2_conn.send_data(stream_id, data)
        data_to_send = self.h2_conn.data_to_send()
        args = (data_to_send,)

        if self.context.config.udp:
            args += (addr,)

        self.context.inbound.write(*args)

    def connection_made(self, transport):
        self.transport = transport
        self._send_headers()

    def eof_received(self):
        return super().eof_received()