""" 
A simple DNS server for testing. Receives a fixed DNS queries and responds with a fixed DNS response.
"""

import asyncio
import struct

class SimpleDNSServerProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(f"Received {len(data)} bytes from {addr}")
        response = self.create_dns_response(data)
        self.transport.sendto(response, addr)
        print(f"Sent response to {addr}")

    def create_dns_response(self, query):
        # Unpack the DNS query
        transaction_id = query[:2]
        flags = b'\x81\x80'  # Standard query response, no error
        questions = query[4:6]
        answer_rrs = b'\x00\x01'
        authority_rrs = b'\x00\x00'
        additional_rrs = b'\x00\x00'
        query_section = query[12:]

        # Create a fixed DNS response
        answer_name = b'\xc0\x0c'
        answer_type = b'\x00\x01'
        answer_class = b'\x00\x01'
        ttl = b'\x00\x00\x00\x3c'
        data_length = b'\x00\x04'
        ip_address = b'\x7f\x00\x00\x01'  # 127.0.0.1

        response = (
            transaction_id + flags + questions + answer_rrs +
            authority_rrs + additional_rrs + query_section +
            answer_name + answer_type + answer_class + ttl +
            data_length + ip_address
        )
        return response

async def main():
    loop = asyncio.get_running_loop()
    print("Starting DNS server on 127.0.0.1:5353")
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SimpleDNSServerProtocol(),
        local_addr=('127.0.0.1', 53)
    )

    try:
        await asyncio.sleep(3600)  # Run for 1 hour
    finally:
        transport.close()

asyncio.run(main())