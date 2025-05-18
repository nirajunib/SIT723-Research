# Detailed Technical Analysis of Network Metrics for **TCP**

---

## Introduction

This report summarizes key statistical findings and interpretations for server and client network metrics collected under the **TCP** protocol. The data compares RSA and ML-DSA cryptographic schemes, each evaluated over 50 trials. Metrics are analyzed to reveal performance, resource utilization, latency, and throughput behavior.

## Server Metrics Analysis

The server-side metrics are captured as time series data over connection lifetimes, aggregated to distributions over trials. These metrics indicate computational load, memory footprint, network throughput, and connection durations.

### Metric: `CPU(%)`
- **Number of samples:** RSA = 2584, ML-DSA = 2560
- **Mean:** RSA = 36.240, ML-DSA = 35.143
- **Median:** RSA = 36.000, ML-DSA = 35.565
- **Standard Deviation:** RSA = 4.833, ML-DSA = 5.981
- **Interquartile Range (IQR):** RSA = 3.191, ML-DSA = 4.015
- **Number of outliers:** RSA = 207, ML-DSA = 233

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- ML-DSA exhibits higher variability, suggesting less stable performance.
- CPU utilization reflects server computational overhead; lower median suggests more efficient processing.

### Metric: `Memory(MB)`
- **Number of samples:** RSA = 2584, ML-DSA = 2560
- **Mean:** RSA = 5038.823, ML-DSA = 4801.891
- **Median:** RSA = 5058.477, ML-DSA = 5102.489
- **Standard Deviation:** RSA = 98.396, ML-DSA = 589.144
- **Interquartile Range (IQR):** RSA = 30.922, ML-DSA = 25.628
- **Number of outliers:** RSA = 326, ML-DSA = 592

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- ML-DSA exhibits higher variability, suggesting less stable performance.
- Memory consumption indicates resource footprint; lower median and variability implies lighter resource use.

### Metric: `Throughput(MB/s)`
- **Number of samples:** RSA = 2584, ML-DSA = 2560
- **Mean:** RSA = 60.689, ML-DSA = 60.916
- **Median:** RSA = 61.790, ML-DSA = 62.152
- **Standard Deviation:** RSA = 6.159, ML-DSA = 8.063
- **Interquartile Range (IQR):** RSA = 3.190, ML-DSA = 7.914
- **Number of outliers:** RSA = 232, ML-DSA = 152

#### Interpretation:
- Median values are similar between RSA and ML-DSA, indicating comparable typical performance.
- ML-DSA exhibits higher variability, suggesting less stable performance.
- Throughput measures data handling capacity; higher median and stability are favorable.

### Metric: `ConnDuration(s)`
- **Number of samples:** RSA = 2584, ML-DSA = 2560
- **Mean:** RSA = 14.527, ML-DSA = 16.541
- **Median:** RSA = 14.405, ML-DSA = 16.056
- **Standard Deviation:** RSA = 8.495, ML-DSA = 10.150
- **Interquartile Range (IQR):** RSA = 14.391, ML-DSA = 15.929
- **Number of outliers:** RSA = 0, ML-DSA = 5

#### Interpretation:
- Median difference of 1.651 suggests **RSA** achieves better typical `connduration(s)`.
- ML-DSA exhibits higher variability, suggesting less stable performance.
- Connection duration reflects connection lifecycle; shorter durations might indicate faster handshakes or terminations.

## Client Metrics Analysis

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

## Time Series Trend Analysis (Server CPU % and Throughput MB/s)

### Metric: `CPU(%)`
- RSA average peak: 96.00, standard deviation over time: 4.83
- ML-DSA average peak: 100.00, standard deviation over time: 5.98
- ML-DSA experiences higher CPU/throughput peaks.
- ML-DSA shows more variability over time.

### Metric: `Throughput(MB/s)`
- RSA average peak: 70.55, standard deviation over time: 6.16
- ML-DSA average peak: 78.03, standard deviation over time: 8.06
- ML-DSA experiences higher CPU/throughput peaks.
- ML-DSA shows more variability over time.

---

## Overall Summary

The comparative analysis reveals nuanced differences between RSA and ML-DSA cryptographic schemes on the tested protocol (**TCP**). Metrics such as CPU utilization, memory footprint, throughput, latency, and connection times demonstrate how each approach impacts performance.

Generally, lower median and mean resource use alongside reduced variability suggests higher efficiency and stability. Differences in connection and handshake times reflect cryptographic and protocol overheads.


---