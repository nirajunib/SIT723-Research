from aioquic.quic.events import HandshakeCompleted, StreamDataReceived
import socket
import asyncio
import argparse
import time
from rsa_utils import generate_rsa_keys, decrypt_rsa
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import HandshakeCompleted
import ssl

DATA_SIZE = 5 * 1024 * 1024  # 100MB
TLS_CERT = "server.crt"         # Path to your generated self-signed certificate
TLS_KEY = "server.key"          # Path to your generated private key


def log(msg, verbose=True):
    if verbose:
        print(f"[SERVER] {msg}")


def start_tcp_server(use_rsa=False, verbose=False):
    """
    Start a TCP server that receives 100MB of data with optional RSA decryption.
    Receives data in chunks with progress logging.
    """
    private_key, public_key = generate_rsa_keys() if use_rsa else (None, None)
    if use_rsa:
        log("RSA enabled. Generated public/private key pair.", verbose)
        log(f"Public Key: (n={public_key.n}, e={public_key.e})", verbose)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 4444))  # Bind to all available interfaces
        s.listen(1)
        log("TCP server is listening on port 4444", verbose)
        conn, addr = s.accept()
        with conn:
            log(f"Accepted connection from {addr}", verbose)
            received = b""
            start_time = time.time()
            while len(received) < DATA_SIZE:
                chunk = conn.recv(4096)  # Receiving data in chunks
                if not chunk:
                    break
                received += chunk
                if len(received) % (10 * 1024 * 1024) < 4096:
                    log(f"Progress: Received {len(received) // (1024 * 1024)} MB", verbose)
            end_time = time.time()

            if use_rsa:
                try:
                    decrypted = decrypt_rsa(private_key, received[:256])
                    received = decrypted + received[256:]
                    log("RSA decryption successful.", verbose)
                except Exception as e:
                    log(f"RSA decryption failed: {e}", verbose)

            if len(received) == DATA_SIZE:
                log(
                    f"✅ Data received correctly. {len(received)} bytes in {end_time - start_time:.2f}s", verbose)
            else:
                log(
                    f"⚠️ Data size mismatch. Expected {DATA_SIZE}, got {len(received)}", verbose)


# ------------------ QUIC SERVER ------------------ #


class MyQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, use_rsa=False, verbose=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.received = b""
        self.use_rsa = use_rsa
        self.verbose = verbose
        self.start_time = None
        self.private_key, self.public_key = generate_rsa_keys() if use_rsa else (None, None)

    def log(self, msg):
        if self.verbose:
            print(f"[SERVER-QUIC] {msg}")

    def quic_event_received(self, event):
        if isinstance(event, HandshakeCompleted):
            self.log("TLS Handshake completed.")

        elif isinstance(event, StreamDataReceived):
            if self.start_time is None:
                self.start_time = time.time()
                self.log("Connection started. Receiving data...")

            self.received += event.data
            print(
                f"[SERVER] Received {len(event.data)} bytes on stream {event.stream_id} (Total: {len(self.received)} bytes)")

            if event.end_stream:
                print("[SERVER] Stream closed.")

            if len(self.received) >= DATA_SIZE:
                end_time = time.time()

                if self.use_rsa:
                    try:
                        decrypted = decrypt_rsa(
                            self.private_key, self.received[:256])
                        self.received = decrypted + self.received[256:]
                        self.log("RSA decryption successful.")
                    except Exception as e:
                        self.log(f"RSA decryption failed: {e}")

                if len(self.received) == DATA_SIZE:
                    self.log(
                        f"✅ QUIC: Received {len(self.received)} bytes in {end_time - self.start_time:.2f}s")
                else:
                    self.log(
                        f"⚠️ Data size mismatch: {len(self.received)} bytes")

                self._quic.close(error_code=0x0)


async def start_quic_server(use_rsa=False, verbose=False):
    config = QuicConfiguration(
        is_client=False,
        certificate=TLS_CERT,
        private_key=TLS_KEY
    )

    # Disable certificate verification for self-signed certs
    # config.verify_mode = ssl.CERT_NONE
    # config.load_verify_locations(cafile=TLS_CERT)
    config.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    log("QUIC server starting with TLS...", verbose)
    await serve(
        "0.0.0.0", 443, configuration=config,
        create_protocol=lambda *args, **kwargs: MyQuicProtocol(
            *args, use_rsa=use_rsa, verbose=verbose, **kwargs)
    )

    log("QUIC server is running. Waiting for connections...", verbose)
    await asyncio.Event().wait()  # Keeps server alive indefinitely


def run_server(protocol='tcp', use_rsa=False, verbose=False):
    if protocol == 'tcp':
        start_tcp_server(use_rsa, verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_server(use_rsa, verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run TCP/QUIC server with optional RSA.")
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--rsa", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    run_server(protocol=args.protocol, use_rsa=args.rsa, verbose=args.verbose)
