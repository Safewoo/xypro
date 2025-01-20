"Proxy module."

import asyncio
import typing as t
import multiprocessing as mp

from loguru import logger

from xypro.config import ProxyConfig
from xypro.protocol import socks5


async def create_proxy(config: ProxyConfig, bind: t.Tuple[str, int]) -> None:
    "Create a proxy connection."
    loop = asyncio.get_running_loop()
    InboundProtocol = socks5.Socks5InboundProtocol
    inbound = await loop.create_server(
        lambda: InboundProtocol(config=config, loop=loop), host=bind[0], port=bind[1]
    )
    logger.info(f"listening on {bind[0]}:{bind[1]}")
    await inbound.serve_forever()
