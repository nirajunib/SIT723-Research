# Detailed Technical Analysis of Network Metrics for **QUIC**

---

## Introduction

This report summarizes key statistical findings and interpretations for server and client network metrics collected under the **QUIC** protocol. The data compares RSA and ML-DSA cryptographic schemes, each evaluated over 50 trials. Metrics are analyzed to reveal performance, resource utilization, latency, and throughput behavior.

## Server Metrics Analysis (Boxplot Summary)

The server-side metrics are captured as aggregated statistics over trials. These metrics indicate computational load, memory footprint, and network throughput.

### Metric: `CPU(%)`
- **Number of samples:** RSA = 200, ML-DSA = 200
- **Mean:** RSA = 40.616, ML-DSA = 40.905
- **Median:** RSA = 40.520, ML-DSA = 40.515
- **Standard Deviation:** RSA = 3.310, ML-DSA = 3.459
- **Interquartile Range (IQR):** RSA = 1.843, ML-DSA = 1.755
- **Number of outliers:** RSA = 13, ML-DSA = 19

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- ML-DSA exhibits higher variability, suggesting less stable performance.
- CPU utilization reflects server computational overhead; lower median suggests more efficient processing.

### Metric: `Memory(MB)`
- **Number of samples:** RSA = 200, ML-DSA = 200
- **Mean:** RSA = 2235.232, ML-DSA = 2218.275
- **Median:** RSA = 2234.538, ML-DSA = 2218.010
- **Standard Deviation:** RSA = 2.865, ML-DSA = 1.982
- **Interquartile Range (IQR):** RSA = 4.605, ML-DSA = 3.630
- **Number of outliers:** RSA = 0, ML-DSA = 0

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- RSA exhibits higher variability, suggesting less stable performance.
- Memory consumption indicates resource footprint; lower median and variability implies lighter resource use.

### Metric: `Throughput(MB/s)`
- **Number of samples:** RSA = 200, ML-DSA = 200
- **Mean:** RSA = 15.224, ML-DSA = 15.867
- **Median:** RSA = 14.111, ML-DSA = 14.579
- **Standard Deviation:** RSA = 2.684, ML-DSA = 3.096
- **Interquartile Range (IQR):** RSA = 1.478, ML-DSA = 1.786
- **Number of outliers:** RSA = 26, ML-DSA = 27

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- ML-DSA exhibits higher variability, suggesting less stable performance.
- Throughput measures data handling capacity; higher median and stability are favorable.

## Server Metrics Time Series Trend Analysis

This section explores the temporal behavior of server CPU usage and throughput over connection durations, highlighting trends, peaks, and variability.

### Metric: `CPU(%)`
- RSA average peak: 51.30, standard deviation over time: 3.31
- ML-DSA average peak: 51.65, standard deviation over time: 3.46
- ML-DSA experiences higher CPU/throughput peaks.
- ML-DSA shows more variability over time.

### Metric: `Throughput(MB/s)`
- RSA average peak: 25.42, standard deviation over time: 2.68
- ML-DSA average peak: 26.54, standard deviation over time: 3.10
- ML-DSA experiences higher CPU/throughput peaks.
- ML-DSA shows more variability over time.

## Client Metrics Analysis (Boxplot Summary)

Client-side metrics represent latency, handshake times, RTT, and total completion times, crucial for user experience and responsiveness.

### Metric: `Handshake(ms)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 30.004, ML-DSA = 17.650
- **Median:** RSA = 11.647, ML-DSA = 13.428
- **Standard Deviation:** RSA = 102.175, ML-DSA = 10.898
- **Interquartile Range (IQR):** RSA = 9.772, ML-DSA = 13.658
- **Number of outliers:** RSA = 4, ML-DSA = 3

#### Interpretation:
- Median difference of 1.781 indicates **RSA** has a performance advantage in this metric.
- RSA shows higher variability, possibly less consistent client experience.
- Handshake time reflects cryptographic negotiation duration; lower values improve connection setup speed.

### Metric: `Latency(ms)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 1.671, ML-DSA = 1.793
- **Median:** RSA = 0.758, ML-DSA = 0.810
- **Standard Deviation:** RSA = 1.611, ML-DSA = 2.140
- **Interquartile Range (IQR):** RSA = 1.591, ML-DSA = 1.594
- **Number of outliers:** RSA = 5, ML-DSA = 5

#### Interpretation:
- Median difference of 0.052 indicates **RSA** has a performance advantage in this metric.
- ML-DSA shows higher variability, indicating potential inconsistency.
- Latency is the network delay; lower values contribute to more responsive connections.

### Metric: `RTT(ms)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 3.343, ML-DSA = 3.586
- **Median:** RSA = 1.515, ML-DSA = 1.620
- **Standard Deviation:** RSA = 3.222, ML-DSA = 4.281
- **Interquartile Range (IQR):** RSA = 3.183, ML-DSA = 3.188
- **Number of outliers:** RSA = 5, ML-DSA = 5

#### Interpretation:
- Median difference of 0.105 indicates **RSA** has a performance advantage in this metric.
- ML-DSA shows higher variability, indicating potential inconsistency.
- Round Trip Time measures time for a message to travel to server and back; critical for protocol efficiency.

### Metric: `TTC (s)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 29.356, ML-DSA = 28.242
- **Median:** RSA = 29.171, ML-DSA = 28.191
- **Standard Deviation:** RSA = 1.331, ML-DSA = 1.037
- **Interquartile Range (IQR):** RSA = 1.491, ML-DSA = 1.240
- **Number of outliers:** RSA = 1, ML-DSA = 0

#### Interpretation:
- Median values are similar, indicating comparable client-side latency or timing.
- RSA shows higher variability, possibly less consistent client experience.
- Total Time to Completion indicates full session duration, converted here to seconds for clarity.

---

## Overall Summary

The comparative analysis reveals nuanced differences between RSA and ML-DSA cryptographic schemes on the tested protocol (**QUIC**). Metrics such as CPU utilization, memory footprint, throughput, latency, and connection times demonstrate how each approach impacts performance.

Generally, lower median and mean resource use alongside reduced variability suggests higher efficiency and stability. Differences in connection and handshake times reflect cryptographic and protocol overheads.


---