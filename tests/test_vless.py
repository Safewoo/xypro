import asyncio
import socket
import struct

import pytest
from loguru import logger

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedOK


from xypro.protocol import vless, socks5
from xypro.config import ProxyConfig


user_id = "27848739-7e62-4138-9fd3-098a63964b6b"
hex_user_id = bytes.fromhex(user_id.replace("-", ""))


print(hex_user_id)

"""
ver,uuid,                           el, udp, port, atyp, addr,     frag?   len(payload)     payload
00,278487397e6241389fd3098a63964b6b,00, 02,  270f,  01,  c0a86438,  00,      14,            3030303030303030303030303030303030303030
"""


def mock_http_raw_request(url: str) -> bytes:
    "Mock a simple GET request to the given URL"
    host = url.split("//")[-1].split("/")[0]
    return f"GET {url} HTTP/1.1\r\nHost: {host}\r\n\r\n".encode("utf-8")


def mock_raw_dns_request(name: str) -> bytes:
    "Mock a simple DNS request for the given domain name"
    transaction_id = b"\xaa\xaa"  # Random transaction ID
    flags = b"\x01\x00"  # Standard query
    questions = b"\x00\x01"  # One question
    answer_rrs = b"\x00\x00"  # No answer
    authority_rrs = b"\x00\x00"  # No authority
    additional_rrs = b"\x00\x00"  # No additional

    # Convert domain name to DNS query format
    query = b"".join(
        struct.pack("!B", len(part)) + part.encode("utf-8") for part in name.split(".")
    )
    query += b"\x00"  # End of the domain name
    query_type = b"\x00\x01"  # Type A
    query_class = b"\x00\x01"  # Class IN

    dns_request = (
        transaction_id
        + flags
        + questions
        + answer_rrs
        + authority_rrs
        + additional_rrs
        + query
        + query_type
        + query_class
    )
    return dns_request


@pytest.mark.asyncio
async def test_tcp_vless():
    vless_host = "127.0.0.1"
    vless_port = 1080
    dst_host = "1.1.1.1"

    uuid = "27848739-7e62-4138-9fd3-098a63964b6b"

    uuid_hex = uuid.replace("-", "").encode("utf-8")
    print(uuid_hex)

    head = vless.VlessRequest(
        ver=vless.VLESS_VER,
        uuid="27848739-7e62-4138-9fd3-098a63964b6b",
        ext_len=0,
        ext=b"",
        cmd=vless.VlessCommand.TCP,
        atyp=socks5.Socks5Msg.ATYP_IPV4,
        addr=socket.inet_aton(dst_host),
        port=80,
    ).pack_head()
    reader, writer = await asyncio.open_connection(vless_host, vless_port)

    async def write():
        "Write to the VLESS server"
        writer.write(head)
        writer.write(mock_http_raw_request("http://bing.com"))

    async def recv() -> bytes:
        "Receive from the VLESS server"
        head = await reader.readexactly(2)
        ver, el = struct.unpack("!BB", head)
        ext = await reader.readexactly(el)
        data = await reader.read(vless.BUFF_SIZE)
        logger.debug(data.decode("utf-8"))

    await asyncio.gather(
        write(),
        recv(),
    )


@pytest.mark.asyncio
async def test_udp_vless():
    vless_host = "127.0.0.1"
    vless_port = 9098
    head = vless.VlessRequest(
        ver=vless.VLESS_VER,
        uuid="27848739-7e62-4138-9fd3-098a63964b6b",
        ext_len=0,
        ext=b"",
        cmd=vless.VlessCommand.UDP,
        atyp=socks5.Socks5Msg.ATYP_IPV4,
        addr=socket.inet_aton("1.1.1.1"),
        port=53,
    ).pack_head()

    reader, writer = await asyncio.open_connection(vless_host, vless_port)

    async def recv() -> bytes:
        "Receive a DNS response"
        head = await reader.readexactly(2)
        ver, el = struct.unpack("!BB", head)
        ext = await reader.readexactly(el)
        data = await reader.read(vless.BUFF_SIZE)

    async def write():
        "Write a DNS request"
        payload = mock_raw_dns_request("safewoo.com")

        frag = 0
        pl = len(payload)
        writer.write(head + frag.to_bytes() + pl.to_bytes() + payload)

    await asyncio.gather(
        write(),
        recv(),
    )


@pytest.mark.asyncio
async def test_ws():
    vless_host = "192.168.100.62"
    vless_port = 9090
    head = vless.VlessRequest(
        ver=vless.VLESS_VER,
        uuid=user_id,
        ext_len=0,
        ext=b"",
        cmd=vless.VlessCommand.TCP,
        atyp=socks5.Socks5Msg.ATYP_IPV4,
        addr=socket.inet_aton("203.178.137.175"),
        port=80,
    ).pack_head()

    async with connect(f"ws://{vless_host}:{vless_port}") as ws:
        payload = mock_http_raw_request("http://ftp.jp.debian.org/debian/")
        data = head + payload
        # ws.send_data(data)
        await ws.send(data, text=False)
        data = b""

        while True:
            if ws.protocol.close_expected():
                break
            try:
                payload = await ws.recv()
                # data += payload
                logger.debug(payload)
            except ConnectionClosedOK:
                break
