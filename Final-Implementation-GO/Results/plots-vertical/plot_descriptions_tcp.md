# Detailed Technical Analysis of Network Metrics for **TCP**

---

## Introduction

This report summarizes key statistical findings and interpretations for server and client network metrics collected under the **TCP** protocol. The data compares RSA and ML-DSA cryptographic schemes, each evaluated over 50 trials. Metrics are analyzed to reveal performance, resource utilization, latency, and throughput behavior.

## Server Metrics Analysis (Boxplot Summary)

The server-side metrics are captured as aggregated statistics over trials. These metrics indicate computational load, memory footprint, and network throughput.

### Metric: `CPU(%)`
- **Number of samples:** RSA = 200, ML-DSA = 200
- **Mean:** RSA = 36.389, ML-DSA = 36.070
- **Median:** RSA = 36.119, ML-DSA = 35.964
- **Standard Deviation:** RSA = 2.958, ML-DSA = 2.720
- **Interquartile Range (IQR):** RSA = 0.981, ML-DSA = 1.005
- **Number of outliers:** RSA = 20, ML-DSA = 19

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- RSA exhibits higher variability, suggesting less stable performance.
- CPU utilization reflects server computational overhead; lower median suggests more efficient processing.

### Metric: `Memory(MB)`
- **Number of samples:** RSA = 200, ML-DSA = 200
- **Mean:** RSA = 4984.727, ML-DSA = 5010.966
- **Median:** RSA = 4986.705, ML-DSA = 5012.272
- **Standard Deviation:** RSA = 11.800, ML-DSA = 10.140
- **Interquartile Range (IQR):** RSA = 19.291, ML-DSA = 14.579
- **Number of outliers:** RSA = 0, ML-DSA = 0

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- RSA exhibits higher variability, suggesting less stable performance.
- Memory consumption indicates resource footprint; lower median and variability implies lighter resource use.

### Metric: `Throughput(MB/s)`
- **Number of samples:** RSA = 200, ML-DSA = 200
- **Mean:** RSA = 60.444, ML-DSA = 61.330
- **Median:** RSA = 61.707, ML-DSA = 62.613
- **Standard Deviation:** RSA = 6.261, ML-DSA = 6.135
- **Interquartile Range (IQR):** RSA = 1.668, ML-DSA = 1.471
- **Number of outliers:** RSA = 9, ML-DSA = 13

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- RSA exhibits higher variability, suggesting less stable performance.
- Throughput measures data handling capacity; higher median and stability are favorable.

## Server Metrics Time Series Trend Analysis

This section explores the temporal behavior of server CPU usage and throughput over connection durations, highlighting trends, peaks, and variability.

### Metric: `CPU(%)`
- RSA average peak: 48.11, standard deviation over time: 2.96
- ML-DSA average peak: 43.52, standard deviation over time: 2.72
- RSA experiences higher CPU/throughput peaks, possibly indicating bursts of higher load or processing.
- RSA shows more variability over time, suggesting less consistent resource usage.

### Metric: `Throughput(MB/s)`
- RSA average peak: 62.77, standard deviation over time: 6.26
- ML-DSA average peak: 63.38, standard deviation over time: 6.14
- ML-DSA experiences higher CPU/throughput peaks.
- RSA shows more variability over time, suggesting less consistent resource usage.

## Client Metrics Analysis (Boxplot Summary)

Client-side metrics represent latency, handshake times, RTT, and total completion times, crucial for user experience and responsiveness.

### Metric: `Handshake(ms)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 14.853, ML-DSA = 13.086
- **Median:** RSA = 9.110, ML-DSA = 10.327
- **Standard Deviation:** RSA = 21.018, ML-DSA = 6.464
- **Interquartile Range (IQR):** RSA = 3.926, ML-DSA = 5.770
- **Number of outliers:** RSA = 8, ML-DSA = 6

#### Interpretation:
- Median difference of 1.217 indicates **RSA** has a performance advantage in this metric.
- RSA shows higher variability, possibly less consistent client experience.
- Handshake time reflects cryptographic negotiation duration; lower values improve connection setup speed.

### Metric: `Latency(ms)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 1.509, ML-DSA = 2.041
- **Median:** RSA = 0.748, ML-DSA = 0.705
- **Standard Deviation:** RSA = 1.827, ML-DSA = 2.835
- **Interquartile Range (IQR):** RSA = 0.628, ML-DSA = 1.754
- **Number of outliers:** RSA = 10, ML-DSA = 7

#### Interpretation:
- Median difference of 0.043 indicates **ML-DSA** has a performance advantage in this metric.
- ML-DSA shows higher variability, indicating potential inconsistency.
- Latency is the network delay; lower values contribute to more responsive connections.

### Metric: `RTT(ms)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 3.018, ML-DSA = 4.081
- **Median:** RSA = 1.495, ML-DSA = 1.410
- **Standard Deviation:** RSA = 3.654, ML-DSA = 5.670
- **Interquartile Range (IQR):** RSA = 1.255, ML-DSA = 3.507
- **Number of outliers:** RSA = 10, ML-DSA = 7

#### Interpretation:
- Median difference of 0.085 indicates **ML-DSA** has a performance advantage in this metric.
- ML-DSA shows higher variability, indicating potential inconsistency.
- Round Trip Time measures time for a message to travel to server and back; critical for protocol efficiency.

### Metric: `TTC (s)`
- **Number of samples:** RSA = 50, ML-DSA = 50
- **Mean:** RSA = 35.924, ML-DSA = 33.248
- **Median:** RSA = 35.473, ML-DSA = 32.430
- **Standard Deviation:** RSA = 2.446, ML-DSA = 3.749
- **Interquartile Range (IQR):** RSA = 2.001, ML-DSA = 2.184
- **Number of outliers:** RSA = 4, ML-DSA = 4

#### Interpretation:
- Median difference of 3.043 indicates **ML-DSA** has a performance advantage in this metric.
- ML-DSA shows higher variability, indicating potential inconsistency.
- Total Time to Completion indicates full session duration, converted here to seconds for clarity.

---

## Overall Summary

The comparative analysis reveals nuanced differences between RSA and ML-DSA cryptographic schemes on the tested protocol (**TCP**). Metrics such as CPU utilization, memory footprint, throughput, latency, and connection times demonstrate how each approach impacts performance.

Generally, lower median and mean resource use alongside reduced variability suggests higher efficiency and stability. Differences in connection and handshake times reflect cryptographic and protocol overheads.


---