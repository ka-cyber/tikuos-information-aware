#!/usr/bin/env python3
"""Produce pre-specified primary and regime-level statistical tables."""
import argparse,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.statistics.paired import paired_summary, holm_bonferroni

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out",default="results/statistical_summary.json")
    a=ap.parse_args()
    d=json.loads(Path(a.input).read_text())
    rows=d["rows"]; regimes=d["regimes"]
    out={"primary_endpoint":d["primary_endpoint"],"comparison":"utility_density - rr",
         "regimes":{}}
    ps=[]
    for regime in regimes:
        x=np.array([r["utility_per_cycle"] for r in rows if r["regime"]==regime and r["policy"]=="utility_density"])
        y=np.array([r["utility_per_cycle"] for r in rows if r["regime"]==regime and r["policy"]=="rr"])
        st=paired_summary(x,y,seed=1701)
        out["regimes"][regime]=st
        ps.append(st["permutation_p"])
    adj=holm_bonferroni(ps)
    for regime,p in zip(regimes,adj):
        out["regimes"][regime]["holm_adjusted_permutation_p"]=float(p)
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n")
    print(a.out)
if __name__=="__main__": main()
