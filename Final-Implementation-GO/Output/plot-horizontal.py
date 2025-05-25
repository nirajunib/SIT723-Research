import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from glob import glob

# Configuration
BASE_DIR = 'Benchmark'
OUTPUT_DIR = 'plots'
PROTOCOLS = ['tcp', 'quic']
SCHEMES = ['rsa-logs', 'mldsa-logs']

# Font and style constants
FONT_FAMILY = 'sans-serif'
FONT_NAME = 'Arial'
TITLE_FONTSIZE = 20
LABEL_FONTSIZE = 18
TICK_FONTSIZE = 16
LEGEND_FONTSIZE = 16

# Set global font settings
plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['font.sans-serif'] = [FONT_NAME, 'DejaVu Sans', 'Liberation Sans']

sns.set(style="whitegrid", font=FONT_FAMILY)

# Color palette for consistency
COLOR_PALETTE = {
    'RSA': '#1f77b4',     # Blue
    'ML-DSA': '#ff7f0e'   # Orange
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


def format_scheme_label(scheme):
    label = scheme.replace('-logs', '').upper()
    return 'ML-DSA' if label == 'MLDSA' else label


def collect_csvs(role, scheme, protocol):
    folder = os.path.join(BASE_DIR, role, scheme, role, protocol)
    files = glob(os.path.join(folder, 'metrics-*.csv'))
    return sorted(files)


def load_server_metrics_avg_line(files, max_lines=200):
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f).head(max_lines)
            dfs.append(df)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
    if not dfs:
        return pd.DataFrame()
    numeric_cols = dfs[0].select_dtypes(include='number').columns
    avg_data = pd.DataFrame(index=range(max_lines))
    for col in numeric_cols:
        col_stack = pd.concat([df[col] for df in dfs], axis=1)
        avg_data[col] = col_stack.mean(axis=1)
    if 'Elapsed(ms)' not in avg_data.columns:
        avg_data['Elapsed(ms)'] = avg_data.index
    avg_data.dropna(how='all', inplace=True)
    return avg_data.reset_index(drop=True)


def load_client_metrics(files):
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def convert_time_units(df, columns):
    for col in columns:
        if col in df.columns and df[col].max() > 1000:
            df[col] = df[col] / 1000
            df.rename(columns={col: col.replace('(ms)', '(s)')}, inplace=True)
    return df


def style_axis(ax, xlabel, ylabel):
    ax.set_xlabel(xlabel, fontsize=LABEL_FONTSIZE)
    ax.set_ylabel(ylabel, fontsize=LABEL_FONTSIZE)
    ax.tick_params(axis='both', labelsize=TICK_FONTSIZE)


def plot_time_series_server(data, protocol):
    fig, axs = plt.subplots(1, 3, figsize=(16, 6))
    metrics = ['CPU(%)', 'Memory(MB)', 'Throughput(MB/s)']

    for idx, metric in enumerate(metrics):
        ax = axs[idx]
        for scheme in SCHEMES:
            df = data.get(scheme)
            if df is None or df.empty:
                continue
            if metric in df.columns and 'Elapsed(ms)' in df.columns:
                x_sec = df['Elapsed(ms)'] / 1000
                label = format_scheme_label(scheme)
                linestyle = '--' if label == 'ML-DSA' else '-'
                ax.plot(x_sec, df[metric],
                        label=label,
                        linestyle=linestyle,
                        color=COLOR_PALETTE[label])
        style_axis(ax, 'Elapsed Time (s)', metric)
        ax.set_xticks(range(0, int(x_sec.max()) + 2, 2))
        ax.legend(fontsize=LEGEND_FONTSIZE)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'server_time_series_{protocol}.png'))
    print(f'[✓] Saved: server_time_series_{protocol}.png')


def plot_box_server(data, protocol):
    fig, axs = plt.subplots(1, 3, figsize=(16, 6))
    metrics = ['CPU(%)', 'Memory(MB)', 'Throughput(MB/s)']
    df_combined = []
    for scheme in SCHEMES:
        df = data.get(scheme)
        if df is None or df.empty:
            continue
        df_copy = df.copy()
        df_copy['Scheme'] = format_scheme_label(scheme)
        df_combined.append(df_copy)
    if not df_combined:
        print(f"No server data to plot for protocol {protocol}")
        return
    df_all = pd.concat(df_combined)

    for idx, metric in enumerate(metrics):
        ax = axs[idx]
        if metric in df_all.columns:
            sns.boxplot(x='Scheme', y=metric, data=df_all, ax=ax,
                        width=0.4, palette=COLOR_PALETTE)
            style_axis(ax, 'Scheme', metric)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'server_boxplot_{protocol}.png'))
    print(f'[✓] Saved: server_boxplot_{protocol}.png')


def plot_box_client(data, protocol):
    fig, axs = plt.subplots(1, 4, figsize=(18, 6))
    metrics = ['Handshake(ms)', 'Latency(ms)', 'RTT(ms)', 'TTC(ms)']
    df_combined = []
    for scheme in SCHEMES:
        df = data[scheme].copy()
        if 'TTC(ms)' in df.columns:
            df['TTC(s)'] = df['TTC(ms)'] / 1000
            df.drop(columns=['TTC(ms)'], inplace=True)
        df['Scheme'] = format_scheme_label(scheme)
        df_combined.append(df)
    df_all = pd.concat(df_combined)

    plot_metrics = ['Handshake(ms)', 'Latency(ms)', 'RTT(ms)', 'TTC(s)']
    for idx, metric in enumerate(plot_metrics):
        ax = axs[idx]
        if metric in df_all.columns:
            sns.boxplot(x='Scheme', y=metric, data=df_all,
                        ax=ax, width=0.4, palette=COLOR_PALETTE)
            style_axis(ax, 'Scheme', metric)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'client_boxplot_{protocol}.png'))
    print(f'[✓] Saved: client_boxplot_{protocol}.png')


def main():
    for protocol in PROTOCOLS:
        print(f'\n📊 Processing {protocol.upper()}')

        server_data = {}
        client_data = {}

        for scheme in SCHEMES:
            s_files = collect_csvs('Server', scheme, protocol)
            server_df = load_server_metrics_avg_line(s_files, max_lines=200)
            server_df = convert_time_units(server_df, [])
            server_data[scheme] = server_df

            c_files = collect_csvs('Client', scheme, protocol)
            client_data[scheme] = load_client_metrics(c_files)

        plot_time_series_server(server_data, protocol)
        plot_box_server(server_data, protocol)
        plot_box_client(client_data, protocol)


if __name__ == '__main__':
    main()
