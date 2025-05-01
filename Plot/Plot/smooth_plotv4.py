import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# Setup
base_dir = "Output"
output_dir = "plots"
os.makedirs(output_dir, exist_ok=True)

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
window_size = 5

data = {
    "rsa_tcp": [],
    "rsa_quic": [],
    "mldsa_tcp": [],
    "mldsa_quic": []
}


def load_latest_csv(path, proto):
    files = glob.glob(os.path.join(path, f"{proto}_*.csv"))
    if not files:
        return None
    latest_file = max(files, key=os.path.getctime)
    return pd.read_csv(latest_file)


# Load CSVs
for role in configs:
    for algo in configs[role]:
        for proto in protocols:
            key = f"{algo}_{proto}"
            folder = os.path.join(
                base_dir, role, "Output", configs[role][algo])
            df = load_latest_csv(folder, proto)
            if df is not None:
                data[key].append(df)

# Normalize and smooth
combined = {}
for key, dfs in data.items():
    if not dfs:
        continue
    df = pd.concat(dfs).reset_index(drop=True)
    df = df.sort_values("Time(s)").reset_index(drop=True)
    df["CPU (%)"] = df["CPU (%)"].rolling(
        window=window_size, min_periods=1).mean()
    df["Memory (MB)"] = df["Memory (MB)"].rolling(
        window=window_size, min_periods=1).mean()
    combined[key] = df

# Line Plot: CPU Usage
plt.figure(figsize=(10, 6))
for key, df in combined.items():
    plt.plot(df["Time(s)"], df["CPU (%)"], label=key.replace('_', ' ').upper())
plt.xlabel("Time (s)")
plt.ylabel("CPU Usage (%)")
plt.title("Smoothed CPU Usage")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "cpu_usage_smoothed.png"))
plt.close()

# Line Plot: Memory Usage
plt.figure(figsize=(10, 6))
for key, df in combined.items():
    plt.plot(df["Time(s)"], df["Memory (MB)"],
             label=key.replace('_', ' ').upper())
plt.xlabel("Time (s)")
plt.ylabel("Memory Usage (MB)")
plt.title("Smoothed Memory Usage")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "memory_usage_smoothed.png"))
plt.close()

# Bar Chart: Connection Time
labels = list(combined.keys())
conn_times = [combined[k]["Connection Time(s)"].mean() for k in labels]
plt.figure(figsize=(10, 6))
plt.bar(labels, conn_times, color=['blue', 'orange', 'green', 'red'])
plt.ylabel("Connection Time (s)")
plt.title("Average Connection Time")
plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "connection_time.png"))
plt.close()

# Bar Chart: Throughput
throughputs = [combined[k]["Throughput (MB/s)"].mean() for k in labels]
plt.figure(figsize=(10, 6))
plt.bar(labels, throughputs, color=['blue', 'orange', 'green', 'red'])
plt.ylabel("Throughput (MB/s)")
plt.title("Average Throughput")
plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "throughput.png"))
plt.close()
