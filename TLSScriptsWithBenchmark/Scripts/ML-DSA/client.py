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

# BENCHMARKING
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

# BENCHMARKING: Resource monitoring function


def monitor_resources(interval, running_flag, stats_list):
    process = psutil.Process()
    start_time = time.time()

    while running_flag["active"]:
        cpu = process.cpu_percent(interval=None)
        mem = process.memory_info().rss / (1024 * 1024)
        timestamp = time.time() - start_time
        stats_list.append((timestamp, cpu, mem))
        time.sleep(interval)

# BENCHMARKING: Save benchmark data to CSV


def save_benchmark(protocol, connection_time, stats_list, signed_msg_size):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = os.path.join(
        BENCHMARK_DIR, f"{protocol}_dilithium_{timestamp}.csv")
    throughput = signed_msg_size / (1024 * 1024) / connection_time

    with open(file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time(s)", "CPU (%)", "Memory (MB)", "Connection Time(s)",
                        "Signed Message Size (bytes)", "Throughput (MB/s)"])
        for row in stats_list:
            writer.writerow(
                [*row, connection_time, signed_msg_size, throughput])


def start_tcp_client(verbose=False):
    generate_keys_if_missing(verbose)
    private_key = load_private_key()
    data = b"x" * DATA_SIZE
    signature = ML_DSA_44.sign(private_key, data)

    stats = []
    running_flag = {"active": True}
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(0.1, running_flag, stats))
    monitor_thread.start()

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.load_verify_locations(cafile=TLS_CERT)
    context.load_cert_chain(certfile="server.pem", keyfile="server_key.pem")
    # context.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    start_time = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 4444))
        with context.wrap_socket(s, server_hostname="127.0.0.1") as tls_sock:
            log("Connected to TLS TCP server.", verbose)
            tls_sock.send(len(signature).to_bytes(4, "big"))
            tls_sock.send(signature)

            total_sent = 0
            while total_sent < len(data):
                end = min(total_sent + CHUNK_SIZE, len(data))
                sent = tls_sock.send(data[total_sent:end])
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent

            #  Clean shutdown
            tls_sock.shutdown(socket.SHUT_WR)
            time.sleep(1)

    end_time = time.time()
    running_flag["active"] = False
    monitor_thread.join()

    connection_time = end_time - start_time
    save_benchmark("tcp", connection_time, stats, len(data) + len(signature))
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
    running_flag = {"active": True}
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(0.1, running_flag, stats))
    monitor_thread.start()

    start_time = time.time()
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
            total_sent += end - total_sent

        conn._quic.send_stream_data(stream_id, b"", end_stream=True)
        await conn.wait_closed()

    end_time = time.time()
    running_flag["active"] = False
    monitor_thread.join()

    connection_time = end_time - start_time
    save_benchmark("quic", connection_time, stats, len(data) + len(signature))
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
