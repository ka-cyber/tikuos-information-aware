#!/usr/bin/env python3
"""Characterize the failure boundary instead of selecting a favorable regime."""
from __future__ import annotations
import argparse,csv
from pathlib import Path
import numpy as np
from experiments.engine import run_policy
from experiments.statistics.paired import paired_summary

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seeds",type=int,default=24)
    ap.add_argument("--budget",type=int,default=2400)
    ap.add_argument("--out",default="results/sensitivity.csv")
    a=ap.parse_args(); rows=[]
    for sigma in np.linspace(0,3.0,25):
        x=[];y=[]
        for seed in range(a.seeds):
            x.append(run_policy(seed,"utility_density","independent",a.budget,hint_noise=float(sigma)).utility_per_cycle)
            y.append(run_policy(seed,"rr","independent",a.budget).utility_per_cycle)
        st=paired_summary(x,y,seed=91)
        rows.append({"sweep":"hint_noise","value":float(sigma),"mean_diff":st["mean_difference"],
                     "ci_low":st["ci95"][0],"ci_high":st["ci95"][1],"p":st["permutation_p"]})
    for flip in np.linspace(0,1,21):
        x=[];y=[]
        for seed in range(a.seeds):
            x.append(run_policy(seed,"utility_density","independent",a.budget,hint_flip=float(flip)).utility_per_cycle)
            y.append(run_policy(seed,"rr","independent",a.budget).utility_per_cycle)
        st=paired_summary(x,y,seed=93)
        rows.append({"sweep":"hint_rank_flip","value":float(flip),"mean_diff":st["mean_difference"],
                     "ci_low":st["ci95"][0],"ci_high":st["ci95"][1],"p":st["permutation_p"]})
    for delay in [1,2,3,5,8,12]:
        x=[];y=[]
        for seed in range(a.seeds):
            x.append(run_policy(seed,"utility_density","delayed_hint",a.budget,hint_delay=delay).utility_per_cycle)
            y.append(run_policy(seed,"rr","delayed_hint",a.budget).utility_per_cycle)
        st=paired_summary(x,y,seed=94)
        rows.append({"sweep":"hint_delay_ticks","value":delay,"mean_diff":st["mean_difference"],
                     "ci_low":st["ci95"][0],"ci_high":st["ci95"][1],"p":st["permutation_p"]})
    for cc in [0,10,25,50,75,100,150,250,400,600,800,1000,1200,1600,2000]:
        x=[];y=[]
        for seed in range(a.seeds):
            x.append(run_policy(seed,"utility_density","independent",a.budget,controller_cycles=cc).utility_per_cycle)
            y.append(run_policy(seed,"rr","independent",a.budget,controller_cycles=cc).utility_per_cycle)
        st=paired_summary(x,y,seed=92)
        rows.append({"sweep":"controller_cycles_per_decision","value":cc,"mean_diff":st["mean_difference"],
                     "ci_low":st["ci95"][0],"ci_high":st["ci95"][1],"p":st["permutation_p"]})
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    print(out)
if __name__=="__main__":main()
