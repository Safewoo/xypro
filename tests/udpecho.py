""" 
A simple UDP echo server that receives UDP datagrams and return the md5 hash of the received data.
"""

import asyncio
import hashlib

class UDPEchoServerProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(f"Received {len(data)} bytes from {addr}")
        md5_hash = hashlib.md5(data).hexdigest().encode('utf-8')
        self.transport.sendto(md5_hash, addr)
        print(f"Sent MD5 hash to {addr}")

async def main(port):
    loop = asyncio.get_running_loop()
    print("Starting UDP echo server on 127.0.0.1:9999")
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPEchoServerProtocol(),
        local_addr=('127.0.0.1', port)
    )

    try:
        await asyncio.sleep(3600)  # Run for 1 hour
    finally:
        transport.close()

        
if __name__ == "__main__":
    # receive a port number from the command line
    import sys
    port = int(sys.argv[1])
    asyncio.run(main(port))