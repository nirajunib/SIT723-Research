import os
import pandas as pd
import matplotlib.pyplot as plt

# Set your Output directory path
base_dir = 'Output'
server_dir = os.path.join(base_dir, 'Output-Server')
client_dir = os.path.join(base_dir, 'Output-Client')

# Benchmark folders
benchmark_folders = [
    ('server_mldsa', os.path.join(server_dir, 'Output', 'server_benchmarks_mldsa')),
    ('server_rsa', os.path.join(server_dir, 'Output', 'server_benchmarks_rsa')),
    ('client_mldsa', os.path.join(client_dir, 'Output', 'client_benchmarks_mldsa')),
    ('client_rsa', os.path.join(client_dir, 'Output', 'client_benchmarks_rsa')),
]

# To store data
data = {}

# Read all csv files
def read_csvs(folder_path):
    dfs = []
    for file in os.listdir(folder_path):
        if file.endswith('.csv'):
            file_path = os.path.join(folder_path, file)
            df = pd.read_csv(file_path)
            dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return None

for label, path in benchmark_folders:
    data[label] = read_csvs(path)

# Plot settings
colors = {
    'server_mldsa': 'blue',
    'server_rsa': 'cyan',
    'client_mldsa': 'red',
    'client_rsa': 'orange',
}

# ----- CPU Usage Line Graph -----
plt.figure(figsize=(12, 6))
for label, df in data.items():
    if df is not None:
        plt.plot(df['Time(s)'], df['CPU (%)'], label=label, color=colors[label])
plt.title('CPU Usage Over Time')
plt.xlabel('Time (s)')
plt.ylabel('CPU Usage (%)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('cpu_usage.png')
plt.show()

# ----- Memory Usage Line Graph -----
plt.figure(figsize=(12, 6))
for label, df in data.items():
    if df is not None:
        plt.plot(df['Time(s)'], df['Memory (MB)'], label=label, color=colors[label])
plt.title('Memory Usage Over Time')
plt.xlabel('Time (s)')
plt.ylabel('Memory (MB)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('memory_usage.png')
plt.show()

# ----- Bar Graph for Connection Time and Throughput -----
conn_times = []
throughputs = []
labels = []

for label, df in data.items():
    if df is not None:
        conn_times.append(df['Connection Time(s)'].mean())
        throughputs.append(df['Throughput (MB/s)'].mean())
        labels.append(label)

x = range(len(labels))

# Connection Time Bar Graph
plt.figure(figsize=(10, 6))
plt.bar(x, conn_times, color=[colors[l] for l in labels])
plt.xticks(x, labels, rotation=45)
plt.ylabel('Connection Time (s)')
plt.title('Average Connection Time')
plt.tight_layout()
plt.savefig('connection_time.png')
plt.show()

# Throughput Bar Graph
plt.figure(figsize=(10, 6))
plt.bar(x, throughputs, color=[colors[l] for l in labels])
plt.xticks(x, labels, rotation=45)
plt.ylabel('Throughput (MB/s)')
plt.title('Average Throughput')
plt.tight_layout()
plt.savefig('throughput.png')
plt.show()
