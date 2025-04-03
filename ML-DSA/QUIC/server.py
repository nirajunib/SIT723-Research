import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived
from dilithium_py.ml_dsa import ML_DSA_44

# Generate ML-DSA key pair
public_key, private_key = ML_DSA_44.keygen()


class MLDSAQuicServer(QuicConnectionProtocol):
    def quic_event_received(self, event):
        """Handles QUIC stream events"""
        if isinstance(event, StreamDataReceived):
            message = event.data
            print(f"Received: {message.decode()}")

            # Measure signing time
            start_time = time.time()
            signature = ML_DSA_44.sign(private_key, message)
            signing_time = (time.time() - start_time) * 1000  # Convert to ms
            print(f"Signing Time: {signing_time:.4f} ms")

            # Send public key and signature back
            response = public_key + b'||' + signature
            self._quic.send_stream_data(event.stream_id, response)


async def main():
    configuration = QuicConfiguration(is_client=False)
    configuration.load_cert_chain("cert.pem", "key.pem")

    # Start QUIC server
    server = await serve(
        host="127.0.0.1",
        port=4433,
        configuration=configuration,
        create_protocol=MLDSAQuicServer
    )

    print("QUIC Server listening on 127.0.0.1:4433")
    await asyncio.Future()  # keeps server running

if __name__ == "__main__":
    asyncio.run(main())
