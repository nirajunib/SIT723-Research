import os
import pandas as pd
import matplotlib.pyplot as plt

# Set your Output directory path
base_dir = 'Output'
folders = [
    os.path.join(base_dir, 'Output-Server', 'Output',
                 'server_benchmarks_mldsa'),
    os.path.join(base_dir, 'Output-Server', 'Output', 'server_benchmarks_rsa'),
    os.path.join(base_dir, 'Output-Client', 'Output',
                 'client_benchmarks_mldsa'),
    os.path.join(base_dir, 'Output-Client', 'Output', 'client_benchmarks_rsa')
]

# Output folder for plots
plot_output_dir = 'individual_csv_plots'
os.makedirs(plot_output_dir, exist_ok=True)

# Read and plot each CSV
for folder_path in folders:
    if not os.path.exists(folder_path):
        continue

    for file in os.listdir(folder_path):
        if file.endswith('.csv'):
            file_path = os.path.join(folder_path, file)
            df = pd.read_csv(file_path)

            # Plot CPU usage
            plt.figure(figsize=(10, 6))
            plt.plot(df['Time(s)'], df['CPU (%)'], color='blue')
            plt.title(f'CPU Usage - {file}')
            plt.xlabel('Time (s)')
            plt.ylabel('CPU Usage (%)')
            plt.grid(True)
            plt.tight_layout()
            cpu_plot_path = os.path.join(plot_output_dir, f'{file}_cpu.png')
            plt.savefig(cpu_plot_path)
            plt.close()

            # Plot Memory usage
            plt.figure(figsize=(10, 6))
            plt.plot(df['Time(s)'], df['Memory (MB)'], color='green')
            plt.title(f'Memory Usage - {file}')
            plt.xlabel('Time (s)')
            plt.ylabel('Memory (MB)')
            plt.grid(True)
            plt.tight_layout()
            memory_plot_path = os.path.join(
                plot_output_dir, f'{file}_memory.png')
            plt.savefig(memory_plot_path)
            plt.close()

print(f"Plots saved in '{plot_output_dir}' folder.")
