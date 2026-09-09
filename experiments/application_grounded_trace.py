#!/usr/bin/env python3
"""Generate an application-grounded workload trace using the supplied assets.

This is intentionally separate from the generic scheduler benchmark.  It proves
the adapters consume real upstream implementations without claiming that the
upstream applications are kernel-integrated.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from experiments.adapters.cardiofusion_adapter import observation, expected_utility
from experiments.adapters.apc_rlnc_adapter import transmit_generation

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--windows",type=int,default=32)
    ap.add_argument("--out",default="results/application_grounded_trace.json")
    a=ap.parse_args(); rows=[]
    for i in range(a.windows):
        degradation=(i%8)/7
        obs=observation(1000+i,degradation)
        event=float(np.clip(.15+.7*((i%11)/10),0,1))
        u=expected_utility(obs,event)
        comm=transmit_generation(2000+i,K=8,redundancy=2+(i%5),
                                 erasure=.05+.25*degradation)
        rows.append({"window":i,"degradation":degradation,**obs,
                     "event_probability":event,"expected_utility":u,**{f"rlnc_{k}":v for k,v in comm.items()}})
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(rows,indent=2))
    print(p)
if __name__=="__main__":main()
