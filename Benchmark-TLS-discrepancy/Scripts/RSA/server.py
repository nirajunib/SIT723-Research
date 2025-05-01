from aioquic.quic.events import HandshakeCompleted, StreamDataReceived
import socket
import asyncio
import argparse
import time
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration

DATA_SIZE = 5 * 1024 * 1024
TLS_CERT = "server.crt"
TLS_KEY = "server.key"
PUBLIC_KEY_FILE = "client_public.pem"


def log(msg, verbose=True):
    if verbose:
        print(f"[SERVER] {msg}")


def load_client_public_key():
    return RSA.import_key(Path(PUBLIC_KEY_FILE).read_bytes())


def verify_signature(public_key, data, signature):
    h = SHA256.new(data)
    pkcs1_15.new(public_key).verify(h, signature)


def start_tcp_server(verbose=False):
    public_key = load_client_public_key()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 4444))
        s.listen(1)
        log("TCP server is listening on port 4444", verbose)
        conn, addr = s.accept()
        with conn:
            log(f"Accepted connection from {addr}", verbose)
            received = b""
            start_time = time.time()
            while len(received) < DATA_SIZE + 256:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                received += chunk
                # if len(received) % (10 * 1024 * 1024) < 4096:
                #     log(f"Progress: Received {len(received) // (1024 * 1024)} MB", verbose)
            end_time = time.time()

            data = received[:-256]
            signature = received[-256:]

            try:
                verify_signature(public_key, data, signature)
                log(f"✅ Data verified. {len(data)} bytes in {end_time - start_time:.2f}s", verbose)
            except Exception as e:
                log(f"❌ Signature verification failed: {e}", verbose)


class MyQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, verbose=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = verbose
        self.received = b""
        self.start_time = None
        self.public_key = load_client_public_key()

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
            # self.log(
            #     f"Received {len(event.data)} bytes on stream {event.stream_id} (Total: {len(self.received)} bytes)")

            if event.end_stream:
                end_time = time.time()
                data = self.received[:-256]
                signature = self.received[-256:]

                try:
                    verify_signature(self.public_key, data, signature)
                    self.log(
                        f"✅ QUIC: Data verified. {len(data)} bytes in {end_time - self.start_time:.2f}s")
                except Exception as e:
                    self.log(f"❌ Signature verification failed: {e}")

                self._quic.close(error_code=0x0)


async def start_quic_server(verbose=False):
    config = QuicConfiguration(
        is_client=False, certificate=TLS_CERT, private_key=TLS_KEY)
    config.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    log("QUIC server starting with TLS...", verbose)
    await serve(
        "0.0.0.0", 443, configuration=config,
        create_protocol=lambda *args, **kwargs: MyQuicProtocol(
            *args, verbose=verbose, **kwargs)
    )
    await asyncio.Event().wait()


def run_server(protocol='tcp', verbose=False):
    if protocol == 'tcp':
        start_tcp_server(verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_server(verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TCP/QUIC server")
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run_server(protocol=args.protocol, verbose=args.verbose)
