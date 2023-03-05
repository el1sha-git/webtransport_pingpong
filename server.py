import logging
import time

from aioquic.asyncio import QuicConnectionProtocol, serve

import asyncio
import pathlib

from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import DatagramFrameReceived, StreamDataReceived, HandshakeCompleted, ConnectionTerminated
from aioquic.quic.logger import QuicLogger

ROOT = pathlib.Path(__file__).parent


class PingPongProtocol(QuicConnectionProtocol):
    def quic_event_received(self, event):
        if isinstance(event, DatagramFrameReceived):
            message = event.data.decode()
            logger.info(f"Received message from client: {message}")
            time.sleep(1)
            self._quic.send_datagram_frame(b"pong")
        elif isinstance(event, StreamDataReceived):
            message = event.data.decode()
            logger.info(f"Received message from client: {message}")
            time.sleep(1)
            self._quic.send_stream_data(event.stream_id, b"pong")
        elif isinstance(event, HandshakeCompleted):
            logger.info("Handshake completed")
        elif isinstance(event, ConnectionTerminated):
            logger.info("Connection terminated")


async def main():
    logger.info("Starting ping pong webtrasport server...")

    configuration = QuicConfiguration(
        alpn_protocols=["webtransport"],
        is_client=False,
        max_datagram_frame_size=65536,
        quic_logger=QuicLogger(),
    )
    configuration.load_cert_chain(ROOT / "server.crt", ROOT / "server.key")
    await serve(
        "localhost",
        4433,
        configuration=configuration,
        create_protocol=PingPongProtocol,
    )
    logger.info("Server started. Waiting for connections...")
    await asyncio.Future()


# except KeyboardInterrupt:
#     logger.info("Shutdown server")
#     for task in asyncio.all_tasks():
#         task.cancel()
#     # wait for all tasks to be cancelled
#     await asyncio.gather(*asyncio.all_tasks())


if __name__ == "__main__":
    logger = logging.getLogger("aioquic_server")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    formatter = logging.Formatter(
        "%(asctime)s  %(message)s", datefmt="%H:%M:%S"
    )
    logger.handlers[0].setFormatter(formatter)
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    try:
        assert loop is not None
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Shutdown server...")
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
    except AssertionError:
        logger.critical("Cant create event loop. Aborting...")
        exit(1)

    # asyncio.run(main())
