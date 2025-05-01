import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter

# Smoothing function using Savitzky-Golay filter


def smooth_series(y, window=11, poly=3):
    if len(y) < window:
        window = len(y) if len(y) % 2 != 0 else len(y) - 1
        if window < 3:
            return y  # Not enough points to smooth
    return savgol_filter(y, window, poly)


# Set your Output directory path
base_dir = 'Output'
server_dir = os.path.join(base_dir, 'Output-Server')
client_dir = os.path.join(base_dir, 'Output-Client')

# Output folder for clean plots
plot_output_dir = 'Cleaned_Plots'
os.makedirs(plot_output_dir, exist_ok=True)

# Benchmark folders
benchmark_folders = [
    ('server_mldsa', os.path.join(server_dir, 'Output', 'server_benchmarks_mldsa')),
    ('server_rsa', os.path.join(server_dir, 'Output', 'server_benchmarks_rsa')),
    ('client_mldsa', os.path.join(client_dir, 'Output', 'client_benchmarks_mldsa')),
    ('client_rsa', os.path.join(client_dir, 'Output', 'client_benchmarks_rsa')),
]

# Colors for plotting
colors = {
    'server_mldsa': 'blue',
    'server_rsa': 'cyan',
    'client_mldsa': 'red',
    'client_rsa': 'orange',
}

# Read CSVs
data = {}


def read_csvs(folder_path):
    dfs = []
    for file in os.listdir(folder_path):
        if file.endswith('.csv'):
            file_path = os.path.join(folder_path, file)
            df = pd.read_csv(file_path)
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else None


for label, path in benchmark_folders:
    df = read_csvs(path)
    if df is not None:
        df = df.sort_values(by='Time(s)')
        data[label] = df

# ----- CPU Usage (Smoothed) -----
plt.figure(figsize=(12, 6))
for label, df in data.items():
    smoothed_cpu = smooth_series(df['CPU (%)'].values)
    plt.plot(df['Time(s)'], smoothed_cpu, label=label, color=colors[label])
plt.title('Smoothed CPU Usage Over Time')
plt.xlabel('Time (s)')
plt.ylabel('CPU Usage (%)')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(plot_output_dir, 'smoothed_cpu_usage.png'))
plt.show()

# ----- Memory Usage (Smoothed) -----
plt.figure(figsize=(12, 6))
for label, df in data.items():
    smoothed_mem = smooth_series(df['Memory (MB)'].values)
    plt.plot(df['Time(s)'], smoothed_mem, label=label, color=colors[label])
plt.title('Smoothed Memory Usage Over Time')
plt.xlabel('Time (s)')
plt.ylabel('Memory (MB)')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(plot_output_dir, 'smoothed_memory_usage.png'))
plt.show()

# ----- Connection Time -----
conn_times = []
throughputs = []
labels = []

for label, df in data.items():
    conn_times.append(df['Connection Time(s)'].mean())
    throughputs.append(df['Throughput (MB/s)'].mean())
    labels.append(label)

x = np.arange(len(labels))

# Connection Time Bar Graph
plt.figure(figsize=(10, 6))
plt.bar(x, conn_times, color=[colors[l] for l in labels])
plt.xticks(x, labels, rotation=45)
plt.ylabel('Connection Time (s)')
plt.title('Average Connection Time')
plt.tight_layout()
plt.savefig(os.path.join(plot_output_dir, 'connection_time.png'))
plt.show()

# Throughput Bar Graph
plt.figure(figsize=(10, 6))
plt.bar(x, throughputs, color=[colors[l] for l in labels])
plt.xticks(x, labels, rotation=45)
plt.ylabel('Throughput (MB/s)')
plt.title('Average Throughput')
plt.tight_layout()
plt.savefig(os.path.join(plot_output_dir, 'throughput.png'))
plt.show()
