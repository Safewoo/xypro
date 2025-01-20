import asyncio

from xypro.proxy import create_proxy
from xypro.config import ProxyConfig
from xypro.run import run

ssl_config = {
    "uuid": "4b118c1f-dd98-4f13-8754-fecfb7c5949e",
    "server": "34.124.174.202",
    "servername": "l1.subwayvpn.com",
    "port": 443,
    "path": "/pwcTmmpYnJ8",
    "network": "ws",
    "tls": True,
}

self_signed_config = {
    "protocol": "vless",
    "uuid": "bafcd0bd-5325-45af-8747-454ffd844784",
    "server": "34.131.126.3",
    "servername": "hhoy.jncc.com",
    "port": 443,
    "network": "ws",
    "tls": True,
    # "path": "/Sul4",
    "skip-cert-verify": True,
    "ws-opts": {
        "path": "/Sul4",
        "headers": {
            "Host": "hhoy.jncc.com",
            "User-Agent": "xyrpo",
        }
    }
}

ws_config = {
    "uuid": "27848739-7e62-4138-9fd3-098a63964b6b",
    "server": "172.17.101.95",
    "port": 9090,
    "network": "ws",
    "tls": False,
    "ws-opts": {
        "path": "/",
        "headers": {
            "Host": "example.com",
            "User-Agent": "xyrpo",
        }
    }
}


if __name__ == "__main__":
    # config_dic = ssl_config
    config_dic = self_signed_config
    # config_dic = ws_config

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    config = ProxyConfig(**config_dic)
    print(config)
    coro = create_proxy(config, ("127.0.0.1", 9098))
    asyncio.run(coro)
    loop.run_forever()
