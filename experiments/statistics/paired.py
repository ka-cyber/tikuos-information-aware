"""Pre-specified paired statistics for the primary endpoint."""
from __future__ import annotations
import numpy as np
from scipy.stats import wilcoxon

def paired_summary(a,b,seed:int=0,bootstrap:int=20000):
    a=np.asarray(a,float); b=np.asarray(b,float)
    if a.shape!=b.shape or a.ndim!=1: raise ValueError("paired vectors required")
    d=a-b; n=len(d); mean=float(d.mean())
    rng=np.random.default_rng(seed)
    idx=rng.integers(0,n,size=(bootstrap,n))
    means=d[idx].mean(axis=1)
    ci=(float(np.quantile(means,.025)),float(np.quantile(means,.975)))
    # Exact paired sign-flip permutation (2^n when n<=20; Monte Carlo otherwise).
    if n<=20:
        vals=np.array([np.mean(d*np.where([(mask>>i)&1 for i in range(n)],1,-1))
                       for mask in range(1<<n)])
        p=float(np.mean(np.abs(vals)>=abs(mean)))
        perm_mode="exact"
    else:
        signs=rng.choice(np.array([-1.,1.]),size=(20000,n))
        vals=(signs*d).mean(axis=1)
        p=float((1+np.sum(np.abs(vals)>=abs(mean)))/(len(vals)+1))
        perm_mode="monte_carlo"
    try:
        w=wilcoxon(a,b,alternative="two-sided",zero_method="wilcox",method="auto")
        wp=float(w.pvalue)
    except ValueError:
        wp=float("nan")
    sd=float(np.std(d,ddof=1)) if n>1 else float("nan")
    dz=mean/sd if sd>0 else float("nan")
    return {"n":n,"mean_difference":mean,"ci95":ci,"permutation_p":p,
            "permutation_mode":perm_mode,"wilcoxon_p":wp,"cohens_dz":float(dz)}

def paired_bootstrap_ci(d,seed=0,n_boot=20000):
    d=np.asarray(d,float); rng=np.random.default_rng(seed)
    idx=rng.integers(0,len(d),size=(n_boot,len(d)))
    m=d[idx].mean(axis=1)
    return tuple(map(float,np.quantile(m,[.025,.975])))


def holm_bonferroni(pvalues):
    """Return Holm-adjusted p-values in original order."""
    p=np.asarray(pvalues,float)
    if p.ndim!=1: raise ValueError("pvalues must be 1-D")
    m=len(p); out=np.full(m,np.nan)
    finite=[i for i,x in enumerate(p) if np.isfinite(x)]
    ordered=sorted(finite,key=lambda i:p[i])
    running=0.0
    for rank,i in enumerate(ordered):
        adj=min(1.0,(m-rank)*p[i])
        running=max(running,adj)
        out[i]=running
    return out
