def start_tcp_server(verbose=False):
    public_key = load_client_public_key()

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    stats = []  # BENCHMARK
    running_flag = {"active": True}  # BENCHMARK
    monitor_thread = threading.Thread(
        target=monitor_resources,
        args=(0.1, running_flag, stats))
    monitor_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 4444))
        s.listen(1)
        log("TCP server is listening on port 4444", verbose)

        conn, addr = s.accept()
        with context.wrap_socket(conn, server_side=True) as ssl_conn:
            log(f"✅ TCP TLS connection accepted from {addr}", verbose)

            start_time = time.time()

            received = b""
            while len(received) < DATA_SIZE + 256:  # Expecting data size + signature
                chunk = ssl_conn.recv(4096)
                if not chunk:
                    log(f"❌ Connection closed unexpectedly before receiving all data.", verbose)
                    break
                received += chunk

            end_time = time.time()
            running_flag["active"] = False  # BENCHMARK
            monitor_thread.join()  # BENCHMARK

            connection_time = end_time - start_time

            if len(received) == DATA_SIZE + 256:
                data = received[:-256]
                signature = received[-256:]
                try:
                    verify_signature(public_key, data, signature)
                    log(f"✅ Data verified. {len(data)} bytes")
                except Exception as e:
                    log(f"❌ Signature verification failed: {e}")

                save_benchmark("tcp", connection_time, stats, len(data) + len(signature))  # BENCHMARK

            else:
                log(
                    f"❌ Data received is incomplete. Expected {DATA_SIZE + 256} bytes but got {len(received)} bytes.", verbose)
