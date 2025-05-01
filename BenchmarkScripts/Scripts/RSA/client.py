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

DATA_SIZE = 15 * 1024 * 1024
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
PRIVATE_KEY_FILE = "client_private.pem"
PUBLIC_KEY_FILE = "client_public.pem"

# BENCHMARKING
BENCHMARK_DIR = "client_benchmarks"
os.makedirs(BENCHMARK_DIR, exist_ok=True)


def log(msg, verbose=True):
    """Print log messages if verbose flag is True."""
    if verbose:
        print(f"[CLIENT] {msg}")


def load_or_generate_keys():
    """Load or generate RSA keys for the client."""
    if Path(PRIVATE_KEY_FILE).exists() and Path(PUBLIC_KEY_FILE).exists():
        private_key = RSA.import_key(Path(PRIVATE_KEY_FILE).read_bytes())
        return private_key, private_key.publickey()

    private_key = RSA.generate(2048)
    Path(PRIVATE_KEY_FILE).write_bytes(private_key.export_key())
    Path(PUBLIC_KEY_FILE).write_bytes(private_key.publickey().export_key())
    return private_key, private_key.publickey()


def sign_data(private_key, data):
    """Sign data using the client's private key."""
    h = SHA256.new(data)
    return pkcs1_15.new(private_key).sign(h)

# BENCHMARKING: Resource monitoring function


def monitor_resources(interval, running_flag, stats_list):
    """Monitor CPU and memory usage during the benchmark."""
    process = psutil.Process()
    start_time = time.time()

    while running_flag["active"]:
        cpu = process.cpu_percent(interval=None)
        mem = process.memory_info().rss / (1024 * 1024)  # in MB
        timestamp = time.time() - start_time
        stats_list.append((timestamp, cpu, mem))
        time.sleep(interval)

# BENCHMARKING: Save benchmark data to CSV


def save_benchmark(protocol, connection_time, stats_list, signed_msg_size):
    """Save the benchmarking results to a CSV file."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = os.path.join(BENCHMARK_DIR, f"{protocol}_{timestamp}.csv")
    throughput = signed_msg_size / (1024 * 1024) / connection_time  # in MB/s

    with open(file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time(s)", "CPU (%)", "Memory (MB)", "Connection Time(s)",
                        "Signed Message Size (bytes)", "Throughput (MB/s)"])
        for row in stats_list:
            writer.writerow(
                [*row, connection_time, signed_msg_size, throughput])


def start_tcp_client(verbose=False):
    """Start the TCP client."""
    private_key, _ = load_or_generate_keys()
    data = b"x" * DATA_SIZE
    signature = sign_data(private_key, data)
    full_data = data + signature

    stats = []  # BENCHMARKING
    running_flag = {"active": True}
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(0.1, running_flag, stats))
    monitor_thread.start()

    start_time = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 4444))
        log("Connected to TCP server", verbose)

        total_sent = 0
        while total_sent < len(full_data):
            end = min(total_sent + CHUNK_SIZE, len(full_data))
            sent = s.send(full_data[total_sent:end])
            total_sent += sent

        end_time = time.time()
        running_flag["active"] = False
        monitor_thread.join()

        connection_time = end_time - start_time
        save_benchmark("tcp", connection_time, stats, len(full_data))
        log(f"✅ Sent {total_sent} bytes in {connection_time:.2f} seconds", verbose)


async def start_quic_client(verbose=False):
    """Start the QUIC client."""
    private_key, _ = load_or_generate_keys()
    data = b"x" * DATA_SIZE
    signature = sign_data(private_key, data)
    full_data = data + signature

    # QUIC Configuration
    configuration = QuicConfiguration(is_client=True)
    # Don't verify server certificate for testing
    configuration.verify_mode = ssl.CERT_NONE
    configuration.load_cert_chain(certfile=TLS_CERT)
    configuration.load_verify_locations(cafile=TLS_CERT)

    stats = []  # BENCHMARKING
    running_flag = {"active": True}
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(0.1, running_flag, stats))
    monitor_thread.start()

    start_time = time.time()
    async with connect("127.0.0.1", 443, configuration=configuration) as connection:
        stream_id = connection._quic.get_next_available_stream_id()
        total_sent = 0

        while total_sent < len(full_data):
            end = min(total_sent + CHUNK_SIZE, len(full_data))
            connection._quic.send_stream_data(
                stream_id, full_data[total_sent:end], end_stream=False)
            total_sent += end - total_sent

        connection._quic.send_stream_data(stream_id, b"", end_stream=True)
        await connection.wait_closed()

    end_time = time.time()
    running_flag["active"] = False
    monitor_thread.join()

    connection_time = end_time - start_time
    save_benchmark("quic", connection_time, stats, len(full_data))
    log(f"✅ Sent {total_sent} bytes in {connection_time:.2f} seconds", verbose)


def run_client(protocol='tcp', verbose=False):
    """Run the client based on the specified protocol."""
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
