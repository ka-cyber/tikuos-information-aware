"""Adapter to the supplied CardioFusion signal-quality implementation.

The kernel never imports this module. It converts physiological observations
into a normalized *expected marginal decision utility* for the generic broker.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

VENDOR = Path(__file__).resolve().parents[2] / "vendor" / "cardiofusion"
if str(VENDOR) not in sys.path: sys.path.insert(0, str(VENDOR))
from preprocessing.signal_quality import assess_segment_quality

def synthetic_ecg_ppg(seed:int, fs:float=250.0, seconds:float=8.0, noise:float=0.05):
    rng=np.random.default_rng(seed); n=int(fs*seconds); t=np.arange(n)/fs
    peaks=(np.arange(1,int(seconds)-0)+0.0)*fs
    peaks=peaks.astype(np.int64)
    ecg=np.zeros(n); ppg=np.zeros(n)
    for p in peaks:
        x=np.arange(n)-p
        ecg += np.exp(-0.5*(x/(0.025*fs))**2)
        ppg += np.exp(-0.5*((x-0.04*fs)/(0.055*fs))**2)
    # Slow baseline and broadband/motion-like degradation.
    ecg += 0.03*np.sin(2*np.pi*0.4*t)
    ppg += 0.02*np.sin(2*np.pi*0.25*t)
    ecg += noise*rng.normal(size=n); ppg += noise*rng.normal(size=n)
    return ecg.astype(np.float64), ppg.astype(np.float64), peaks, fs

def observation(seed:int, degradation:float):
    ecg,ppg,peaks,fs=synthetic_ecg_ppg(seed,noise=0.03+0.25*degradation)
    e=assess_segment_quality(ecg,peaks,fs,"ecg")
    # PPG peaks are phase-shifted from ECG in this synthetic signal.
    ppeaks=np.clip(peaks+int(0.04*fs),0,len(ppg)-1)
    p=assess_segment_quality(ppg,ppeaks,fs,"ppg")
    sqi_e=0.0 if e.sqi is None or np.isnan(e.sqi) else float(np.clip(e.sqi,0,1))
    sqi_p=0.0 if p.sqi is None or np.isnan(p.sqi) else float(np.clip(p.sqi,0,1))
    return {"ecg_sqi":sqi_e,"ppg_sqi":sqi_p,
            "quality":0.5*(sqi_e+sqi_p),
            "valid":bool(e.passes_feasibility and p.passes_feasibility)}

def expected_utility(obs:dict, event_probability:float, modality_gain:float=0.35)->float:
    # Utility is an expected marginal decision benefit, not a quality score.
    # Event probability weights the consequence; residual quality weights how
    # much useful evidence the action can still recover.
    q=float(np.clip(obs["quality"],0,1))
    return float(np.clip(event_probability*(0.35+modality_gain*q),0,1))
