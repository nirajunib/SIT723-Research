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
sns.set(style="whitegrid")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def collect_csvs(role, scheme, protocol):
    folder = os.path.join(BASE_DIR, role, scheme, role, protocol)
    files = glob(os.path.join(folder, 'metrics-*.csv'))
    return sorted(files)


def load_server_metrics(files):
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
    return dfs


def load_client_metrics(files):
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
    return pd.concat(dfs, ignore_index=True)


def aggregate_server_time_series(dfs):
    df_combined = pd.concat(dfs, axis=0)
    df_combined = df_combined.groupby('Elapsed(ms)').mean().reset_index()
    df_combined['Elapsed(s)'] = df_combined['Elapsed(ms)'] / 1000
    return df_combined


def convert_time_units(df, columns):
    for col in columns:
        if col in df.columns and df[col].max() > 1000:
            df[col] = df[col] / 1000
            df.rename(columns={col: col.replace('(ms)', '(s)')}, inplace=True)
    return df


def plot_time_series_server(data, protocol):
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    metrics = ['CPU(%)', 'Memory(MB)', 'Throughput(MB/s)', 'ConnDuration(s)']
    positions = [(0, 0), (0, 1), (1, 0), (1, 1)]

    for idx, metric in enumerate(metrics):
        ax = axs[positions[idx]]
        for scheme in SCHEMES:
            df = data[scheme]
            if metric in df.columns:
                ax.plot(df['Elapsed(s)'], df[metric],
                        label=scheme.replace('-logs', '').upper())
        ax.set_title(f'{metric} over Time - {protocol.upper()}')
        ax.set_xlabel('Elapsed Time (s)')
        ax.set_ylabel(metric)
        ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'server_time_series_{protocol}.png'))
    print(f'[✓] Saved: server_time_series_{protocol}.png')


def plot_box_server(data, protocol):
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    metrics = ['CPU(%)', 'Memory(MB)', 'Throughput(MB/s)', 'ConnDuration(s)']
    positions = [(0, 0), (0, 1), (1, 0), (1, 1)]

    df_combined = []
    for scheme in SCHEMES:
        df = data[scheme].copy()
        df['Scheme'] = scheme.replace('-logs', '').upper()
        df_combined.append(df)
    df_all = pd.concat(df_combined)

    for idx, metric in enumerate(metrics):
        ax = axs[positions[idx]]
        if metric in df_all.columns:
            sns.boxplot(x='Scheme', y=metric, data=df_all, ax=ax)
            ax.set_title(f'{metric} Distribution - {protocol.upper()}')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'server_boxplot_{protocol}.png'))
    print(f'[✓] Saved: server_boxplot_{protocol}.png')


def plot_time_series_client(data, protocol):
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    metrics = ['Handshake(ms)', 'Latency(ms)', 'RTT(ms)', 'TTC(ms)']
    positions = [(0, 0), (0, 1), (1, 0), (1, 1)]

    for idx, metric in enumerate(metrics):
        ax = axs[positions[idx]]
        for scheme in SCHEMES:
            df = data[scheme].copy()

            # Convert TTC(ms) explicitly to seconds here and adjust label/title
            if metric == 'TTC(ms)':
                y = df[metric] / 1000
                label = f'{scheme.replace("-logs", "").upper()}'
                ylabel = metric.replace('(ms)', '(s)')
                title_metric = 'TTC(s)'
            else:
                y = df[metric]
                label = scheme.replace("-logs", "").upper()
                ylabel = metric
                title_metric = metric

            ax.plot(y.reset_index(drop=True), label=label)
        ax.set_title(f'{title_metric} Time Series - {protocol.upper()}')
        ax.set_xlabel('Trial')
        ax.set_ylabel(ylabel)
        ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'client_time_series_{protocol}.png'))
    print(f'[✓] Saved: client_time_series_{protocol}.png')


def plot_box_client(data, protocol):
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    metrics = ['Handshake(ms)', 'Latency(ms)', 'RTT(ms)', 'TTC(ms)']
    positions = [(0, 0), (0, 1), (1, 0), (1, 1)]

    df_combined = []
    for scheme in SCHEMES:
        df = data[scheme].copy()
        # Convert TTC(ms) explicitly here
        if 'TTC(ms)' in df.columns:
            df['TTC(s)'] = df['TTC(ms)'] / 1000
            df.drop(columns=['TTC(ms)'], inplace=True)
        df['Scheme'] = scheme.replace('-logs', '').upper()
        df_combined.append(df)

    df_all = pd.concat(df_combined)

    # Now plot using updated column names with TTC(s)
    plot_metrics = ['Handshake(ms)', 'Latency(ms)', 'RTT(ms)', 'TTC(s)']

    for idx, metric in enumerate(plot_metrics):
        ax = axs[positions[idx]]
        if metric in df_all.columns:
            ylabel = metric
            # Adjust ylabel/title for TTC(s)
            title_metric = metric
            if metric == 'TTC(s)':
                title_metric = 'TTC(s)'
                ylabel = 'TTC (s)'

            sns.boxplot(x='Scheme', y=metric, data=df_all, ax=ax)
            ax.set_title(f'{title_metric} Distribution - {protocol.upper()}')
            ax.set_ylabel(ylabel)

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
        f"The data compares RSA and MLDSA cryptographic schemes, each evaluated over 50 trials. "
        f"Metrics are analyzed to reveal performance, resource utilization, latency, and throughput behavior.\n"
    )

    # --- SERVER METRICS ---
    lines.append("## Server Metrics Analysis\n")
    lines.append(
        "The server-side metrics are captured as time series data over connection lifetimes, "
        "aggregated to distributions over trials. These metrics indicate computational load, memory footprint, "
        "network throughput, and connection durations.\n"
    )

    server_metrics = ['CPU(%)', 'Memory(MB)',
                      'Throughput(MB/s)', 'ConnDuration(s)']
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

        def count_outliers(series):
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            return ((series < lower_bound) | (series > upper_bound)).sum()

        rsa_outliers = count_outliers(rsa_vals)
        mldsa_outliers = count_outliers(mldsa_vals)

        lines.append(f"### Metric: `{metric}`")
        lines.append(
            f"- **Number of samples:** RSA = {rsa_count}, MLDSA = {mldsa_count}")
        lines.append(
            f"- **Mean:** RSA = {rsa_mean:.3f}, MLDSA = {mldsa_mean:.3f}")
        lines.append(
            f"- **Median:** RSA = {rsa_median:.3f}, MLDSA = {mldsa_median:.3f}")
        lines.append(
            f"- **Standard Deviation:** RSA = {rsa_std:.3f}, MLDSA = {mldsa_std:.3f}")
        lines.append(
            f"- **Interquartile Range (IQR):** RSA = {rsa_iqr:.3f}, MLDSA = {mldsa_iqr:.3f}")
        lines.append(
            f"- **Number of outliers:** RSA = {rsa_outliers}, MLDSA = {mldsa_outliers}\n")

        median_diff = mldsa_median - rsa_median

        lines.append("#### Interpretation:")
        if abs(median_diff) < 0.05 * max(abs(rsa_median), abs(mldsa_median)):
            lines.append(
                "- Median values are similar between RSA and MLDSA, indicating comparable typical performance.")
        else:
            better = "RSA" if median_diff > 0 else "MLDSA"
            lines.append(
                f"- Median difference of {abs(median_diff):.3f} suggests **{better}** achieves better typical `{metric.lower()}`."
            )

        if rsa_std > mldsa_std:
            lines.append(
                "- RSA exhibits higher variability, suggesting less stable performance.")
        else:
            lines.append(
                "- MLDSA exhibits higher variability, suggesting less stable performance.")

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
        elif metric == 'ConnDuration(s)':
            lines.append(
                "- Connection duration reflects connection lifecycle; shorter durations might indicate faster handshakes or terminations."
            )
        lines.append("")

    # --- CLIENT METRICS ---
    lines.append("## Client Metrics Analysis\n")
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
            f"- **Number of samples:** RSA = {rsa_count}, MLDSA = {mldsa_count}")
        lines.append(
            f"- **Mean:** RSA = {rsa_mean:.3f}, MLDSA = {mldsa_mean:.3f}")
        lines.append(
            f"- **Median:** RSA = {rsa_median:.3f}, MLDSA = {mldsa_median:.3f}")
        lines.append(
            f"- **Standard Deviation:** RSA = {rsa_std:.3f}, MLDSA = {mldsa_std:.3f}")
        lines.append(
            f"- **Interquartile Range (IQR):** RSA = {rsa_iqr:.3f}, MLDSA = {mldsa_iqr:.3f}")
        lines.append(
            f"- **Number of outliers:** RSA = {rsa_outliers}, MLDSA = {mldsa_outliers}\n")

        median_diff = mldsa_median - rsa_median

        lines.append("#### Interpretation:")
        if abs(median_diff) < 0.05 * max(abs(rsa_median), abs(mldsa_median)):
            lines.append(
                "- Median values are similar, indicating comparable client-side latency or timing.")
        else:
            better = "RSA" if median_diff > 0 else "MLDSA"
            lines.append(
                f"- Median difference of {abs(median_diff):.3f} indicates **{better}** has a performance advantage in this metric."
            )

        if rsa_std > mldsa_std:
            lines.append(
                "- RSA shows higher variability, possibly less consistent client experience.")
        else:
            lines.append(
                "- MLDSA shows higher variability, indicating potential inconsistency.")

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

    # --- TIME SERIES TREND SUMMARY ---
    lines.append(
        "## Time Series Trend Analysis (Server CPU % and Throughput MB/s)\n")
    try:
        for metric in ['CPU(%)', 'Throughput(MB/s)']:
            rsa_df = server_data['rsa-logs']
            mldsa_df = server_data['mldsa-logs']

            rsa_series = rsa_df[metric].dropna()
            mldsa_series = mldsa_df[metric].dropna()

            # Group by elapsed time if available, else mean overall
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
                f"- MLDSA average peak: {mldsa_peak:.2f}, standard deviation over time: {mldsa_std_trend:.2f}")

            if rsa_peak > mldsa_peak:
                lines.append(
                    "- RSA experiences higher CPU/throughput peaks, possibly indicating bursts of higher load or processing.")
            else:
                lines.append(
                    "- MLDSA experiences higher CPU/throughput peaks.")

            if rsa_std_trend > mldsa_std_trend:
                lines.append(
                    "- RSA shows more variability over time, suggesting less consistent resource usage.")
            else:
                lines.append("- MLDSA shows more variability over time.")

            lines.append("")
    except Exception as e:
        lines.append(f"Time series trend analysis failed due to error: {e}\n")

    # --- CLOSING SUMMARY ---
    lines.append("---\n")
    lines.append("## Overall Summary\n")
    lines.append(
        "The comparative analysis reveals nuanced differences between RSA and MLDSA cryptographic "
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
            # Server
            s_files = collect_csvs('Server', scheme, protocol)
            s_dfs = load_server_metrics(s_files)
            server_df = aggregate_server_time_series(s_dfs)
            server_df = convert_time_units(server_df, ['ConnDuration(s)'])
            server_data[scheme] = server_df

            # Client
            c_files = collect_csvs('Client', scheme, protocol)
            client_data[scheme] = load_client_metrics(c_files)

        # Server plots
        plot_time_series_server(server_data, protocol)
        plot_box_server(server_data, protocol)

        # Client plots
        plot_time_series_client(client_data, protocol)
        plot_box_client(client_data, protocol)

        # Call the detailed explanation generator function
        description_text = generate_detailed_data_insights(
            protocol, server_data, client_data)

        # Save the detailed description to a text file in your output folder
        output_description_path = os.path.join(
            OUTPUT_DIR, f"plot_descriptions_{protocol}.md")
        with open(output_description_path, 'w') as f:
            f.write(description_text)

        print(f"Detailed textual analysis saved to {output_description_path}")
        print(f'✅ Completed analysis for {protocol.upper()}')


if __name__ == '__main__':
    main()
