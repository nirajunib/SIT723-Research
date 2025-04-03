import asyncio
import time
import ssl
import threading
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
from dilithium_py.ml_dsa import ML_DSA_44

HOST = "127.0.0.1"
PORT = 4433
NUM_REQUESTS = 10  # Number of concurrent requests


async def send_message():
    """Sends a message, measures latency, and verifies signature"""
    configuration = QuicConfiguration(is_client=True)
    configuration.verify_mode = ssl.CERT_NONE  # Disable certificate verification

    async with connect(HOST, PORT, configuration=configuration) as connection:
        reader, writer = await connection.create_stream()

        message = b"Benchmarking ML-DSA QUIC Server"

        # Measure sending latency (Client -> Server -> Client round trip)
        start_time = time.time()
        writer.write(message)

        response = await reader.read()
        end_time = time.time()

        # Extract public key and signature
        public_key, signature = response.split(b'||', 1)

        # Measure verification time
        verify_start = time.time()
        is_valid = ML_DSA_44.verify(public_key, message, signature)
        verify_end = time.time()

        # Compute time metrics
        round_trip_latency = (end_time - start_time) * 1000  # ms
        verification_latency = (verify_end - verify_start) * 1000  # ms

        print(
            f"RTT: {round_trip_latency:.4f} ms | Verification: {verification_latency:.4f} ms | Valid: {is_valid}")

# Run multiple clients in parallel using threads
threads = []
for _ in range(NUM_REQUESTS):
    thread = threading.Thread(target=lambda: asyncio.run(send_message()))
    thread.start()
    threads.append(thread)

# Wait for all threads to finish
for thread in threads:
    thread.join()

print("Benchmarking completed!")
