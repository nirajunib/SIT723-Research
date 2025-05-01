import ssl
import socket
import asyncio
import argparse
import time
import os
import csv
import threading
import psutil  # Benchmarking
from dilithium_py.ml_dsa import ML_DSA_44
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, HandshakeCompleted

DATA_SIZE = 8 * 1024 * 1024  # 5MB
CHUNK_SIZE = 4096
TLS_CERT = "server.crt"
TLS_KEY = "server.key"
PUBLIC_KEY_PATH = "client_keys/dilithium_public.key"

# Benchmarking directory
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


def monitor_resources(interval, running_flag, stats_list):
    process = psutil.Process()
    start_time = time.time()
    while running_flag["active"]:
        cpu = process.cpu_percent(interval=None)
        mem = process.memory_info().rss / (1024 * 1024)
        timestamp = time.time() - start_time
        stats_list.append((timestamp, cpu, mem))
        time.sleep(interval)


def save_benchmark(protocol, connection_time, stats_list, signed_msg_size):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = os.path.join(BENCHMARK_DIR, f"{protocol}_{timestamp}.csv")
    throughput = signed_msg_size / (1024 * 1024) / connection_time  # MB/s

    with open(file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time(s)", "CPU (%)", "Memory (MB)", "Connection Time(s)",
                        "Signed Message Size (bytes)", "Throughput (MB/s)"])
        for row in stats_list:
            writer.writerow(
                [*row, connection_time, signed_msg_size, throughput])


def start_tcp_server(verbose=False):
    public_key = load_public_key()

    stats = []
    running_flag = {"active": True}
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(0.1, running_flag, stats))
    monitor_thread.start()

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # context.load_cert_chain(certfile="server.pem", keyfile="server_key.pem")
    context.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 4444))
        s.listen(1)
        log("TCP TLS server listening on port 4444", verbose)
        conn, addr = s.accept()
        with context.wrap_socket(conn, server_side=True) as tls_conn:
            log(f"Accepted TLS connection from {addr}", verbose)
            sig_len = int.from_bytes(tls_conn.recv(4), "big")
            signature = tls_conn.recv(sig_len)

            received = b""
            start_time = time.time()
            while len(received) < DATA_SIZE:
                chunk = tls_conn.recv(CHUNK_SIZE)
                if not chunk:
                    break
                received += chunk
            end_time = time.time()
            running_flag["active"] = False
            monitor_thread.join()

            connection_time = end_time - start_time
            total_size = len(received) + len(signature) + 4
            save_benchmark("tcp", connection_time, stats, total_size)

            try:
                ML_DSA_44.verify(public_key, signature, received)
                log(
                    f"✅ Signature verified. Received {len(received)} bytes in {connection_time:.2f}s", verbose)
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

        # Benchmarking
        self.stats = []
        self.running_flag = {"active": True}
        self.monitor_thread = threading.Thread(
            target=monitor_resources, args=(0.1, self.running_flag, self.stats))
        self.monitor_thread.start()
        self.handshake_start_time = time.time()

    def log(self, msg):
        if self.verbose:
            print(f"[SERVER-QUIC] {msg}")

    def quic_event_received(self, event):
        if isinstance(event, HandshakeCompleted):
            self.log("✅ TLS handshake completed.")
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
                end_time = time.time()
                self.running_flag["active"] = False
                self.monitor_thread.join()

                connection_time = end_time - self.handshake_start_time
                total_size = len(self.received) + len(self.signature) + 4
                save_benchmark("quic", connection_time, self.stats, total_size)

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
