## Dependencies
sudo apt instal python3-pip
pip3 install aioquic dilithium-py
sudo apt install htop
sudo apt install iperf3s

## generate SSL certificates for QUIC (cert.pem and key.pem)
rm *.pem && openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -config openssl.cnf
