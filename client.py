import asyncio
import logging
import ssl
from aioquic.asyncio import connect, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, DatagramFrameReceived, StreamDataReceived

# Define the host and port for the server
HOST = "localhost"
PORT = 4433

# Define the path to the server's certificate
SERVER_CERT = "server.crt"

# Define the ping pong message
PING_MSG = b"ping"
connection = None


# Define the handler to process incoming data
class PingPongProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def connection_made(self, transport):
        self._transport = transport
        logger.info("Connected to server")

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, DatagramFrameReceived):
            message = event.data.decode()
            logger.info(f"Received message from server: {message}")
            self._quic.send_datagram_frame(b"ping")
        elif isinstance(event, StreamDataReceived):
            message = event.data.decode()
            logger.info(f"Received message from server: {message}")
            self._quic.send_stream_data(event.stream_id, b"ping")

    def connection_lost(self, exc):
        logger.info("Connection closed")


# Define the function to start the ping pong loop
async def start_ping_pong(protocol):
    protocol._quic.send_datagram_frame(b"ping")
    protocol.transmit()


# Define the function to start the client
async def main():
    # Set up the QUIC configuration
    quic_config = QuicConfiguration(
        alpn_protocols=["webtransport"],
        is_client=True,
        max_datagram_frame_size=65536,
        verify_mode=ssl.CERT_REQUIRED,
        server_name=HOST,
    )
    quic_config.load_verify_locations("server.crt")

    # Connect to the server
    global connection
    async with connect(HOST, PORT, configuration=quic_config, create_protocol=PingPongProtocol) as connection:
        asyncio.create_task(start_ping_pong(connection))

        await connection.wait_closed()


# Start the client
if __name__ == "__main__":
    logger = logging.getLogger("aioquic_client")
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

    except AssertionError:
        logger.critical("Cant create event loop. Aborting...")
        exit(1)
    except KeyboardInterrupt:
        logger.info("Shutdown client...")
        connection.close()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        exit(0)
