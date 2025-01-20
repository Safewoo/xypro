""" 
Configuration definition that compatible with Clash 
"""

import typing as t
import yaml
from pydantic import BaseModel, Field


class WsOpts(BaseModel):
    "Websocket options"
    path: str = "/"
    headers: t.Dict[str, str] = Field(default_factory=dict)


class ProxyConfig(BaseModel):
    "Proxy configuration"
    name: str
    network: t.Literal["tcp", "ws", "http"]
    uuid: str
    server: str
    port: int
    tls: bool = False
    type: t.Literal["vless"] = "vless"
    udp: bool = False
    servername: str | None = None
    skip_cert_verify: bool = Field(False, alias="skip-cert-verify")

    ws_opts: WsOpts | None = Field(None, alias="ws-opts")


# class Configurations(BaseModel):
#     "Configurations"

#     log_level: t.Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
#         default="INFO"
#     )
#     port: int = Field(default=7890)  # not implemented yet
#     socks_port: int = Field(default=7891, alias="socks-port")
#     proxies: t.List[ProxyConfig]


def load_config(config_path: str) -> ProxyConfig:
    "Load configuration from file"

    try:
        with open(config_path, "rb") as f:
            config_dic = yaml.safe_load(f)
            return ProxyConfig(**config_dic)

    except FileNotFoundError as err:
        raise ValueError(f"Config file {config_path} not found") from err
