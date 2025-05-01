import socket
import asyncio
import argparse
import time
import os
from dilithium_py.ml_dsa import ML_DSA_44
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, HandshakeCompleted

DATA_SIZE = 5 * 1024 * 1024  # 5MB
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
TLS_KEY = "server.key"
PUBLIC_KEY_PATH = "client_keys/dilithium_public.key"


def log(msg, verbose=True):
    if verbose:
        print(f"[SERVER] {msg}")


def load_public_key():
    if not os.path.exists(PUBLIC_KEY_PATH):
        raise FileNotFoundError("Missing client public key.")
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return f.read()


def start_tcp_server(verbose=False):
    public_key = load_public_key()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 4444))
        s.listen(1)
        log("TCP server listening on port 4444", verbose)
        conn, addr = s.accept()
        with conn:
            log(f"Accepted connection from {addr}", verbose)
            sig_len = int.from_bytes(conn.recv(4), "big")
            signature = conn.recv(sig_len)
            received = b""
            start_time = time.time()
            while len(received) < DATA_SIZE:
                chunk = conn.recv(CHUNK_SIZE)
                if not chunk:
                    break
                received += chunk
            try:
                ML_DSA_44.verify(public_key, signature, received)
                log(
                    f"✅ Signature verified. Received {len(received)} bytes in {time.time() - start_time:.2f}s", verbose)
            except Exception as e:
                log(f"❌ Signature verification failed: {e}", verbose)

# ----------- QUIC ------------


class MyQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, verbose=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = verbose
        self.public_key = load_public_key()
        self.sig_len = None
        self.signature = b""
        self.received = b""
        self.start_time = None

    def log(self, msg):
        if self.verbose:
            print(f"[SERVER-QUIC] {msg}")

    def quic_event_received(self, event):
        if isinstance(event, HandshakeCompleted):
            self.log("TLS handshake completed.")
        elif isinstance(event, StreamDataReceived):
            if self.start_time is None:
                self.start_time = time.time()
            self.received += event.data
            if self.sig_len is None and len(self.received) >= 4:
                self.sig_len = int.from_bytes(self.received[:4], "big")
                self.received = self.received[4:]
                self.log(f"Signature length: {self.sig_len} bytes")

            if self.sig_len is not None and len(self.signature) < self.sig_len:
                needed = self.sig_len - len(self.signature)
                self.signature += self.received[:needed]
                self.received = self.received[needed:]

            if self.sig_len is not None and len(self.received) >= DATA_SIZE:
                try:
                    ML_DSA_44.verify(
                        self.public_key, self.signature, self.received)
                    self.log(
                        f"✅ QUIC: Signature verified. Received {len(self.received)} bytes in {time.time() - self.start_time:.2f}s")
                except Exception as e:
                    self.log(f"❌ QUIC: Signature verification failed: {e}")
                self._quic.close()


async def start_quic_server(verbose=False):
    config = QuicConfiguration(is_client=False)
    config.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)
    log("QUIC server starting with TLS...", verbose)
    await serve("0.0.0.0", 4443, configuration=config,
                create_protocol=lambda *args, **kwargs: MyQuicProtocol(*args, verbose=verbose, **kwargs))
    await asyncio.Event().wait()


def run_server(protocol='tcp', verbose=False):
    if protocol == 'tcp':
        start_tcp_server(verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_server(verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run_server(args.protocol, args.verbose)
