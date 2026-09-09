#!/usr/bin/env python3
"""
Simulation entry point (see README "Getting Started").

Example (matches the README verbatim):
    python run_sim.py --nodes 100 --channel markov --burst-duration 50 --runs 50

Output: prints a Table-1/2-style summary to stdout and writes a CSV of
per-run results to --out (default: results.csv).
"""
from __future__ import annotations
import argparse
import csv
import sys
import time

from simulator import SimConfig, Simulator
from metrics import aggregate_runs


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="APC-RLNC discrete-event simulator")
    p.add_argument('--nodes', type=int, default=30, help='number of peers (N)')
    p.add_argument('--channel', choices=['bernoulli', 'markov', 'velocity'],
                    default='bernoulli', help='channel erasure model (Section 3.3)')
    p.add_argument('--burst-duration', type=int, default=50,
                    help='mean bad-state dwell time in packets (Markov channel only)')
    p.add_argument('--scheme', choices=['random', 'static', 'apc'], default='apc',
                    help='encoding/clustering scheme to evaluate')
    p.add_argument('--steps', type=int, default=500, help='simulation steps T')
    p.add_argument('--generation-interval', type=int, default=5)
    p.add_argument('--K', type=int, default=32, help='generation size (source packets)')
    p.add_argument('--beta', type=float, default=1.5, help='cluster redundancy safety margin')
    p.add_argument('--lam', type=float, default=0.01, help='clustering loss lambda (Eq. 3)')
    p.add_argument('--tau', type=int, default=20, help='reconfiguration period (steps)')
    p.add_argument('--churn', type=float, default=0.02, help='per-step churn rate rho_churn')
    p.add_argument('--payload-len', type=int, default=32, help='bytes per packet')
    p.add_argument('--runs', type=int, default=50, help='independent Monte Carlo runs')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--out', type=str, default='results.csv')
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    cfg = SimConfig(
        n_nodes=args.nodes, channel=args.channel, burst_duration=args.burst_duration,
        scheme=args.scheme, T=args.steps, generation_interval=args.generation_interval,
        K=args.K, beta=args.beta, lam=args.lam, tau=args.tau, churn_rate=args.churn,
        payload_len=args.payload_len, seed=args.seed,
    )

    print(f"Running {args.runs} run(s): nodes={args.nodes} channel={args.channel} "
          f"scheme={args.scheme} steps={args.steps} K={args.K} tau={args.tau}",
          file=sys.stderr)

    t0 = time.time()
    run_summaries = []
    for r in range(args.runs):
        run_cfg = SimConfig(**{**cfg.__dict__, 'seed': args.seed + r})
        sim = Simulator(run_cfg)
        run_summaries.append(sim.run())
        print(f"  run {r + 1}/{args.runs} done", file=sys.stderr)
    elapsed = time.time() - t0

    agg = aggregate_runs(run_summaries)

    with open(args.out, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['run_idx'] + list(run_summaries[0].keys()))
        for i, s in enumerate(run_summaries):
            writer.writerow([i] + [s[k] for k in s])

    print("\n=== Summary (mean ± std over {} runs) ===".format(args.runs))
    print(f"{'Metric':<16}{'Mean':>12}{'Std':>12}")
    for k, v in agg.items():
        print(f"{k:<16}{v['mean']:>12.3f}{v['std']:>12.3f}")
    print(f"\nWall-clock time: {elapsed:.2f}s  |  per-run CSV written to: {args.out}")


if __name__ == '__main__':
    main()
