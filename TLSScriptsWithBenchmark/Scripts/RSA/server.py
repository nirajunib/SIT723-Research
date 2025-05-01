import socket
import asyncio
import argparse
import time
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
import os
import csv
import threading
import psutil  # BENCHMARK
from aioquic.quic.events import HandshakeCompleted, StreamDataReceived
import ssl  # TLS support for TCP

DATA_SIZE = 5 * 1024 * 1024
TLS_CERT = "server.crt"
TLS_KEY = "server.key"
PUBLIC_KEY_FILE = "client_public.pem"

# BENCHMARK
BENCHMARK_DIR = "server_benchmarks"
os.makedirs(BENCHMARK_DIR, exist_ok=True)


def log(msg, verbose=True):
    if verbose:
        print(f"[SERVER] {msg}")


def load_client_public_key():
    return RSA.import_key(Path(PUBLIC_KEY_FILE).read_bytes())


def verify_signature(public_key, data, signature):
    h = SHA256.new(data)
    pkcs1_15.new(public_key).verify(h, signature)

# BENCHMARK


def monitor_resources(interval, running_flag, stats_list):
    process = psutil.Process()
    start_time = time.time()
    while running_flag["active"]:
        cpu = process.cpu_percent(interval=None)
        mem = process.memory_info().rss / (1024 * 1024)
        timestamp = time.time() - start_time
        stats_list.append((timestamp, cpu, mem))
        time.sleep(interval)

# BENCHMARK


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
    public_key = load_client_public_key()

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 4444))
        s.listen(1)
        log("TCP server is listening on port 4444", verbose)

        conn, addr = s.accept()
        with context.wrap_socket(conn, server_side=True) as ssl_conn:
            log(f"✅ TCP TLS connection accepted from {addr}", verbose)

            received = b""
            while len(received) < DATA_SIZE + 256:  # Expecting data size + signature
                chunk = ssl_conn.recv(4096)
                if not chunk:
                    log(f"❌ Connection closed unexpectedly before receiving all data.", verbose)
                    break
                received += chunk
                # log(f"Received {len(received)} bytes so far...")

            # After receiving all data
            if len(received) == DATA_SIZE + 256:
                data = received[:-256]
                signature = received[-256:]
                try:
                    verify_signature(public_key, data, signature)
                    log(f"✅ Data verified. {len(data)} bytes")
                except Exception as e:
                    log(f"❌ Signature verification failed: {e}")
            else:
                log(
                    f"❌ Data received is incomplete. Expected {DATA_SIZE + 256} bytes but got {len(received)} bytes.", verbose)


class MyQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, verbose=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = verbose
        self.received = b""
        self.start_time = None
        self.public_key = load_client_public_key()

        # BENCHMARK
        self.stats = []
        self.running_flag = {"active": True}
        self.monitor_thread = threading.Thread(
            target=monitor_resources,
            args=(0.1, self.running_flag, self.stats))
        self.monitor_thread.start()

        #  Start handshake timing immediately on init
        self.handshake_start_time = time.time()
        self.handshake_end_time = None

    def log(self, msg):
        if self.verbose:
            print(f"[SERVER-QUIC] {msg}")

    def quic_event_received(self, event):
        if isinstance(event, HandshakeCompleted):
            self.handshake_end_time = time.time()
            self.log(f"✅ TLS Handshake completed.")

        elif isinstance(event, StreamDataReceived):
            if self.start_time is None:
                self.start_time = time.time()
                self.log("Connection started. Receiving data...")

            self.received += event.data

            if event.end_stream:
                connection_end_time = time.time()
                data = self.received[:-256]
                signature = self.received[-256:]

                self.running_flag["active"] = False
                self.monitor_thread.join()

                connection_time = connection_end_time - self.handshake_start_time
                save_benchmark("quic", connection_time,
                               self.stats, len(data) + len(signature))

                try:
                    verify_signature(self.public_key, data, signature)
                    self.log(
                        f"✅ QUIC: Data verified. {len(data)} bytes in {connection_time:.2f}s")
                except Exception as e:
                    self.log(f"❌ Signature verification failed: {e}")

                self._quic.close(error_code=0x0)


async def start_quic_server(verbose=False):
    config = QuicConfiguration(
        is_client=False, certificate=TLS_CERT, private_key=TLS_KEY)
    config.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    log("QUIC server starting with TLS...", verbose)
    await serve(
        "0.0.0.0", 443, configuration=config,
        create_protocol=lambda *args, **kwargs: MyQuicProtocol(
            *args, verbose=verbose, **kwargs)
    )
    await asyncio.Event().wait()


def run_server(protocol='tcp', verbose=False):
    if protocol == 'tcp':
        start_tcp_server(verbose)
    elif protocol == 'quic':
        asyncio.run(start_quic_server(verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TCP/QUIC server")
    parser.add_argument("--protocol", choices=["tcp", "quic"], required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run_server(protocol=args.protocol, verbose=args.verbose)
