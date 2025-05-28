# Open Source Implementation of the Post-Quantum Secure TransportLayer: Quantum Signatures into TCP and QUIC

We design, implement, and evaluate the integration of Module Lattice-based Digital Signatures (ML-DSA) into TCP and QUIC to enable post-quantum secure Internet communication. A comprehensive analysis of authentication mechanisms, protocol adaptability, and performance impacts reveals that QUIC exhibits greater compatibility and requires fewer modifications to support post-quantum cryptography. Our results demonstrate a viable and efficient approach to quantum-resistant data transmission. Benchmarking further highlights the trade-offs between computational overhead and cryptographic strength, offering practical insights into implementation challenges and security considerations. All developed artifacts are available in this GitHub repository.


<img src=https://github.com/nirajunib/SIT723-Research/blob/4b40568877731af805478715d5a11a86ab3037fb/Demo/Overview.png />

> **Note:** The final and most up-to-date version of the code used in the research report is located in the `Final-Implementation-GO/` directory.

---

## Final Version

The codebase used in the **final research report** is located in:

`Final-Implementation-GO/`

This version contains the most stable, cleaned, and benchmark-accurate scripts including:
- RSA and ML-DSA configurations in Golang
- TLS Implementation
- Accurate Benchmarking
- Captured Metrics
- Graphs
- Demo Video

---

## Sample Output & Visualization

- Raw client and server output logs are located in `Final-Implementation-GO/Output/`.
- Benchmark plotting scripts can be found in `Final-Implementation-GO/Code-Files/Scripts/plot-*.py`.

---

## 🔍 Development Timeline

Due to the iterative nature of the research, multiple directories exist representing various development stages. Instead of overwriting scripts, separate folders were created to preserve test history and provide flexibility for rollback and comparisons.

---

