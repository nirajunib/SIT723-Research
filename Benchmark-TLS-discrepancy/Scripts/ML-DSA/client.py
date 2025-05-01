import ssl
import socket
import asyncio
import argparse
import time
import os
from dilithium_py.ml_dsa import ML_DSA_44
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

DATA_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
PRIVATE_KEY_PATH = "client_keys/dilithium_private.key"
PUBLIC_KEY_PATH = "client_keys/dilithium_public.key"


def log(msg, verbose=True):
    if verbose:
        print(f"[CLIENT] {msg}")


def generate_and_save_keypair(verbose=False):
    public_key, private_key = ML_DSA_44.keygen()
    os.makedirs("client_keys", exist_ok=True)
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key)
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(public_key)
    log("🔑 Dilithium keypair generated and saved.", verbose)


def generate_keys_if_missing(verbose=False):
    if not os.path.exists(PRIVATE_KEY_PATH) or not os.path.exists(PUBLIC_KEY_PATH):
        generate_and_save_keypair(verbose)


def load_private_key():
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return f.read()


def start_tcp_client(verbose=False):
    generate_keys_if_missing(verbose)
    private_key = load_private_key()
    data = b"x" * DATA_SIZE
    signature = ML_DSA_44.sign(private_key, data)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 4444))
        log("Connected to TCP server.", verbose)
        s.send(len(signature).to_bytes(4, "big"))
        s.send(signature)

        total_sent = 0
        while total_sent < len(data):
            end = min(total_sent + CHUNK_SIZE, len(data))
            sent = s.send(data[total_sent:end])
            total_sent += sent
        log(f"✅ Sent {total_sent} bytes.", verbose)


async def start_quic_client(verbose=False):
    generate_keys_if_missing(verbose)
    private_key = load_private_key()
    data = b"x" * DATA_SIZE
    signature = ML_DSA_44.sign(private_key, data)

    config = QuicConfiguration(is_client=True)
    config.load_cert_chain(certfile=TLS_CERT)
    config.verify_mode = ssl.CERT_NONE

    log("Connecting to QUIC server...", verbose)
    async with connect("127.0.0.1", 4443, configuration=config) as conn:
        stream_id = conn._quic.get_next_available_stream_id()
        conn._quic.send_stream_data(stream_id, len(signature).to_bytes(
            4, "big") + signature, end_stream=False)

        total_sent = 0
        while total_sent < len(data):
            end = min(total_sent + CHUNK_SIZE, len(data))
            conn._quic.send_stream_data(
                stream_id, data[total_sent:end], end_stream=False)
            total_sent += CHUNK_SIZE

        conn._quic.send_stream_data(stream_id, b"", end_stream=True)
        await conn.wait_closed()
        log(f"✅ Sent {total_sent} bytes via QUIC.", verbose)


def run_client(protocol='tcp', verbose=False):
    if protocol == 'tcp':
        start_tcp_client(verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_client(verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run_client(args.protocol, args.verbose)
