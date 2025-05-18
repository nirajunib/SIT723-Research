# Detailed Technical Analysis of Network Metrics for **QUIC**

---

## Introduction

This report summarizes key statistical findings and interpretations for server and client network metrics collected under the **QUIC** protocol. The data compares RSA and MLDSA cryptographic schemes, each evaluated over 50 trials. Metrics are analyzed to reveal performance, resource utilization, latency, and throughput behavior.

## Server Metrics Analysis

The server-side metrics are captured as time series data over connection lifetimes, aggregated to distributions over trials. These metrics indicate computational load, memory footprint, network throughput, and connection durations.

### Metric: `CPU(%)`
- **Number of samples:** RSA = 3853, MLDSA = 3418
- **Mean:** RSA = 39.708, MLDSA = 40.476
- **Median:** RSA = 40.000, MLDSA = 40.530
- **Standard Deviation:** RSA = 7.898, MLDSA = 7.865
- **Interquartile Range (IQR):** RSA = 7.455, MLDSA = 6.505
- **Number of outliers:** RSA = 178, MLDSA = 256

#### Interpretation:
- Median values are similar between RSA and MLDSA, indicating comparable typical performance.
- RSA exhibits higher variability, suggesting less stable performance.
- CPU utilization reflects server computational overhead; lower median suggests more efficient processing.

### Metric: `Memory(MB)`
- **Number of samples:** RSA = 3853, MLDSA = 3418
- **Mean:** RSA = 2231.113, MLDSA = 2211.358
- **Median:** RSA = 2253.290, MLDSA = 2232.872
- **Standard Deviation:** RSA = 74.973, MLDSA = 56.680
- **Interquartile Range (IQR):** RSA = 15.525, MLDSA = 13.626
- **Number of outliers:** RSA = 336, MLDSA = 543

#### Interpretation:
- Median values are similar between RSA and MLDSA, indicating comparable typical performance.
- RSA exhibits higher variability, suggesting less stable performance.
- Memory consumption indicates resource footprint; lower median and variability implies lighter resource use.

### Metric: `Throughput(MB/s)`
- **Number of samples:** RSA = 3853, MLDSA = 3418
- **Mean:** RSA = 14.803, MLDSA = 15.237
- **Median:** RSA = 14.073, MLDSA = 14.267
- **Standard Deviation:** RSA = 2.865, MLDSA = 3.113
- **Interquartile Range (IQR):** RSA = 1.543, MLDSA = 1.604
- **Number of outliers:** RSA = 383, MLDSA = 416

#### Interpretation:
- Median values are similar between RSA and MLDSA, indicating comparable typical performance.
- MLDSA exhibits higher variability, suggesting less stable performance.
- Throughput measures data handling capacity; higher median and stability are favorable.

### Metric: `ConnDuration(s)`
- **Number of samples:** RSA = 3853, MLDSA = 3418
- **Mean:** RSA = 14.871, MLDSA = 14.264
- **Median:** RSA = 14.812, MLDSA = 14.212
- **Standard Deviation:** RSA = 8.605, MLDSA = 8.249
- **Interquartile Range (IQR):** RSA = 14.790, MLDSA = 14.166
- **Number of outliers:** RSA = 0, MLDSA = 0

#### Interpretation:
- Median values are similar between RSA and MLDSA, indicating comparable typical performance.
- RSA exhibits higher variability, suggesting less stable performance.
- Connection duration reflects connection lifecycle; shorter durations might indicate faster handshakes or terminations.

## Client Metrics Analysis

Client-side metrics represent latency, handshake times, RTT, and total completion times, crucial for user experience and responsiveness.

### Metric: `Handshake(ms)`
- **Number of samples:** RSA = 50, MLDSA = 50
- **Mean:** RSA = 30.004, MLDSA = 17.650
- **Median:** RSA = 11.647, MLDSA = 13.428
- **Standard Deviation:** RSA = 102.175, MLDSA = 10.898
- **Interquartile Range (IQR):** RSA = 9.772, MLDSA = 13.658
- **Number of outliers:** RSA = 4, MLDSA = 3

#### Interpretation:
- Median difference of 1.781 indicates **RSA** has a performance advantage in this metric.
- RSA shows higher variability, possibly less consistent client experience.
- Handshake time reflects cryptographic negotiation duration; lower values improve connection setup speed.

### Metric: `Latency(ms)`
- **Number of samples:** RSA = 50, MLDSA = 50
- **Mean:** RSA = 1.671, MLDSA = 1.793
- **Median:** RSA = 0.758, MLDSA = 0.810
- **Standard Deviation:** RSA = 1.611, MLDSA = 2.140
- **Interquartile Range (IQR):** RSA = 1.591, MLDSA = 1.594
- **Number of outliers:** RSA = 5, MLDSA = 5

#### Interpretation:
- Median difference of 0.052 indicates **RSA** has a performance advantage in this metric.
- MLDSA shows higher variability, indicating potential inconsistency.
- Latency is the network delay; lower values contribute to more responsive connections.

### Metric: `RTT(ms)`
- **Number of samples:** RSA = 50, MLDSA = 50
- **Mean:** RSA = 3.343, MLDSA = 3.586
- **Median:** RSA = 1.515, MLDSA = 1.620
- **Standard Deviation:** RSA = 3.222, MLDSA = 4.281
- **Interquartile Range (IQR):** RSA = 3.183, MLDSA = 3.188
- **Number of outliers:** RSA = 5, MLDSA = 5

#### Interpretation:
- Median difference of 0.105 indicates **RSA** has a performance advantage in this metric.
- MLDSA shows higher variability, indicating potential inconsistency.
- Round Trip Time measures time for a message to travel to server and back; critical for protocol efficiency.

### Metric: `TTC (s)`
- **Number of samples:** RSA = 50, MLDSA = 50
- **Mean:** RSA = 29.356, MLDSA = 28.242
- **Median:** RSA = 29.171, MLDSA = 28.191
- **Standard Deviation:** RSA = 1.331, MLDSA = 1.037
- **Interquartile Range (IQR):** RSA = 1.491, MLDSA = 1.240
- **Number of outliers:** RSA = 1, MLDSA = 0

#### Interpretation:
- Median values are similar, indicating comparable client-side latency or timing.
- RSA shows higher variability, possibly less consistent client experience.
- Total Time to Completion indicates full session duration, converted here to seconds for clarity.

## Time Series Trend Analysis (Server CPU % and Throughput MB/s)

### Metric: `CPU(%)`
- RSA average peak: 100.00, standard deviation over time: 7.90
- MLDSA average peak: 100.00, standard deviation over time: 7.87
- MLDSA experiences higher CPU/throughput peaks.
- RSA shows more variability over time, suggesting less consistent resource usage.

### Metric: `Throughput(MB/s)`
- RSA average peak: 36.83, standard deviation over time: 2.86
- MLDSA average peak: 31.89, standard deviation over time: 3.11
- RSA experiences higher CPU/throughput peaks, possibly indicating bursts of higher load or processing.
- MLDSA shows more variability over time.

---

## Overall Summary

The comparative analysis reveals nuanced differences between RSA and MLDSA cryptographic schemes on the tested protocol (**QUIC**). Metrics such as CPU utilization, memory footprint, throughput, latency, and connection times demonstrate how each approach impacts performance.

Generally, lower median and mean resource use alongside reduced variability suggests higher efficiency and stability. Differences in connection and handshake times reflect cryptographic and protocol overheads.


---