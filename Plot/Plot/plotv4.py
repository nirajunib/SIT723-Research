import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# Setup
base_dir = "Output"
output_dir = "plots"
os.makedirs(output_dir, exist_ok=True)

# Definitions
configs = {
    "Output-Server": {
        "rsa": "server_benchmarks_rsa",
        "mldsa": "server_benchmarks_mldsa"
    },
    "Output-Client": {
        "rsa": "client_benchmarks_rsa",
        "mldsa": "client_benchmarks_mldsa"
    }
}
protocols = ["tcp", "quic"]

# Data structure to collect relevant info
data = {
    "rsa_tcp": [],
    "rsa_quic": [],
    "mldsa_tcp": [],
    "mldsa_quic": []
}

# Helper to load csvs


def load_data(path):
    files = glob.glob(os.path.join(path, "*.csv"))
    latest_file = max(files, key=os.path.getctime)
    return pd.read_csv(latest_file)


# Gather data
for role in configs:
    for algo in configs[role]:
        for proto in protocols:
            key = f"{algo}_{proto}"
            folder = os.path.join(
                base_dir, role, "Output", configs[role][algo])
            files = glob.glob(os.path.join(folder, f"{proto}_*.csv"))
            if not files:
                continue
            latest_file = max(files, key=os.path.getctime)
            df = pd.read_csv(latest_file)
            data[key].append(df)

# Combine client and server data by averaging
combined = {}
for key, dfs in data.items():
    if not dfs:
        continue
    combined_df = pd.concat(dfs).groupby(level=0).mean(numeric_only=True)
    combined[key] = combined_df

# Plot 1: CPU Usage
plt.figure(figsize=(10, 6))
for key, df in combined.items():
    plt.plot(df["Time(s)"], df["CPU (%)"], label=key.replace('_', ' ').upper())
plt.xlabel("Time (s)")
plt.ylabel("CPU Usage (%)")
plt.title("CPU Usage over Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "cpu_usage.png"))
plt.close()

# Plot 2: Memory Usage
plt.figure(figsize=(10, 6))
for key, df in combined.items():
    plt.plot(df["Time(s)"], df["Memory (MB)"],
             label=key.replace('_', ' ').upper())
plt.xlabel("Time (s)")
plt.ylabel("Memory Usage (MB)")
plt.title("Memory Usage over Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "memory_usage.png"))
plt.close()

# Bar Chart Helpers
labels = list(combined.keys())
conn_times = [combined[k]["Connection Time(s)"].mean() for k in labels]
throughputs = [combined[k]["Throughput (MB/s)"].mean() for k in labels]

# Plot 3: Connection Time
plt.figure(figsize=(10, 6))
plt.bar(labels, conn_times, color=['blue', 'orange', 'green', 'red'])
plt.ylabel("Connection Time (s)")
plt.title("Average Connection Time")
plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "connection_time.png"))
plt.close()

# Plot 4: Throughput
plt.figure(figsize=(10, 6))
plt.bar(labels, throughputs, color=['blue', 'orange', 'green', 'red'])
plt.ylabel("Throughput (MB/s)")
plt.title("Average Throughput")
plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "throughput.png"))
plt.close()
