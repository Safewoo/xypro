"Context for proxy"

from abc import ABC, abstractmethod
from importlib import import_module
from asyncio import (
    Future,
    Protocol,
    AbstractEventLoop,
)

from loguru import logger

from xypro.config import ProxyConfig
from xypro.types import AtypAddress


class AdapterABC(ABC):
    """
    Every proto adapter should implement this interface.
    """

    @abstractmethod
    def inbound_process(self, data: bytes):
        "process inbound data from client"
        raise NotImplementedError

    @abstractmethod
    def outbound_process(self, data: bytes, udp=False, dst: AtypAddress | None = None):
        "process outbound data from server"
        raise NotImplementedError


class StreamABC(ABC):
    """
    Every stream should implement this interface.
    """

    context: "ProxyContext"
    loop = AbstractEventLoop

    def __init__(self, context: "ProxyContext", loop=None):
        self.context = context
        self.loop = loop

    def _write_outbound(self, data: bytes, *args, **kwargs):
        "write data to outbound"

        if not self.context.outbound:
            raise ValueError("Outbound not connected")

        if self.context.adapter:
            proto_data = self.context.adapter.outbound_process(data)
            self.context.outbound.write(proto_data, *args, **kwargs)
        else:
            raise ValueError("Adapter not found")

    def _write_inbound(self, data: bytes, *args, **kwargs):
        "write data to inbound"

        if not self.context.inbound:
            raise ValueError("Inbound not connected")

        if self.context.adapter:
            proto_data = self.context.adapter.inbound_process(data)
            self.context.inbound.write(proto_data, *args, **kwargs)
        else:
            raise ValueError("Adapter not found")

    @abstractmethod
    def close(self):
        "close the stream"
        raise NotImplementedError

    @abstractmethod
    def write(self, data: bytes):
        "write data to the stream"
        raise NotImplementedError


class ProxyContext(object):
    """Vless context"""

    config: ProxyConfig

    destination: AtypAddress | None = None
    source: AtypAddress | None = None  # if source specified, it's a udp over tcp relay

    outbound_connected: Future
    adapter: AdapterABC | None = None
    inbound: Protocol | None = None
    outbound: Protocol | None = None

    closed: Future

    def __init__(self, config: ProxyConfig):
        self.config = config
        self.outbound_connected = Future()
        self.closed = Future()
        self._create_adapter()
        logger.debug("ProxyContext created")

    def _create_adapter(self):
        if self.config.type not in ["vless", "tcp"]:
            raise NotImplementedError

        module_name = f"xypro.protocol.{self.config.type}"
        protocol_module = import_module(module_name)
        adapter_class = protocol_module.Adapter
        logger.debug(f"Adapter class: {adapter_class}")
        self.adapter = adapter_class(self)

    def close(self):
        "close inbound and outbound connection"

        if self.inbound:
            self.inbound.close()

        if self.outbound:
            self.outbound.close()
