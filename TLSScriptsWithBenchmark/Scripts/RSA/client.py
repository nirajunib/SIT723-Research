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
import os
import csv
import threading
import psutil  # For benchmarking

DATA_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
TLS_CERT_PEM = "server.pem"
PRIVATE_KEY_FILE = "client_private.pem"
PUBLIC_KEY_FILE = "client_public.pem"

BENCHMARK_DIR = "client_benchmarks"
os.makedirs(BENCHMARK_DIR, exist_ok=True)


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


def monitor_resources(interval, running_flag, stats_list, data_tracker):
    process = psutil.Process()
    start_time = time.time()
    prev_bytes = 0
    while running_flag["active"]:
        cpu = process.cpu_percent(interval=None)
        mem = process.memory_info().rss / (1024 * 1024)
        timestamp = time.time() - start_time
        current_bytes = data_tracker["bytes"]
        throughput = (current_bytes - prev_bytes) / (1024 * 1024) / interval
        prev_bytes = current_bytes
        stats_list.append((timestamp, cpu, mem, throughput))
        time.sleep(interval)


def save_benchmark(protocol, connection_time, stats_list, signed_msg_size, first_data_latency):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = os.path.join(BENCHMARK_DIR, f"{protocol}_{timestamp}.csv")
    with open(file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Time(s)", "CPU (%)", "Memory (MB)", "Throughput (MB/s)",
            "Connection Time(s)", "Signed Message Size (bytes)", "First Data Latency (s)"
        ])
        for row in stats_list:
            writer.writerow(
                [*row, connection_time, signed_msg_size, first_data_latency])


def start_tcp_client(verbose=False):
    private_key, _ = load_or_generate_keys()
    data = b"x" * DATA_SIZE
    signature = sign_data(private_key, data)
    full_data = data + signature

    stats = []
    data_tracker = {"bytes": 0}
    running_flag = {"active": True}
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(0.1, running_flag, stats, data_tracker))
    monitor_thread.start()

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.load_verify_locations(cafile=TLS_CERT)
    context.load_cert_chain(certfile="server.pem", keyfile="server_key.pem")

    start_time = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 4444))
        with context.wrap_socket(s, server_hostname="127.0.0.1") as ssl_sock:
            log("Connected to TCP TLS server", verbose)
            log(
                f"SSL handshake completed. Status: {ssl_sock.getpeercert()}", verbose)

            total_sent = 0
            first_data_time = None
            while total_sent < len(full_data):
                end = min(total_sent + CHUNK_SIZE, len(full_data))
                sent = ssl_sock.send(full_data[total_sent:end])
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent
                data_tracker["bytes"] += sent
                if first_data_time is None and total_sent >= CHUNK_SIZE:
                    first_data_time = time.time()

            ssl_sock.shutdown(socket.SHUT_WR)
            time.sleep(1)

    end_time = time.time()
    running_flag["active"] = False
    monitor_thread.join()

    connection_time = end_time - start_time
    first_data_latency = (
        first_data_time - start_time) if first_data_time else None
    save_benchmark("tcp", connection_time, stats,
                   len(full_data), first_data_latency)
    log(f"✅ Sent {total_sent} bytes in {connection_time:.2f} seconds", verbose)


async def start_quic_client(verbose=False):
    private_key, _ = load_or_generate_keys()
    data = b"x" * DATA_SIZE
    signature = sign_data(private_key, data)
    full_data = data + signature

    configuration = QuicConfiguration(is_client=True)
    configuration.verify_mode = ssl.CERT_NONE
    configuration.load_cert_chain(certfile=TLS_CERT)
    configuration.load_verify_locations(cafile=TLS_CERT)

    stats = []
    data_tracker = {"bytes": 0}
    running_flag = {"active": True}
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(0.1, running_flag, stats, data_tracker))
    monitor_thread.start()

    start_time = time.time()
    async with connect("127.0.0.1", 4443, configuration=configuration) as connection:
        stream_id = connection._quic.get_next_available_stream_id()
        total_sent = 0
        first_data_time = None

        while total_sent < len(full_data):
            end = min(total_sent + CHUNK_SIZE, len(full_data))
            chunk = full_data[total_sent:end]
            connection._quic.send_stream_data(
                stream_id, chunk, end_stream=False)
            chunk_size = len(chunk)
            total_sent += chunk_size
            data_tracker["bytes"] += chunk_size
            if first_data_time is None and total_sent >= CHUNK_SIZE:
                first_data_time = time.time()

        connection._quic.send_stream_data(stream_id, b"", end_stream=True)
        await connection.wait_closed()

    end_time = time.time()
    running_flag["active"] = False
    monitor_thread.join()

    connection_time = end_time - start_time
    first_data_latency = (
        first_data_time - start_time) if first_data_time else None
    save_benchmark("quic", connection_time, stats,
                   len(full_data), first_data_latency)
    log(f"✅ Sent {total_sent} bytes in {connection_time:.2f} seconds", verbose)


def run_client(protocol='tcp', verbose=False):
    if protocol == 'tcp':
        start_tcp_client(verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_client(verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TCP/QUIC client")
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")
    args = parser.parse_args()
    run_client(protocol=args.protocol, verbose=args.verbose)
