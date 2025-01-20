import socket
import time
import random
from typing import Dict, List, Tuple
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.netutil import bind_sockets
from loguru import logger


class UDPServer(object):
    def __init__(self, port: int):
        self.port = port
        self._sock = None
        self._io_loop = None
        self._periodic = None
        self._buffer: Dict[Tuple[str, int], List[int]] = {}

    def start(self):
        """Start the UDP server"""
        # Create and bind socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._sock.bind(("", self.port))

        # Setup IOLoop
        self._io_loop = IOLoop.current()
        self._io_loop.add_handler(
            self._sock.fileno(), self._handle_datagram, IOLoop.READ
        )

        # Setup periodic callback
        self._periodic = PeriodicCallback(self._process_buffer, 3000)
        self._periodic.start()

        logger.info(f"UDP Server started on port {self.port}")

    def stop(self):
        """Stop the UDP server"""
        if self._periodic:
            self._periodic.stop()
        if self._io_loop and self._sock:
            self._io_loop.remove_handler(self._sock.fileno())
        if self._sock:
            self._sock.close()
            self._sock = None
        logger.info("UDP Server stopped")

    def _handle_datagram(self, fd: int, events: int):
        """Handle incoming UDP datagram"""
        while True:
            try:
                data, addr = self._sock.recvfrom(65535)
                if not data:
                    return

                # Store received bytes
                if addr not in self._buffer:
                    self._buffer[addr] = []
                self._buffer[addr].extend(data)
                logger.debug(f"Received {len(data)} bytes from {addr}")

            except BlockingIOError:
                return
            except Exception as e:
                logger.error(f"Error handling datagram: {e}")
                return

    def _process_buffer(self):
        """Process buffered data every 3 seconds"""
        for addr, data in self._buffer.items():
            if data:
                total = sum(data)
                try:
                    self._sock.sendto(str(total).encode(), addr)
                    logger.info(f"Sent sum {total} to {addr}")
                except Exception as e:
                    logger.error(f"Error sending response: {e}")

        # Clear buffer
        self._buffer.clear()


if __name__ == "__main__":
    udp_server = UDPServer(9090)
    udp_server.start()
    try:
        IOLoop.current().start()
    except KeyboardInterrupt:
        udp_server.stop()
        IOLoop.current().stop()
        logger.info("Server stopped by user")
