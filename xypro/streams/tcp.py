import asyncio as aio
from loguru import logger
from xypro.context import ProxyContext, StreamABC


class TCPOutboundProtocol(aio.Protocol, StreamABC):
    transport: aio.Transport
    context: ProxyContext
    loop: aio.AbstractEventLoop

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def connection_made(self, transport):
        self.transport = transport
        self.context.outbound_connected.set_result(1)
        logger.debug("TCP outbound connection made")
    
    def connection_lost(self, exc):
        self.close()

    def data_received(self, data):
        # logger.debug(data)
        logger.debug(f"TCP outbound data received {len(data)} bytes")
        proto_data = self.context.adapter.inbound_process(data)
        logger.debug(proto_data)
        if self.context.source:
            # UDP over TCP relay
            self.context.inbound.write(proto_data, self.context.source)
        else:
            self.context.inbound.write(proto_data)

    def write(self, data):
        logger.debug(data)
        self.transport.write(data)

    def close(self):
        if self.transport:
            self.transport.close()
        if self.context.inbound:
            self.context.inbound.close()
