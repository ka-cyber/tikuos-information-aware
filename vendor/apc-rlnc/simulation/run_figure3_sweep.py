#!/usr/bin/env python3
"""
Figure 3: PDR vs Burst Duration Sweep

Runs the 2-state Markov burst-error experiment for the implemented
schemes (Random, Static, APC) and saves the aggregated results as CSV.

Output:
    figure3_sweep_results.csv
"""

import csv
import time
from pathlib import Path

from simulator import SimConfig, Simulator
from metrics import aggregate_runs


# ---------------------------------------------------------------------
# Experiment Configuration
# ---------------------------------------------------------------------

BURSTS = [5, 10, 20, 30, 40, 50, 60]
SCHEMES = ["random", "static", "apc"]

N_RUNS = 50

CONFIG = dict(
    n_nodes=100,
    channel="markov",
    T=500,
    generation_interval=5,
    K=32,
    tau=20,
    churn_rate=0.02,
)

OUTPUT_FILE = Path(__file__).parent / "figure3_sweep_results.csv"


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    rows = []
    start_time = time.time()

    total_jobs = len(SCHEMES) * len(BURSTS)
    job = 0

    for scheme in SCHEMES:
        for burst in BURSTS:

            job += 1

            print(
                f"\n[{job}/{total_jobs}] "
                f"Scheme={scheme.upper()}  Burst={burst}",
                flush=True,
            )

            summaries = []

            for seed in range(N_RUNS):

                cfg = SimConfig(
                    **CONFIG,
                    burst_duration=burst,
                    scheme=scheme,
                    seed=seed,
                )

                sim = Simulator(cfg)
                summaries.append(sim.run())

            agg = aggregate_runs(summaries)

            row = {
                "scheme": scheme,
                "burst_duration_packets": burst,
                "pdr_pct_mean": round(agg["pdr_pct"]["mean"], 3),
                "pdr_pct_std": round(agg["pdr_pct"]["std"], 3),
                "n_runs": N_RUNS,
            }

            rows.append(row)

            elapsed = time.time() - start_time

            print(
                f"    PDR = {row['pdr_pct_mean']:.3f}% "
                f"(±{row['pdr_pct_std']:.3f})   "
                f"Elapsed = {elapsed:.1f}s",
                flush=True,
            )

    with OUTPUT_FILE.open("w", newline="") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "scheme",
                "burst_duration_packets",
                "pdr_pct_mean",
                "pdr_pct_std",
                "n_runs",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\n--------------------------------------")
    print("Figure 3 sweep completed successfully.")
    print(f"Results saved to: {OUTPUT_FILE}")
    print(f"Total runtime: {time.time() - start_time:.1f} s")
    print("--------------------------------------")


if __name__ == "__main__":
    main()