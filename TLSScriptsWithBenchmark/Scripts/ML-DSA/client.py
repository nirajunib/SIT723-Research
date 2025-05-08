import ssl
import socket
import asyncio
import argparse
import time
import os
import csv
import threading
import psutil
from dilithium_py.ml_dsa import ML_DSA_44
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

DATA_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
PRIVATE_KEY_PATH = "client_keys/dilithium_private.key"
PUBLIC_KEY_PATH = "client_keys/dilithium_public.key"

BENCHMARK_DIR = "client_benchmarks"
os.makedirs(BENCHMARK_DIR, exist_ok=True)


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
    file_path = os.path.join(
        BENCHMARK_DIR, f"{protocol}_dilithium_{timestamp}.csv")
    with open(file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time(s)", "CPU (%)", "Memory (MB)", "Throughput (MB/s)",
                         "Connection Time(s)", "Signed Message Size (bytes)", "First Data Latency (s)"])
        for row in stats_list:
            writer.writerow(
                [*row, connection_time, signed_msg_size, first_data_latency])


def start_tcp_client(verbose=False):
    generate_keys_if_missing(verbose)
    private_key = load_private_key()
    data = b"x" * DATA_SIZE
    signature = ML_DSA_44.sign(private_key, data)

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.load_verify_locations(cafile=TLS_CERT)

    stats = []
    data_tracker = {"bytes": 0}
    running_flag = {"active": True}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 4444))
        with context.wrap_socket(s, server_hostname="localhost") as tls_sock:
            log("Connected to TLS TCP server.", verbose)

            # Start timing *after* TLS handshake
            start_time = time.time()
            monitor_thread = threading.Thread(
                target=monitor_resources, args=(0.1, running_flag, stats, data_tracker))
            monitor_thread.start()

            tls_sock.send(len(signature).to_bytes(4, "big"))
            tls_sock.send(signature)

            total_sent = 0
            first_data_time = None
            while total_sent < len(data):
                end = min(total_sent + CHUNK_SIZE, len(data))
                sent = tls_sock.send(data[total_sent:end])
                time.sleep(0)  # yield to allow monitoring thread to observe
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent
                data_tracker["bytes"] += sent
                # Only set first_data_time after sending at least 1 full CHUNK_SIZE
                if first_data_time is None and total_sent >= CHUNK_SIZE:
                    first_data_time = time.time()

            tls_sock.shutdown(socket.SHUT_WR)
            # time.sleep(1)

    end_time = time.time()
    running_flag["active"] = False
    monitor_thread.join()

    connection_time = end_time - start_time
    first_data_latency = (
        first_data_time - start_time) if first_data_time else None
    save_benchmark("tcp", connection_time, stats, len(
        data) + len(signature), first_data_latency)

    log(f"✅ Sent {total_sent + len(signature)} bytes in {connection_time:.2f} seconds", verbose)


async def start_quic_client(verbose=False):
    generate_keys_if_missing(verbose)
    private_key = load_private_key()
    data = b"x" * DATA_SIZE
    signature = ML_DSA_44.sign(private_key, data)

    config = QuicConfiguration(is_client=True)
    config.load_cert_chain(certfile=TLS_CERT)
    config.verify_mode = ssl.CERT_NONE

    stats = []
    data_tracker = {"bytes": 0}
    running_flag = {"active": True}

    log("Connecting to QUIC server...", verbose)
    async with connect("127.0.0.1", 4443, configuration=config) as conn:
        await conn.wait_connected()
        log("QUIC handshake complete.", verbose)

        start_time = time.time()
        monitor_thread = threading.Thread(
            target=monitor_resources, args=(0.1, running_flag, stats, data_tracker))
        monitor_thread.start()

        stream_id = conn._quic.get_next_available_stream_id()
        conn._quic.send_stream_data(stream_id, len(signature).to_bytes(
            4, "big") + signature, end_stream=False)

        total_sent = 0
        first_data_time = None
        while total_sent < len(data):
            end = min(total_sent + CHUNK_SIZE, len(data))
            conn._quic.send_stream_data(
                stream_id, data[total_sent:end], end_stream=False)
            time.sleep(0)  # yield to allow monitoring thread to observe
            chunk_size = end - total_sent
            total_sent += chunk_size
            data_tracker["bytes"] += chunk_size
            # Only set first_data_time after sending at least 1 full CHUNK_SIZE
            if first_data_time is None and total_sent >= CHUNK_SIZE:
                first_data_time = time.time()

        conn._quic.send_stream_data(stream_id, b"", end_stream=True)
        await conn.wait_closed()

    end_time = time.time()
    running_flag["active"] = False
    monitor_thread.join()

    connection_time = end_time - start_time
    first_data_latency = (
        first_data_time - start_time) if first_data_time else None
    save_benchmark("quic", connection_time, stats, len(
        data) + len(signature), first_data_latency)

    log(f"✅ Sent {total_sent + len(signature)} bytes in {connection_time:.2f} seconds", verbose)


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
