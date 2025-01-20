import asyncio
import struct
import socket
import time
import random
from typing import Tuple

from loguru import logger


def create_udp_associate_request(client_ip: str, client_port: int) -> bytes:
    """
    Create a valid UDP ASSOCIATE request.
    """
    request = bytearray([0x05, 0x03, 0x00, 0x01])  # VER, CMD, RSV, ATYP (IPv4)
    request += socket.inet_aton(client_ip)  # BND.ADDR (client IP)
    request += struct.pack("!H", client_port)  # BND.PORT (client port)
    return bytes(request)


def mock_dns_query(domain: str) -> bytes:
    """
    Mockup DNS query function that sends a DNS query to a DNS server and returns the response.
    """

    # Create a DNS query for the specified domain
    transaction_id = struct.pack("!H", 0x1234)  # Random transaction ID
    flags = struct.pack("!H", 0x0100)  # Standard query
    questions = struct.pack("!H", 0x0001)  # Number of questions
    answer_rrs = struct.pack("!H", 0x0000)  # Number of answer resource records
    authority_rrs = struct.pack("!H", 0x0000)  # Number of authority resource records
    additional_rrs = struct.pack("!H", 0x0000)  # Number of additional resource records
    query = (
        b"\x03" + b"www" + b"\x07" + b"safewoo" + b"\x03" + b"com" + b"\x00"
    )  # Query: www.safewoo.com
    query_type = struct.pack("!H", 0x0001)  # Query type: A (IPv4 address)
    query_class = struct.pack("!H", 0x0001)  # Query class: IN (Internet)

    dns_query = (
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

    return dns_query


def test_send_via_socks5():
    # Test sending a DNS query via a SOCKS5 server
    socks5_server = "127.0.0.1"
    # socks5_port = 9098
    socks5_port = 1080
    dns_server = "1.1.1.1"
    domain = "safewoo.com"

    query = mock_dns_query(domain)

    # Create a TCP connection to the SOCKS5 server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
        tcp_sock.connect((socks5_server, socks5_port))

        # 1. Handshake
        tcp_sock.sendall(b"\x05\x01\x00")
        handshake_response = tcp_sock.recv(2)
        assert handshake_response == b"\x05\x00", "SOCKS5 handshake failed"
        print("Handshake successful")

        # 2. UDP ASSOCIATE request
        udp_associate_request = b"\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00"
        # udp_ass_request = create_udp_associate_request()
        tcp_sock.sendall(udp_associate_request)
        associate_response = tcp_sock.recv(10)
        assert associate_response[1] == 0x00, "UDP ASSOCIATE request failed"
        print("UDP ASSOCIATE successful")

        # Extract the UDP relay address and port from the response
        relay_ip = socket.inet_ntoa(associate_response[4:8])
        relay_port = struct.unpack("!H", associate_response[8:10])[0]

        print(f"Relay IP: {relay_ip}, Relay port: {relay_port}")

        # Create a UDP socket to send the DNS query via the SOCKS5 server
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            # Construct the UDP packet with the SOCKS5 header
            # udp_sock.setblocking(False)
            udp_packet = bytearray()
            udp_packet += b"\x00\x00\x00"  # Reserved
            udp_packet += b"\x01"  # Address type: IPv4
            udp_packet += socket.inet_aton(dns_server)
            udp_packet += struct.pack("!H", 53)  # DNS server port
            udp_packet += query  # DNS query
            print(udp_packet)
            print(f"send to {relay_ip}:{relay_port}")
            # Send the UDP packet to the SOCKS5 server's UDP relay
            udp_sock.sendto(udp_packet, (relay_ip, relay_port))
            print("Sent DNS query via SOCKS5")

            # Receive the response from the SOCKS5 server's UDP relay
            response, _ = udp_sock.recvfrom(4096)
            print("Received response from SOCKS5")

            # Extract the DNS response from the SOCKS5 UDP packet
            dns_response = response[10:]
            print(dns_response)


def test_socks5_echo():
    # Test sending a DNS query via a SOCKS5 server
    socks5_server = "127.0.0.1"
    socks5_port = 9098

    echo_server_port = 53
    dns_server = "1.1.1.1"

    domain = "safewoo.com"
    query = mock_dns_query(domain)
    # z = "00"*10
    # query = z.encode()

    # Create a TCP connection to the SOCKS5 server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
        tcp_sock.connect((socks5_server, socks5_port))

        # 1. Handshake
        tcp_sock.sendall(b"\x05\x01\x00")
        handshake_response = tcp_sock.recv(2)
        assert handshake_response == b"\x05\x00", "SOCKS5 handshake failed"
        print("Handshake successful")

        # 2. UDP ASSOCIATE request
        udp_associate_request = b"\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00"
        # udp_ass_request = create_udp_associate_request()
        tcp_sock.sendall(udp_associate_request)
        associate_response = tcp_sock.recv(10)
        assert associate_response[1] == 0x00, "UDP ASSOCIATE request failed"
        print("UDP ASSOCIATE successful")

        # Extract the UDP relay address and port from the response
        relay_ip = socket.inet_ntoa(associate_response[4:8])
        relay_port = struct.unpack("!H", associate_response[8:10])[0]

        print(f"Relay IP: {relay_ip}, Relay port: {relay_port}")

        # Create a UDP socket to send the DNS query via the SOCKS5 server
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            # Construct the UDP packet with the SOCKS5 header
            # udp_sock.setblocking(False)
            udp_packet = bytearray()
            udp_packet += b"\x00\x00\x00"  # Reserved
            udp_packet += b"\x01"  # Address type: IPv4
            udp_packet += socket.inet_aton(dns_server)
            udp_packet += struct.pack("!H", echo_server_port)  # DNS server port
            udp_packet += query  # DNS query
            print(f"send to {relay_ip}:{relay_port}")
            # Send the UDP packet to the SOCKS5 server's UDP relay
            print(udp_packet.hex())
            udp_sock.sendto(udp_packet, (relay_ip, relay_port))
            print("Sent DNS query via SOCKS5")

            # Receive the response from the SOCKS5 server's UDP relay
            response, _ = udp_sock.recvfrom(4096)
            print("Received response from SOCKS5")

            # Extract the DNS response from the SOCKS5 UDP packet
            dns_response = response[10:]
            print(dns_response)
            print(dns_response.hex())


def send_udp_data_through_socks(
    socks_server_udp_ip, socks_server_udp_port, dest_ip, dest_port, udp_data_to_send
):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.sendto(udp_data_to_send, (socks_server_udp_ip, socks_server_udp_port))
        response, _ = udp_sock.recvfrom(1024)  # Receive response
        udp_sock.close()
        return response


def udp_encap(data: bytes, dest_ip: str, dest_port: int, frag: int = 0) -> bytes:
    """
    Encapsulate the given data into a UDP packet.
    """
    packet = bytearray()
    packet += b"\x00\x00"  # Reserved
    packet += struct.pack("!B", frag)  # Fragment ID
    packet += b"\x01"  # Address type: IPv4
    packet += socket.inet_aton(dest_ip)
    packet += struct.pack("!H", dest_port)
    packet += data
    return bytes(packet)


def get_socks5_proxy(
    proxy_addr: Tuple[str, int]
) -> Tuple[socket.socket, Tuple[str, int]]:
    # Test sending a DNS query via a SOCKS5 server
    # socks5_server = "127.0.0.1"
    # socks5_port = 1080
    # socks5_port = 1080
    # dns_server = "114.114.114.114"
    # domain = "safewoo.com"

    # query = mock_dns_query(domain)

    # Create a TCP connection to the SOCKS5 server
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.connect(proxy_addr)

    # 1. Handshake
    tcp_sock.sendall(b"\x05\x01\x00")
    handshake_response = tcp_sock.recv(2)
    assert handshake_response == b"\x05\x00", "SOCKS5 handshake failed"
    print("Handshake successful")

    # 2. UDP ASSOCIATE request
    udp_associate_request = b"\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00"
    # udp_ass_request = create_udp_associate_request()
    tcp_sock.sendall(udp_associate_request)
    associate_response = tcp_sock.recv(10)
    assert associate_response[1] == 0x00, "UDP ASSOCIATE request failed"
    print("UDP ASSOCIATE successful")

    # Extract the UDP relay address and port from the response
    relay_ip = socket.inet_ntoa(associate_response[4:8])
    relay_port = struct.unpack("!H", associate_response[8:10])[0]

    print(f"Relay IP: {relay_ip}, Relay port: {relay_port}")

    proxy_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return proxy_sock, (relay_ip, relay_port)


def test_send_udp():
    """
    Send random UDP data to the specified address, run forever and receive response, thie response is the length of the data sent.
    """

    from tornado.ioloop import IOLoop

    loop = IOLoop.current()
    address = ("127.0.0.1", 9090)
    proxy_addr = ("127.0.0.1", 9098)
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock, proxy_bnd_addr = get_socks5_proxy(proxy_addr)
    sock.setblocking(True)

    def _send():
        frag = 0
        while True:
            frag = frag + 1
            try:
                data = str(hash(time.time())).encode()
                data = udp_encap(data, address[0], address[1], 0)
                sock.sendto(data, proxy_bnd_addr)
                logger.debug(
                    f"Sent {len(data)} bytes to {address} via proxy {proxy_bnd_addr}"
                )
                time.sleep(random.randint(1, 5) * 0.1)
            except Exception as e:
                logger.error(f"Error sending UDP data: {e}")
                return

    def _recv():
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                logger.debug(f"Received {data} from {addr}")
            except Exception as e:
                logger.error(f"Error receiving UDP data: {e}")
                return

    loop.run_in_executor(None, _send)
    loop.run_in_executor(None, _recv)
    loop.start()
