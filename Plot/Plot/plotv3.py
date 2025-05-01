import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# Function to load CSV files based on pattern


def load_csv_files(folder, pattern):
    # Get all CSV files in the folder that match the pattern
    return glob.glob(os.path.join(folder, pattern))

# Function to plot CPU usage


def plot_cpu_usage(rsa_tcp, rsa_quic, mldsa_tcp, mldsa_quic, output_folder):
    plt.figure(figsize=(10, 6))
    plt.plot(rsa_tcp['Time(s)'], rsa_tcp['CPU (%)'],
             label='RSA TCP', color='b')
    plt.plot(rsa_quic['Time(s)'], rsa_quic['CPU (%)'],
             label='RSA QUIC', color='g')
    plt.plot(mldsa_tcp['Time(s)'], mldsa_tcp['CPU (%)'],
             label='MLDSA TCP', color='r')
    plt.plot(mldsa_quic['Time(s)'], mldsa_quic['CPU (%)'],
             label='MLDSA QUIC', color='c')
    plt.xlabel('Time (s)')
    plt.ylabel('CPU Usage (%)')
    plt.title('CPU Usage over Time')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_folder, 'cpu_usage.png'))
    plt.close()

# Function to plot memory usage


def plot_memory_usage(rsa_tcp, rsa_quic, mldsa_tcp, mldsa_quic, output_folder):
    plt.figure(figsize=(10, 6))
    plt.plot(rsa_tcp['Time(s)'], rsa_tcp['Memory (MB)'],
             label='RSA TCP', color='b')
    plt.plot(rsa_quic['Time(s)'], rsa_quic['Memory (MB)'],
             label='RSA QUIC', color='g')
    plt.plot(mldsa_tcp['Time(s)'], mldsa_tcp['Memory (MB)'],
             label='MLDSA TCP', color='r')
    plt.plot(mldsa_quic['Time(s)'], mldsa_quic['Memory (MB)'],
             label='MLDSA QUIC', color='c')
    plt.xlabel('Time (s)')
    plt.ylabel('Memory Usage (MB)')
    plt.title('Memory Usage over Time')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_folder, 'memory_usage.png'))
    plt.close()

# Function to plot connection time


def plot_connection_time(rsa_tcp, rsa_quic, mldsa_tcp, mldsa_quic, output_folder):
    plt.figure(figsize=(10, 6))
    plt.bar(['RSA TCP', 'RSA QUIC', 'MLDSA TCP', 'MLDSA QUIC'],
            [rsa_tcp['Connection Time(s)'].mean(), rsa_quic['Connection Time(s)'].mean(),
             mldsa_tcp['Connection Time(s)'].mean(), mldsa_quic['Connection Time(s)'].mean()],
            color=['b', 'g', 'r', 'c'])
    plt.xlabel('Protocol')
    plt.ylabel('Connection Time (s)')
    plt.title('Connection Time Comparison')
    plt.grid(True)
    plt.savefig(os.path.join(output_folder, 'connection_time.png'))
    plt.close()

# Function to plot throughput


def plot_throughput(rsa_tcp, rsa_quic, mldsa_tcp, mldsa_quic, output_folder):
    plt.figure(figsize=(10, 6))
    plt.bar(['RSA TCP', 'RSA QUIC', 'MLDSA TCP', 'MLDSA QUIC'],
            [rsa_tcp['Throughput (MB/s)'].mean(), rsa_quic['Throughput (MB/s)'].mean(),
             mldsa_tcp['Throughput (MB/s)'].mean(), mldsa_quic['Throughput (MB/s)'].mean()],
            color=['b', 'g', 'r', 'c'])
    plt.xlabel('Protocol')
    plt.ylabel('Throughput (MB/s)')
    plt.title('Throughput Comparison')
    plt.grid(True)
    plt.savefig(os.path.join(output_folder, 'throughput.png'))
    plt.close()

# Main function to process the CSV files and generate plots


def main():
    # Define the output folder for saving plots
    output_folder = 'plots_output'
    os.makedirs(output_folder, exist_ok=True)

    # Define folder paths
    server_folder = 'Output/Output-Server/Output'
    client_folder = 'Output/Output-Client/Output'

    # Load CSV files from server and client directories
    server_rsa_tcp_files = load_csv_files(os.path.join(
        server_folder, 'server_benchmarks_rsa'), '*tcp*.csv')
    server_rsa_quic_files = load_csv_files(os.path.join(
        server_folder, 'server_benchmarks_rsa'), '*quic*.csv')
    server_mldsa_tcp_files = load_csv_files(os.path.join(
        server_folder, 'server_benchmarks_mldsa'), '*tcp*.csv')
    server_mldsa_quic_files = load_csv_files(os.path.join(
        server_folder, 'server_benchmarks_mldsa'), '*quic*.csv')

    client_rsa_tcp_files = load_csv_files(os.path.join(
        client_folder, 'client_benchmarks_rsa'), '*tcp*.csv')
    client_rsa_quic_files = load_csv_files(os.path.join(
        client_folder, 'client_benchmarks_rsa'), '*quic*.csv')
    client_mldsa_tcp_files = load_csv_files(os.path.join(
        client_folder, 'client_benchmarks_mldsa'), '*tcp*.csv')
    client_mldsa_quic_files = load_csv_files(os.path.join(
        client_folder, 'client_benchmarks_mldsa'), '*quic*.csv')

    # For now, we assume only one CSV file in each category for simplicity.
    # You can extend this to aggregate data if multiple CSVs exist per category.
    rsa_tcp = pd.read_csv(server_rsa_tcp_files[0])
    rsa_quic = pd.read_csv(server_rsa_quic_files[0])
    mldsa_tcp = pd.read_csv(server_mldsa_tcp_files[0])
    mldsa_quic = pd.read_csv(server_mldsa_quic_files[0])

    # Plot and save images
    plot_cpu_usage(rsa_tcp, rsa_quic, mldsa_tcp, mldsa_quic, output_folder)
    plot_memory_usage(rsa_tcp, rsa_quic, mldsa_tcp, mldsa_quic, output_folder)
    plot_connection_time(rsa_tcp, rsa_quic, mldsa_tcp,
                         mldsa_quic, output_folder)
    plot_throughput(rsa_tcp, rsa_quic, mldsa_tcp, mldsa_quic, output_folder)


if __name__ == "__main__":
    main()
