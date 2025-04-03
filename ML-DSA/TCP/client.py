import socket
import time
import threading
from dilithium_py.ml_dsa import ML_DSA_44

HOST = "127.0.0.1"
PORT = 65432
NUM_REQUESTS = 10  # Number of messages to send


def send_message():
    """Sends a message and measures latency"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    # Receive the public key from the server
    public_key = client.recv(2592)

    message = b"Benchmarking ML-DSA TCP Server"
    client.sendall(message)

    start_time = time.time()
    signature = client.recv(2420)
    end_time = time.time()

    verification_start = time.time()
    is_valid = ML_DSA_44.verify(public_key, message, signature)
    verification_end = time.time()

    client.close()

    signing_latency = (end_time - start_time) * 1000  # Convert to ms
    verification_latency = (verification_end - verification_start) * 1000

    print(
        f"Signing Time: {signing_latency:.4f} ms | Verification Time: {verification_latency:.4f} ms | Valid: {is_valid}")


# Run multiple clients in parallel
threads = []
for _ in range(NUM_REQUESTS):
    thread = threading.Thread(target=send_message)
    thread.start()
    threads.append(thread)

# Wait for all threads to finish
for thread in threads:
    thread.join()

print("Benchmarking completed!")
