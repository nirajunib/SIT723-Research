import socket
import asyncio
import argparse
import time
from rsa_utils import generate_rsa_keys, encrypt_rsa
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
import ssl


DATA_SIZE = 5 * 1024 * 1024  # 100MB
TLS_CERT = "server.crt"         # Path to your server's self-signed certificate


def log(msg, verbose=True):
    if verbose:
        print(f"[CLIENT] {msg}")


def start_tcp_client(use_rsa=False, verbose=False):
    """
    Start a TCP client to send 100MB of data to the server with optional RSA encryption.
    Sends data in chunks with progress logging.
    """
    chunk_size = 4096
    data = b"x" * DATA_SIZE
    _, public_key = generate_rsa_keys() if use_rsa else (None, None)

    if use_rsa:
        log("RSA enabled. Encrypting initial data block...", verbose)
        encrypted = encrypt_rsa(public_key, data[:190])
        data = encrypted + data[190:]
        log(
            f"RSA encryption complete. Total data size: {len(data)} bytes", verbose)

    log("Connecting to TCP server...", verbose)
    start_time = time.time()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Use actual public IP of the server
        s.connect(("127.0.0.1", 4444))
        log("Connected. Starting to send data in chunks...", verbose)

        total_sent = 0
        while total_sent < len(data):
            end = min(total_sent + chunk_size, len(data))
            sent = s.send(data[total_sent:end])
            total_sent += sent

            if verbose and total_sent % (10 * 1024 * 1024) < chunk_size:
                log(f"Progress: Sent {total_sent // (1024 * 1024)} MB", verbose)

    end_time = time.time()
    log(f"✅ Finished sending {total_sent} bytes in {end_time - start_time:.2f} seconds", verbose)


async def start_quic_client(use_rsa=False, verbose=False):
    """
    Start a QUIC client to send 100MB of data to the server with optional RSA encryption.
    Sends data in chunks with progress logging.
    """
    chunk_size = 4096
    data = b"x" * DATA_SIZE
    _, public_key = generate_rsa_keys() if use_rsa else (None, None)

    if use_rsa:
        log("RSA enabled. Encrypting initial data block...", verbose)
        encrypted = encrypt_rsa(public_key, data[:190])
        data = encrypted + data[190:]
        log(
            f"RSA encryption complete. Total data size: {len(data)} bytes", verbose)

    # Load server's certificate for verification
    configuration = QuicConfiguration(is_client=True)
    # Trust server's self-signed certificate
    # For testing only; use proper verification in production
    configuration.verify_mode = ssl.CERT_NONE
    configuration.load_cert_chain(certfile=TLS_CERT)
    configuration.load_verify_locations(cafile='server.crt')

    log("Connecting to QUIC server...", verbose)
    start_time = time.time()

    async with connect("127.0.0.1", 443, configuration=configuration) as connection:
        log("Connected to QUIC server.", verbose)

        stream_id = connection._quic.get_next_available_stream_id()
        total_sent = 0

        while total_sent < len(data):
            end = min(total_sent + chunk_size, len(data))
            chunk = data[total_sent:end]

            connection._quic.send_stream_data(
                stream_id, chunk, end_stream=False)
            total_sent += len(chunk)

            if verbose and total_sent % (10 * 1024 * 1024) < chunk_size:
                log(f"Progress: Sent {total_sent // (1024 * 1024)} MB", verbose)

        # Close the stream after sending all data
        connection._quic.send_stream_data(stream_id, b"", end_stream=True)

        await connection.wait_closed()

        end_time = time.time()
        log(f"✅ Finished sending {total_sent} bytes in {end_time - start_time:.2f} seconds", verbose)


def run_client(protocol='tcp', use_rsa=False, verbose=False):
    if protocol == 'tcp':
        start_tcp_client(use_rsa, verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_client(use_rsa, verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run TCP/QUIC client with optional RSA.")
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--rsa", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    run_client(protocol=args.protocol, use_rsa=args.rsa, verbose=args.verbose)
