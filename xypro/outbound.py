"Outbound connection module."

import typing as t
import asyncio as aio
import ssl

from loguru import logger

from xypro.streams.websocket import WebsocketOutboundProtocol
from xypro.streams.tcp import TCPOutboundProtocol


def create_ssl_context(tls: bool, skip_cert_verify: bool) -> ssl.SSLContext | None:
    "Create ssl context."
    if tls:
        ssl_context = ssl.create_default_context()
        if skip_cert_verify:
            logger.warning("skip certificate verification")
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        return ssl_context


async def create_outbound_connection(
    context,
) -> t.Tuple[aio.Transport, aio.Protocol]:
    "Create an outbound connection."
    loop = aio.get_running_loop()
    logger.debug(f"connect to {context.config.server}:{context.config.port}")

    tls = context.config.tls
    skip_cert_verify = context.config.skip_cert_verify
    ssl_context = create_ssl_context(tls, skip_cert_verify)

    match context.config.network:
        case "ws":
            stream_class = WebsocketOutboundProtocol
        case "tcp":
            stream_class = TCPOutboundProtocol
        case _:
            raise NotImplementedError
    
    transport, protocol = await loop.create_connection(
        lambda: stream_class(context=context),
        host=context.config.server,
        port=context.config.port,
        ssl=ssl_context,
    )
    
    context.outbound = protocol
    return transport, protocol
