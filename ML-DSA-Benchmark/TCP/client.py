import socket
import time
import psutil
import threading
import matplotlib.pyplot as plt
import numpy as np
from dilithium_py.ml_dsa import ML_DSA_44

HOST = "127.0.0.1"
PORT = 65432
NUM_REQUESTS = 3  # 3 concurrent requests
CHUNK_SIZE = 1024 * 1024  # 1MB
MESSAGE_SIZE = 50 * 1024 * 1024  # 500MB
LARGE_MESSAGE = b"A" * MESSAGE_SIZE

process = psutil.Process()
cpu_mem_log = []
request_times = []
monitoring = False


def monitor_usage():
    """Tracks CPU and memory usage in real-time."""
    global monitoring
    while monitoring:
        cpu = process.cpu_percent(interval=0.1)
        mem = process.memory_info().rss / (1024 * 1024)  # MB
        cpu_mem_log.append((time.time(), cpu, mem))
        print(f"[CLIENT]  🖥️  CPU: {cpu:.2f}% | RAM: {mem:.2f} MB")
        time.sleep(0.1)


def send_message(request_id):
    """Handles a client request with detailed benchmarking."""
    global monitoring
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print(f"\n[CLIENT-{request_id+1}]  🚀  Connecting to {HOST}:{PORT} ...")
    connection_start = time.time()
    client.connect((HOST, PORT))
    connection_end = time.time()

    monitoring = True
    monitor_thread = threading.Thread(target=monitor_usage)
    monitor_thread.start()

    key_receive_start = time.time()
    public_key = client.recv(2592)
    key_receive_end = time.time()

    message_send_start = time.time()
    for i in range(0, MESSAGE_SIZE, CHUNK_SIZE):
        client.sendall(LARGE_MESSAGE[i: i + CHUNK_SIZE])
    message_send_end = time.time()

    sig_receive_start = time.time()
    signature = client.recv(2420)
    sig_receive_end = time.time()

    verification_start = time.time()
    # is_valid = ML_DSA_44.verify(public_key, LARGE_MESSAGE, signature)
    is_valid = ML_DSA_44.verify(public_key, bytes(LARGE_MESSAGE), signature)

    verification_end = time.time()

    monitoring = False
    monitor_thread.join()

    # Compute metrics
    total_duration = sig_receive_end - connection_start
    throughput = (MESSAGE_SIZE / (1024 * 1024)) / total_duration

    request_times.append((request_id + 1, total_duration, throughput))

    print(f"[CLIENT-{request_id+1}]  ✅  Completed | Time: {total_duration:.2f}s | Throughput: {throughput:.2f} MB/s | Signature: {'✅  Valid' if is_valid else '❌  Invalid'}")


# Run multiple clients
threads = []
for i in range(NUM_REQUESTS):
    thread = threading.Thread(target=send_message, args=(i,))
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()

print("\n✅  Benchmarking completed!")

# Extract CPU and memory usage logs
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

plt.suptitle("Client CPU and Memory Usage Over Time")
plt.show()

# Plot request completion times
req_ids, durations, throughputs = zip(*request_times)

plt.figure(figsize=(10, 4))
plt.bar(req_ids, durations, color="green")
plt.xlabel("Request ID")
plt.ylabel("Completion Time (s)")
plt.xticks(req_ids)
plt.title("Client Request Completion Times")
plt.grid()
plt.show()

plt.figure(figsize=(10, 4))
plt.bar(req_ids, throughputs, color="purple")
plt.xlabel("Request ID")
plt.ylabel("Throughput (MB/s)")
plt.xticks(req_ids)
plt.title("Client Throughput per Request")
plt.grid()
plt.show()
