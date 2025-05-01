import os
import csv
import matplotlib.pyplot as plt
import pandas as pd

# Function to load the benchmark data from CSV files


def load_benchmark_data(directory, protocol):
    # List to hold the data for plotting
    data = []

    # Search for all CSV files in the benchmark directory
    for filename in os.listdir(directory):
        if filename.startswith(protocol) and filename.endswith(".csv"):
            file_path = os.path.join(directory, filename)

            # Read the CSV file
            with open(file_path, mode='r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip the header
                for row in reader:
                    timestamp, cpu, mem = float(
                        row[0]), float(row[1]), float(row[2])
                    data.append((timestamp, cpu, mem))

    # Convert to a DataFrame for easier manipulation
    df = pd.DataFrame(data, columns=["Time(s)", "CPU (%)", "Memory (MB)"])
    return df

# Function to plot the benchmark data


def plot_benchmark_data():
    # Define the directory where benchmarks are saved
    # benchmark_dir = "server_benchmarks"
    benchmark_dir = "client_benchmarks"

    # Load data for TCP and QUIC
    tcp_data = load_benchmark_data(benchmark_dir, "tcp")
    quic_data = load_benchmark_data(benchmark_dir, "quic")

    # Plot CPU usage
    plt.figure(figsize=(10, 6))
    plt.plot(tcp_data["Time(s)"], tcp_data["CPU (%)"],
             label="TCP CPU Usage", color="b")
    plt.plot(quic_data["Time(s)"], quic_data["CPU (%)"],
             label="QUIC CPU Usage", color="g")
    plt.xlabel("Time (seconds)")
    plt.ylabel("CPU Usage (%)")
    plt.title("CPU Usage over Time (TCP vs QUIC)")
    plt.legend(loc="upper left")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # Plot Memory usage
    plt.figure(figsize=(10, 6))
    plt.plot(tcp_data["Time(s)"], tcp_data["Memory (MB)"],
             label="TCP Memory Usage", color="b")
    plt.plot(quic_data["Time(s)"], quic_data["Memory (MB)"],
             label="QUIC Memory Usage", color="g")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Memory Usage (MB)")
    plt.title("Memory Usage over Time (TCP vs QUIC)")
    plt.legend(loc="upper left")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_benchmark_data()
