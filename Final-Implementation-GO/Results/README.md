### Packet Loss Simulation
```bash
sudo tc qdisc del dev enp0s3 root && sudo tc qdisc add dev enp0s3 root netem loss 5%
sudo tc qdisc del dev enp0s3 root && sudo tc qdisc add dev enp0s3 root netem loss 10%
sudo tc qdisc del dev enp0s3 root && sudo tc qdisc add dev enp0s3 root netem loss 20%
sudo tc qdisc del dev enp0s3 root && sudo tc qdisc add dev enp0s3 root netem loss 40%
```

## MLDSA TCP (Mean)
```csv
Packet Loss (%), Handshake (ms)
5, 8.4130
10, 35.8334
20, 109.7051
40, 400.2101
```

## MLDSA QUIC (Mean)
```csv
Packet Loss (%), Handshake (ms)
5, 10.1398
10, 23.6088
20, 117.2675
40, 412.4862
```