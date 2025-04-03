import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dilithium_py.ml_dsa import ML_DSA_44

# Generate a key pair once and reuse it
public_key, private_key = ML_DSA_44.keygen()

# server setup
HOST = "127.0.0.1"
PORT = 65432

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)

print(f"Server listening on {HOST}:{PORT}")


def handle_client(conn, addr):
    """Handles each client connection"""
    print(f"Connection from {addr}")

    # Send the public key
    conn.sendall(public_key)

    # Receive message
    data = conn.recv(1024)
    if not data:
        conn.close()
        return

    print(f"Received: {data.decode()}")

    start_time = time.time()
    signature = ML_DSA_44.sign(private_key, data)  # Sign the message
    end_time = time.time()

    signing_time = (end_time - start_time) * 1000  # Convert to milliseconds
    print(f"Signing Time: {signing_time:.4f} ms")

    conn.sendall(signature)  # Send the signature back
    conn.close()


# multithreading for concurrent connections
with ThreadPoolExecutor(max_workers=10) as executor:
    while True:
        conn, addr = server.accept()
        executor.submit(handle_client, conn, addr)
