## Repository Structure
```text
 apc-rlnc/
├── simulation/                 # Discrete-event Python simulator
│   ├── core/                   # EWMA scoring, clustering (Alg. 1), FTRL regret, analytical checks
│   ├── networks/               # Mobility (random waypoint) and churn models
│   ├── coding/                 # GF(256) arithmetic, RLNC encode/decode, hierarchical coding
│   ├── tests/                  # Pytest test suite
│   ├── run_sim.py              # Simulation entry point CLI
│   └── setup.py                # Optional Cython acceleration setup
│
├── testbed/                    # Embedded system stack for edge devices
│   ├── clustering-go/          # Go implementation of gossip clustering daemon
│   ├── rlnc-cpp/               # Self-contained C++ GF(256)/RLNC library
│   ├── orchestration/          # Kubernetes manifests (DaemonSet, Deployment, xApp)
│   └── network-emulation/      # tc/netem channel emulation scripts
│
└── docs/
    └── reference_results/      # Transcribed tables and figure reproduction scripts
```

---

 🚀 Quick Start

 Prerequisites

Simulation: Python 3.12+, standard C/C++ compiler (for optional Cython acceleration).
Testbed Stack: Go 1.22+, CMake 3.22+, Linux kernel with `iproute2` (`tc`/`netem`).

 1. Running the Simulator

```bash
cd simulation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

 Optional: Build the Cython GF(256) extension for a ~5x execution speedup
python setup.py build_ext --inplace
```

Run simulation scenarios:

```bash
 Burst-error channel evaluation (100 nodes, 2-state Markov)
python run_sim.py --nodes 100 --channel markov --burst-duration 50 --runs 50

 Compare schemes under Bernoulli channel models
python run_sim.py --nodes 30 --channel bernoulli --scheme random --runs 20
python run_sim.py --nodes 30 --channel bernoulli --scheme apc    --runs 20
```

Run test suite and analytical checks:

```bash
 Run unit tests across GF(256), RLNC, EWMA, and clustering
python -m pytest tests/ -v

 Validate closed-form claims for Theorems 1 and 2
python -m core.analytical_check
```

 2. Deploying on Edge Hardware (Testbed Stack)

 Build and run the Go Gossip Daemon:
```bash
cd testbed/clustering-go
go build -o apc-cluster-daemon .
./apc-cluster-daemon --interface=wlan0 --epoch-duration=1.5s
```

 Build and run the C++ RLNC Coding Engine:
```bash
cd testbed/rlnc-cpp
mkdir build && cd build && cmake .. && make
./rlnc_demo --K 32 --R 16 --p 0.225 --trials 2000
```

 Apply Channel Emulation via `tc/netem`:
```bash
cd testbed/network-emulation
sudo ./emulate_channels.sh apply --interface wlan0 \
    --loss-good 0.05 --loss-bad 0.40 --transition 0.10
```

 Deploy on Kubernetes / O-RAN Near-RT RIC:
```bash
kubectl apply -f testbed/orchestration/namespace.yaml
kubectl apply -f testbed/orchestration/configmap.yaml
kubectl apply -f testbed/orchestration/clustering-daemonset.yaml
kubectl apply -f testbed/orchestration/rlnc-service-deployment.yaml
kubectl apply -f testbed/orchestration/xapp-emulation.yaml
```

---

 Implemented Schemes

The released simulator implements:

- Random RLNC
- Static RLNC
- APC-RLNC

The work additionally compares APC-RLNC against the published
PACE and ARLNC methods. These are included as literature baselines for
comparative evaluation, but their independent implementations are not
redistributed in this repository.

 📊 Summary Performance Summary

Vehicular Networks (50 Nodes, 5% Churn): 99.32% PDR (5.2 percentage-point gain over Random RLNC) and 145 ms latency (18% improvement).
Burst-Error Channels (100 Nodes, Markov): APC-RLNC maintains near-perfect packet delivery across the evaluated
  burst durations, while the Random baseline degrades to approximately
  60.6% PDR at a 50-packet burst. The results also reveal a ceiling
  effect in which the Static redundancy baseline achieves similarly
  high delivery under the evaluated redundancy policy..
Adversarial Resilience (20% Malicious Nodes): Achieves 98.02% PDR via Byzantine-resilient median-of-means clustering isolation.
Energy Consumption: 12.7% reduction in energy draw per delivered generation relative to Random RLNC.
Scalability: $O(N \log N)$ distributed runtime complexity; reconfiguration overhead remains <3% at 500 nodes.

---

 📑 Citation

A citation will be added once the accompanying manuscript has completed peer review.

If you use this repository during the review period, please reference the repository URL or contact the authors for the latest manuscript version.

---

 📄 License

Distributed under the [MIT License](LICENSE).
