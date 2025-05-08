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
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, HandshakeCompleted

# Constants
DATA_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
TLS_KEY = "server.key"
PUBLIC_KEY_PATH = "client_keys/dilithium_public.key"

BENCHMARK_DIR = "server_benchmarks"
os.makedirs(BENCHMARK_DIR, exist_ok=True)


def log(msg, verbose=True):
    if verbose:
        print(f"[SERVER] {msg}")


def load_public_key():
    if not os.path.exists(PUBLIC_KEY_PATH):
        raise FileNotFoundError("Missing client public key.")
    with open(PUBLIC_KEY_PATH, "rb") as f:
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
    file_path = os.path.join(BENCHMARK_DIR, f"{protocol}_{timestamp}.csv")
    with open(file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time(s)", "CPU (%)", "Memory (MB)", "Throughput (MB/s)",
                         "Connection Time(s)", "Signed Message Size (bytes)", "First Data Latency (s)"])
        for row in stats_list:
            writer.writerow(
                [*row, connection_time, signed_msg_size, first_data_latency])


def start_tcp_server(verbose=False):
    public_key = load_public_key()

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 4444))
        s.listen(1)
        log("TCP TLS server listening on port 4444", verbose)
        conn, addr = s.accept()
        with context.wrap_socket(conn, server_side=True) as tls_conn:
            log(f"Accepted TLS connection from {addr}", verbose)

            stats = []
            running_flag = {"active": True}
            data_tracker = {"bytes": 0}
            monitor_thread = threading.Thread(
                target=monitor_resources, args=(0.1, running_flag, stats, data_tracker))
            monitor_thread.start()

            sig_len = int.from_bytes(tls_conn.recv(4), "big")
            signature = tls_conn.recv(sig_len)

            received = b""
            start_time = time.time()
            first_data_time = None

            while len(received) < DATA_SIZE:
                chunk = tls_conn.recv(CHUNK_SIZE)
                if not chunk:
                    break
                received += chunk
                data_tracker["bytes"] += len(chunk)
                if first_data_time is None and len(received) >= CHUNK_SIZE:
                    first_data_time = time.time()
                # Yield control to allow monitoring thread to run
                time.sleep(0)

            end_time = time.time()
            running_flag["active"] = False
            monitor_thread.join()

            connection_time = end_time - start_time
            first_data_latency = (
                first_data_time - start_time) if first_data_time else None
            total_size = len(received) + len(signature) + 4

            save_benchmark("tcp", connection_time, stats,
                           total_size, first_data_latency)

            try:
                ML_DSA_44.verify(public_key, signature, received)
                log(
                    f"✅ Signature verified. Received {len(received)} bytes in {connection_time:.2f}s", verbose)
            except Exception as e:
                log(f"❌ Signature verification failed: {e}", verbose)


# ---------- QUIC --------------

class MyQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, verbose=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = verbose
        self.public_key = load_public_key()
        self.sig_len = None
        self.signature = b""
        self.received = b""
        self.start_time = None
        self.first_data_time = None
        self.handshake_end_time = None

        self.stats = []
        self.data_tracker = {"bytes": 0}
        self.running_flag = {"active": True}
        self.monitor_thread = None

    def log(self, msg):
        if self.verbose:
            print(f"[SERVER-QUIC] {msg}")

    def quic_event_received(self, event):
        if isinstance(event, HandshakeCompleted):
            self.log("✅ TLS handshake completed.")
            self.handshake_end_time = time.time()

            self.monitor_thread = threading.Thread(
                target=monitor_resources, args=(0.1, self.running_flag, self.stats, self.data_tracker))
            self.monitor_thread.start()

        elif isinstance(event, StreamDataReceived):
            self.received += event.data
            self.data_tracker["bytes"] += len(event.data)

            if self.sig_len is None and len(self.received) >= 4:
                self.sig_len = int.from_bytes(self.received[:4], "big")
                self.received = self.received[4:]
                self.log(f"Signature length: {self.sig_len} bytes")

            if self.sig_len is not None and len(self.signature) < self.sig_len:
                needed = self.sig_len - len(self.signature)
                self.signature += self.received[:needed]
                self.received = self.received[needed:]

            # Set first_data_time only after receiving the first full data chunk (excluding signature)
            if self.first_data_time is None and self.sig_len is not None and len(self.received) >= CHUNK_SIZE:
                self.first_data_time = time.time()
            time.sleep(0)  # Yield control to allow monitoring thread to run

            if self.sig_len is not None and len(self.received) >= DATA_SIZE:
                end_time = time.time()
                self.running_flag["active"] = False
                if self.monitor_thread:
                    self.monitor_thread.join()

                connection_time = end_time - self.handshake_end_time
                first_data_latency = (
                    self.first_data_time - self.handshake_end_time) if self.first_data_time else None
                total_size = len(self.received) + len(self.signature) + 4

                save_benchmark("quic", connection_time, self.stats,
                               total_size, first_data_latency)

                try:
                    ML_DSA_44.verify(
                        self.public_key, self.signature, self.received)
                    self.log(
                        f"✅ QUIC: Signature verified. Received {len(self.received)} bytes in {connection_time:.2f}s")
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
