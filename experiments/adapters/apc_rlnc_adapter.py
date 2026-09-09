"""Adapter using the supplied APC-RLNC GF(256)/RLNC implementation.

It estimates communication completion probability for an end-to-end task.
This module is an application workload, not a kernel dependency.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
VENDOR=Path(__file__).resolve().parents[2]/"vendor"/"apc-rlnc"
sys.path.insert(0,str(VENDOR/"simulation"))
from coding.rlnc import RLNCEncoder, RLNCDecoder

def transmit_generation(seed:int, K:int=8, redundancy:int=4, erasure:float=0.2, payload_len:int=8):
    rng=np.random.default_rng(seed)
    packets=rng.integers(0,256,size=(K,payload_len),dtype=np.uint16).astype(np.uint8)
    coded=RLNCEncoder(packets,rng=rng).generate(K+redundancy)
    dec=RLNCDecoder(K,payload_len); received=0
    for pkt in coded:
        if rng.random()>=erasure:
            received+=1; dec.add_packet(pkt)
    return {"decoded":dec.is_decoded(),"rank":dec.rank(),"tx":K+redundancy,
            "received":received,"redundancy":redundancy/(K+redundancy)}

def decode_probability(erasure:float,K:int,redundancy:int)->float:
    # Exact binomial received-packet probability used by supplied APC-RLNC
    # implementation; finite-field rank deficiency is intentionally separate.
    from math import comb
    n=K+redundancy
    return float(sum(comb(n,k)*(1-erasure)**k*erasure**(n-k) for k in range(K,n+1)))
