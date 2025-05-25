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

plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['font.sans-serif'] = [FONT_NAME, 'DejaVu Sans', 'Liberation Sans']
sns.set(style="whitegrid", font=FONT_FAMILY)

COLOR_PALETTE = {
    'RSA': '#1f77b4',
    'ML-DSA': '#ff7f0e'
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
    fig, axs = plt.subplots(3, 1, figsize=(8, 12))
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
    fig, axs = plt.subplots(3, 1, figsize=(8, 12))
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
    fig, axs = plt.subplots(4, 1, figsize=(8, 16))
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


def generate_detailed_data_insights(protocol, server_data, client_data):
    """
    Generates a comprehensive, detailed, and technical explanation of the
    plotted metrics, describing statistical properties, trends, and implications,
    formatted in Markdown for better readability.
    """

    import numpy as np

    lines = []
    lines.append(
        f"# Detailed Technical Analysis of Network Metrics for **{protocol.upper()}**\n")
    lines.append("---\n")

    lines.append("## Introduction\n")
    lines.append(
        f"This report summarizes key statistical findings and interpretations "
        f"for server and client network metrics collected under the **{protocol.upper()}** protocol. "
        f"The data compares RSA and ML-DSA cryptographic schemes, each evaluated over 50 trials. "
        f"Metrics are analyzed to reveal performance, resource utilization, latency, and throughput behavior.\n"
    )

    # --- SERVER METRICS ---
    lines.append("## Server Metrics Analysis (Boxplot Summary)\n")
    lines.append(
        "The server-side metrics are captured as aggregated statistics over trials. These metrics indicate computational load, memory footprint, "
        "and network throughput.\n"
    )

    # Removed 'ConnDuration(s)' as requested
    server_metrics = ['CPU(%)', 'Memory(MB)', 'Throughput(MB/s)']

    def count_outliers(series):
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        return ((series < lower_bound) | (series > upper_bound)).sum()

    for metric in server_metrics:
        rsa_vals = server_data['rsa-logs'][metric]
        mldsa_vals = server_data['mldsa-logs'][metric]

        rsa_count = rsa_vals.count()
        mldsa_count = mldsa_vals.count()

        rsa_mean = rsa_vals.mean()
        mldsa_mean = mldsa_vals.mean()

        rsa_median = rsa_vals.median()
        mldsa_median = mldsa_vals.median()

        rsa_std = rsa_vals.std()
        mldsa_std = mldsa_vals.std()

        rsa_iqr = rsa_vals.quantile(0.75) - rsa_vals.quantile(0.25)
        mldsa_iqr = mldsa_vals.quantile(0.75) - mldsa_vals.quantile(0.25)

        rsa_outliers = count_outliers(rsa_vals)
        mldsa_outliers = count_outliers(mldsa_vals)

        lines.append(f"### Metric: `{metric}`")
        lines.append(
            f"- **Number of samples:** RSA = {rsa_count}, ML-DSA = {mldsa_count}")
        lines.append(
            f"- **Mean:** RSA = {rsa_mean:.3f}, ML-DSA = {mldsa_mean:.3f}")
        lines.append(
            f"- **Median:** RSA = {rsa_median:.3f}, ML-DSA = {mldsa_median:.3f}")
        lines.append(
            f"- **Standard Deviation:** RSA = {rsa_std:.3f}, ML-DSA = {mldsa_std:.3f}")
        lines.append(
            f"- **Interquartile Range (IQR):** RSA = {rsa_iqr:.3f}, ML-DSA = {mldsa_iqr:.3f}")
        lines.append(
            f"- **Number of outliers:** RSA = {rsa_outliers}, ML-DSA = {mldsa_outliers}\n")

        median_diff = mldsa_median - rsa_median

        lines.append("#### Interpretation:")
        if abs(median_diff) < 0.05 * max(abs(rsa_median), abs(mldsa_median)):
            lines.append(
                "- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.")
        else:
            better = "RSA" if median_diff > 0 else "ML-DSA"
            lines.append(
                f"- Median difference of {abs(median_diff):.3f} suggests **{better}** achieves better typical `{metric.lower()}`."
            )

        if rsa_std > mldsa_std:
            lines.append(
                "- RSA exhibits higher variability, suggesting less stable performance.")
        else:
            lines.append(
                "- ML-DSA exhibits higher variability, suggesting less stable performance.")

        # Specific metric technical notes
        if metric == 'CPU(%)':
            lines.append(
                "- CPU utilization reflects server computational overhead; lower median suggests more efficient processing."
            )
        elif metric == 'Memory(MB)':
            lines.append(
                "- Memory consumption indicates resource footprint; lower median and variability implies lighter resource use."
            )
        elif metric == 'Throughput(MB/s)':
            lines.append(
                "- Throughput measures data handling capacity; higher median and stability are favorable."
            )
        lines.append("")

    # --- TIME SERIES TREND ANALYSIS FOR SERVER ---
    lines.append("## Server Metrics Time Series Trend Analysis\n")
    lines.append(
        "This section explores the temporal behavior of server CPU usage and throughput over connection durations, highlighting trends, peaks, and variability.\n"
    )
    try:
        for metric in ['CPU(%)', 'Throughput(MB/s)']:
            rsa_df = server_data['rsa-logs']
            mldsa_df = server_data['mldsa-logs']

            rsa_series = rsa_df[metric].dropna()
            mldsa_series = mldsa_df[metric].dropna()

            if 'Elapsed(s)' in rsa_df.columns and 'Elapsed(s)' in mldsa_df.columns:
                rsa_avg_trend = rsa_df.groupby('Elapsed(s)')[metric].mean()
                mldsa_avg_trend = mldsa_df.groupby('Elapsed(s)')[metric].mean()

                rsa_peak = rsa_avg_trend.max()
                mldsa_peak = mldsa_avg_trend.max()

                rsa_std_trend = rsa_avg_trend.std()
                mldsa_std_trend = mldsa_avg_trend.std()
            else:
                rsa_peak = rsa_series.max()
                mldsa_peak = mldsa_series.max()
                rsa_std_trend = rsa_series.std()
                mldsa_std_trend = mldsa_series.std()

            lines.append(f"### Metric: `{metric}`")
            lines.append(
                f"- RSA average peak: {rsa_peak:.2f}, standard deviation over time: {rsa_std_trend:.2f}")
            lines.append(
                f"- ML-DSA average peak: {mldsa_peak:.2f}, standard deviation over time: {mldsa_std_trend:.2f}")

            if rsa_peak > mldsa_peak:
                lines.append(
                    "- RSA experiences higher CPU/throughput peaks, possibly indicating bursts of higher load or processing.")
            else:
                lines.append(
                    "- ML-DSA experiences higher CPU/throughput peaks.")

            if rsa_std_trend > mldsa_std_trend:
                lines.append(
                    "- RSA shows more variability over time, suggesting less consistent resource usage.")
            else:
                lines.append("- ML-DSA shows more variability over time.")

            lines.append("")
    except Exception as e:
        lines.append(f"Time series trend analysis failed due to error: {e}\n")

    # --- CLIENT METRICS ---
    lines.append("## Client Metrics Analysis (Boxplot Summary)\n")
    lines.append(
        "Client-side metrics represent latency, handshake times, RTT, and total completion times, "
        "crucial for user experience and responsiveness.\n"
    )

    client_metrics = ['Handshake(ms)', 'Latency(ms)', 'RTT(ms)', 'TTC(ms)']
    for metric in client_metrics:
        rsa_vals = client_data['rsa-logs'][metric]
        mldsa_vals = client_data['mldsa-logs'][metric]

        # Convert TTC to seconds for analysis and adjust label
        if metric == 'TTC(ms)':
            rsa_vals = rsa_vals / 1000.0
            mldsa_vals = mldsa_vals / 1000.0
            metric_label = "TTC (s)"
        else:
            metric_label = metric

        rsa_count = rsa_vals.count()
        mldsa_count = mldsa_vals.count()

        rsa_mean = rsa_vals.mean()
        mldsa_mean = mldsa_vals.mean()

        rsa_median = rsa_vals.median()
        mldsa_median = mldsa_vals.median()

        rsa_std = rsa_vals.std()
        mldsa_std = mldsa_vals.std()

        rsa_iqr = rsa_vals.quantile(0.75) - rsa_vals.quantile(0.25)
        mldsa_iqr = mldsa_vals.quantile(0.75) - mldsa_vals.quantile(0.25)

        rsa_outliers = count_outliers(rsa_vals)
        mldsa_outliers = count_outliers(mldsa_vals)

        lines.append(f"### Metric: `{metric_label}`")
        lines.append(
            f"- **Number of samples:** RSA = {rsa_count}, ML-DSA = {mldsa_count}")
        lines.append(
            f"- **Mean:** RSA = {rsa_mean:.3f}, ML-DSA = {mldsa_mean:.3f}")
        lines.append(
            f"- **Median:** RSA = {rsa_median:.3f}, ML-DSA = {mldsa_median:.3f}")
        lines.append(
            f"- **Standard Deviation:** RSA = {rsa_std:.3f}, ML-DSA = {mldsa_std:.3f}")
        lines.append(
            f"- **Interquartile Range (IQR):** RSA = {rsa_iqr:.3f}, ML-DSA = {mldsa_iqr:.3f}")
        lines.append(
            f"- **Number of outliers:** RSA = {rsa_outliers}, ML-DSA = {mldsa_outliers}\n")

        median_diff = mldsa_median - rsa_median

        lines.append("#### Interpretation:")
        if abs(median_diff) < 0.05 * max(abs(rsa_median), abs(mldsa_median)):
            lines.append(
                "- Median values are similar, indicating comparable client-side latency or timing.")
        else:
            better = "RSA" if median_diff > 0 else "ML-DSA"
            lines.append(
                f"- Median difference of {abs(median_diff):.3f} indicates **{better}** has a performance advantage in this metric."
            )

        if rsa_std > mldsa_std:
            lines.append(
                "- RSA shows higher variability, possibly less consistent client experience.")
        else:
            lines.append(
                "- ML-DSA shows higher variability, indicating potential inconsistency.")

        # Specific explanations per metric
        if metric == 'Handshake(ms)':
            lines.append(
                "- Handshake time reflects cryptographic negotiation duration; lower values improve connection setup speed."
            )
        elif metric == 'Latency(ms)':
            lines.append(
                "- Latency is the network delay; lower values contribute to more responsive connections."
            )
        elif metric == 'RTT(ms)':
            lines.append(
                "- Round Trip Time measures time for a message to travel to server and back; critical for protocol efficiency."
            )
        elif metric == 'TTC(ms)':
            lines.append(
                "- Total Time to Completion indicates full session duration, converted here to seconds for clarity."
            )
        lines.append("")

    # --- CLOSING SUMMARY ---
    lines.append("---\n")
    lines.append("## Overall Summary\n")
    lines.append(
        "The comparative analysis reveals nuanced differences between RSA and ML-DSA cryptographic "
        f"schemes on the tested protocol (**{protocol.upper()}**). Metrics such as CPU utilization, memory footprint, "
        "throughput, latency, and connection times demonstrate how each approach impacts performance.\n\n"

        "Generally, lower median and mean resource use alongside reduced variability suggests higher efficiency "
        "and stability. Differences in connection and handshake times reflect cryptographic and protocol overheads.\n\n"
    )
    lines.append("---")

    return "\n".join(lines)


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

        # Call the detailed explanation generator function
        description_text = generate_detailed_data_insights(
            protocol, server_data, client_data)
        # Save the detailed description to a text file in your output folder
        output_description_path = os.path.join(
            OUTPUT_DIR, f"plot_descriptions_{protocol}.md")
        with open(output_description_path, 'w') as f:
            f.write(description_text)


if __name__ == '__main__':
    main()
