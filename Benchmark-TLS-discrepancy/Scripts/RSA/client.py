import socket
import asyncio
import argparse
import time
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
import ssl

DATA_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
PRIVATE_KEY_FILE = "client_private.pem"
PUBLIC_KEY_FILE = "client_public.pem"


def log(msg, verbose=True):
    if verbose:
        print(f"[CLIENT] {msg}")


def load_or_generate_keys():
    if Path(PRIVATE_KEY_FILE).exists() and Path(PUBLIC_KEY_FILE).exists():
        private_key = RSA.import_key(Path(PRIVATE_KEY_FILE).read_bytes())
        return private_key, private_key.publickey()
    private_key = RSA.generate(2048)
    Path(PRIVATE_KEY_FILE).write_bytes(private_key.export_key())
    Path(PUBLIC_KEY_FILE).write_bytes(private_key.publickey().export_key())
    return private_key, private_key.publickey()


def sign_data(private_key, data):
    h = SHA256.new(data)
    return pkcs1_15.new(private_key).sign(h)


def start_tcp_client(verbose=False):
    private_key, _ = load_or_generate_keys()
    data = b"x" * DATA_SIZE
    signature = sign_data(private_key, data)
    full_data = data + signature

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 4444))
        log("Connected to TCP server", verbose)

        total_sent = 0
        start_time = time.time()
        while total_sent < len(full_data):
            end = min(total_sent + CHUNK_SIZE, len(full_data))
            sent = s.send(full_data[total_sent:end])
            total_sent += sent

            if verbose and total_sent % (10 * 1024 * 1024) < CHUNK_SIZE:
                log(f"Progress: Sent {total_sent // (1024 * 1024)} MB", verbose)

        end_time = time.time()
        log(f"✅ Finished sending {total_sent} bytes in {end_time - start_time:.2f} seconds", verbose)


async def start_quic_client(verbose=False):
    private_key, _ = load_or_generate_keys()
    data = b"x" * DATA_SIZE
    signature = sign_data(private_key, data)
    full_data = data + signature

    configuration = QuicConfiguration(is_client=True)
    configuration.verify_mode = ssl.CERT_NONE
    configuration.load_cert_chain(certfile=TLS_CERT)
    configuration.load_verify_locations(cafile=TLS_CERT)

    log("Connecting to QUIC server...", verbose)
    start_time = time.time()

    async with connect("127.0.0.1", 443, configuration=configuration) as connection:
        log("Connected to QUIC server.", verbose)
        stream_id = connection._quic.get_next_available_stream_id()
        total_sent = 0

        while total_sent < len(full_data):
            end = min(total_sent + CHUNK_SIZE, len(full_data))
            chunk = full_data[total_sent:end]
            connection._quic.send_stream_data(
                stream_id, chunk, end_stream=False)
            total_sent += len(chunk)

            if verbose and total_sent % (10 * 1024 * 1024) < CHUNK_SIZE:
                log(f"Progress: Sent {total_sent // (1024 * 1024)} MB", verbose)

        connection._quic.send_stream_data(stream_id, b"", end_stream=True)
        await connection.wait_closed()
        end_time = time.time()
        log(f"✅ Finished sending {total_sent} bytes in {end_time - start_time:.2f} seconds", verbose)


def run_client(protocol='tcp', verbose=False):
    if protocol == 'tcp':
        start_tcp_client(verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_client(verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TCP/QUIC client")
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run_client(protocol=args.protocol, verbose=args.verbose)
