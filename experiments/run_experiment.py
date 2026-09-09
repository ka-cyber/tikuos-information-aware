#!/usr/bin/env python3
"""Run the pre-registered Stage-1 information-utility experiment.

Primary endpoint:
    delivered downstream utility / (CPU cycles + controller cycles)
at a matched total CPU budget.

The experiment includes in-distribution, OOD, adversarial, and
controller-cost-dominant regimes.  It does not report modeled joules as
measured energy.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from experiments.engine import run_policy
from experiments.statistics.paired import paired_summary

POLICIES=["rr","cost","spt","edf","llf","quality","task","max_utility","utility_density","clairvoyant_dp"]
REGIMES=["homogeneous","independent","high_uncertainty","tight_deadlines",
         "misleading_quality","utility_cost_anticorrelation","nonstationary",
         "adversarial","high_compute_cost","controller_cost_dominant",
         "noisy_hint","delayed_hint","miscalibrated","rank_error","distribution_shift"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seeds",type=int,default=24)
    ap.add_argument("--budget",type=int,default=2400)
    ap.add_argument("--controller-cycles",type=int,default=35)
    ap.add_argument("--out",default="results/stage1.json")
    args=ap.parse_args()
    rows=[]
    for regime in REGIMES:
        for seed in range(args.seeds):
            for policy in POLICIES:
                r=run_policy(seed,policy,regime,args.budget,controller_cycles=args.controller_cycles)
                row=r.__dict__.copy(); row["regime"]=regime; rows.append(row)
    primary={}
    for regime in REGIMES:
        u={p:np.array([x["utility_per_cycle"] for x in rows if x["regime"]==regime and x["policy"]==p])
           for p in POLICIES}
        primary[regime]={"utility_density_vs_rr":paired_summary(u["utility_density"],u["rr"],seed=17)}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"primary_endpoint":"utility_per_cycle","budget_cycles":args.budget,
                               "seeds":args.seeds,"regimes":REGIMES,"policies":POLICIES,"controller_cycles_per_decision":args.controller_cycles,
                               "rows":rows,"paired_statistics":primary},indent=2))
    print(out)
if __name__=="__main__": main()
