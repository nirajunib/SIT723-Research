import socket
import time
import psutil
import threading
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from dilithium_py.ml_dsa import ML_DSA_44
import matplotlib.pyplot as plt

public_key, private_key = ML_DSA_44.keygen()

HOST = "127.0.0.1"
PORT = 65432
CHUNK_SIZE = 1024 * 1024  # 1MB
MESSAGE_SIZE = 50 * 1024 * 1024  # 500MB
MAX_REQUESTS = 3  # Stop server after this for benchmarking

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)

print(f"[SERVER]  📡  Listening on {HOST}:{PORT}")

process = psutil.Process()
cpu_mem_log = []
request_times = []
monitoring = False
request_counter = 0  # Track number of requests


def monitor_usage():
    """Tracks CPU and memory usage in real-time."""
    global monitoring
    while monitoring:
        cpu = process.cpu_percent(interval=0.1)
        mem = process.memory_info().rss / (1024 * 1024)  # MB
        cpu_mem_log.append((time.time(), cpu, mem))
        print(f"[SERVER]  🖥️  CPU: {cpu:.2f}% | RAM: {mem:.2f} MB")
        time.sleep(0.1)


def handle_client(conn, addr, request_id):
    """Handles a client request with detailed benchmarking."""
    global monitoring, request_counter
    print(
        f"\n[SERVER]  🔗  Connection from {addr} (Request ID: {request_id+1})")

    monitoring = True
    monitor_thread = threading.Thread(target=monitor_usage)
    monitor_thread.start()

    handshake_start = time.time()
    conn.sendall(public_key)

    data = bytearray()
    while len(data) < MESSAGE_SIZE:
        chunk = conn.recv(CHUNK_SIZE)
        if not chunk:
            break
        data.extend(chunk)

    handshake_end = time.time()

    signing_start = time.time()
    # signature = ML_DSA_44.sign(private_key, bytes(data))
    signature = ML_DSA_44.sign(private_key, data)
    print(f"Data Received: {len(data)} bytes")
    signing_end = time.time()

    conn.sendall(signature)
    conn.close()
    monitoring = False
    monitor_thread.join()

    total_duration = signing_end - handshake_start
    throughput = (len(data) / (1024 * 1024)) / total_duration

    request_times.append((request_id + 1, total_duration, throughput))
    print(
        f"[SERVER]  ✅  Request {request_id+1} completed | Time: {total_duration:.2f}s | Throughput: {throughput:.2f} MB/s")

    request_counter += 1


with ThreadPoolExecutor(max_workers=5) as executor:
    request_id = 0
    while request_id < 3:  # Stop after 3 requests for benchmarking
        conn, addr = server.accept()
        executor.submit(handle_client, conn, addr, request_id)
        request_id += 1

print("\n[SERVER]  🚀  Benchmarking completed! Generating plots...")

# Extract CPU and memory usage logs
if cpu_mem_log:
    timestamps, cpu_usage, mem_usage = zip(*cpu_mem_log)
    timestamps = np.array(timestamps) - timestamps[0]

    # Plot CPU and Memory Usage
    plt.figure(figsize=(10, 5))
    plt.subplot(2, 1, 1)
    plt.plot(timestamps, cpu_usage, label="CPU Usage (%)", color="red")
    plt.xlabel("Time (s)")
    plt.ylabel("CPU (%)")
    plt.legend()
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.plot(timestamps, mem_usage, label="Memory Usage (MB)", color="blue")
    plt.xlabel("Time (s)")
    plt.ylabel("Memory (MB)")
    plt.legend()
    plt.grid()

    plt.suptitle("Server CPU and Memory Usage Over Time")
    plt.show()

# Plot request completion times
if request_times:
    req_ids, durations, throughputs = zip(*request_times)

    plt.figure(figsize=(10, 4))
    plt.bar(req_ids, durations, color="green")
    plt.xlabel("Request ID")
    plt.ylabel("Completion Time (s)")
    plt.xticks(req_ids)
    plt.title("Server Request Completion Times")
    plt.grid()
    plt.show()

    plt.figure(figsize=(10, 4))
    plt.bar(req_ids, throughputs, color="purple")
    plt.xlabel("Request ID")
    plt.ylabel("Throughput (MB/s)")
    plt.xticks(req_ids)
    plt.title("Server Throughput per Request")
    plt.grid()
    plt.show()
1
