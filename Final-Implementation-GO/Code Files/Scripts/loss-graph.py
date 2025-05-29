import matplotlib.pyplot as plt

# Data
packet_loss = [5, 10, 20, 40]
tcp_handshake = [8.4130, 35.8334, 109.7051, 400.2101]
quic_handshake = [10.1398, 23.6088, 117.2675, 412.4862]

# Common settings
x_ticks = list(range(0, 41, 10))  # 0 to 40 with step 10
y_ticks = list(range(0, 420, 100))  # 0 to 400 with step 100

# Create a single plot
plt.figure(figsize=(8, 6))

# Plot ML-DSA TCP (solid blue line)
plt.plot(packet_loss, tcp_handshake, marker='o',
         linestyle='-', color='blue', label='ML-DSA TCP')

# Plot ML-DSA QUIC (dashed red line)
plt.plot(packet_loss, quic_handshake, marker='o',
         linestyle='--', color='red', label='ML-DSA QUIC')

# Add title and labels
plt.title('ML-DSA Handshake Time Comparison')
plt.xlabel('Packet Loss (%)')
plt.ylabel('Handshake Time (ms)')
plt.xticks(x_ticks)
plt.yticks(y_ticks)

# Add grid and legend
plt.grid(True)
plt.legend()

# Save and show the plot
plt.tight_layout()
plt.savefig('ml_dsa_tcp_quic_combined.png')
plt.show()
