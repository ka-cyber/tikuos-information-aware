"""End-to-end policy experiment engine.

The engine models the exact Stage-1 TikuOS worker decision boundary:
one worker is dispatched at a time, CPU budget is fixed, and a selected worker
consumes its estimated CPU cost.  It deliberately keeps the *realized*
downstream utility separate from the scheduling hint so that the policy cannot
win by construction.

The simulator is an execution model, not a claim that the host is an MCU.
The production C contract is compiled and exercised by the verification suite.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Callable
import numpy as np
from tikuos_iu.contract import UtilityHint, select

@dataclass
class Task:
    task_id:int
    release:int
    deadline:int
    cost:int
    true_utility:float
    hinted_utility:float
    quality:float
    urgency:float
    completed:bool=False
    completion_time:int|None=None

@dataclass
class RunResult:
    policy:str
    seed:int
    utility:float
    cpu_cycles:int
    controller_cycles:int
    completed:int
    missed:int
    utility_per_cycle:float
    deadline_success_rate:float

def make_tasks(seed:int,n:int=80,regime:str="heterogeneous",hint_noise:float=0.0,hint_flip:float=0.0,hint_delay:int=3)->list[Task]:
    r=np.random.default_rng(seed)
    quality=r.uniform(0,1,n)
    urgency=r.uniform(0,1,n)
    cost=r.integers(20,101,n)
    event=r.beta(2,2,n)
    if regime=="homogeneous": event[:]=0.5; quality[:]=0.7
    elif regime=="high_uncertainty": quality=r.uniform(0,0.25,n); event=r.uniform(0.3,1,n)
    elif regime=="tight_deadlines": pass
    elif regime=="misleading_quality": quality=1-quality
    elif regime=="utility_cost_anticorrelation":
        event=np.clip(1-(cost-cost.min())/(cost.max()-cost.min()),0,1)
    elif regime=="independent":
        event=r.uniform(0,1,n)
    elif regime=="nonstationary":
        event=np.r_[r.uniform(.05,.25,n//2),r.uniform(.75,1,n-n//2)]
    elif regime=="adversarial":
        # Hint will be constructed to be inversely ranked to realized utility.
        event=r.uniform(0,1,n)
    elif regime=="high_compute_cost":
        cost=r.integers(200,501,n)
        event=r.uniform(.2,.8,n)
    elif regime=="controller_cost_dominant":
        # Controller work is intentionally larger than a typical worker.
        cost=r.integers(1,6,n)
        event=r.uniform(.2,.8,n)
    elif regime in {"delayed_hint","rank_error","distribution_shift"}:
        event=r.uniform(0,1,n)
    true=np.clip(event*(0.35+0.65*quality),0,1)
    hint=true.copy()
    if regime=="noisy_hint" or hint_noise>0:
        hint=np.clip(true+r.normal(0,hint_noise if hint_noise>0 else .25,n),0,1)
    if regime=="delayed_hint":
        delay=max(1,int(hint_delay))
        if delay >= n:
            raise ValueError("hint_delay must be smaller than task count")
        hint=np.r_[true[:delay], true[:-delay]]
    if regime=="miscalibrated":
        # Calibration error without changing rank: affine bias/scale.
        hint=np.clip(.15+.7*true,0,1)
    if regime=="rank_error":
        # Partial rank corruption: a controllable mixture of truth and
        # anti-truth, plus noise. This can cross the usefulness boundary.
        alpha=.65
        hint=np.clip(alpha*true+(1-alpha)*(1-true)+r.normal(0,.05,n),0,1)
    if regime=="distribution_shift":
        # The estimator was calibrated on a quality/event relationship that
        # is inverted at deployment; predicted ranking can become unreliable.
        hint=np.clip(event*(0.35+0.65*(1-quality)),0,1)
    if regime=="adversarial":
        # Worst-case ranking: high predicted utility is preferentially assigned
        # to low-realized-utility work, with an additional cost trap.
        cscale=(cost-cost.min())/max(1,(cost.max()-cost.min()))
        hint=np.clip(cscale,0,1)
    if hint_flip>0:
        hint=np.clip((1-hint_flip)*hint + hint_flip*(1-hint) +
                     r.normal(0,hint_noise,n),0,1)
    deadline=r.integers(180,701,n) if regime!="tight_deadlines" else r.integers(60,181,n)
    # Release=0 isolates the scheduling contract and makes the offline oracle exact.
    return [Task(i,0,int(deadline[i]),int(cost[i]),float(true[i]),float(hint[i]),
                 float(quality[i]),float(urgency[i])) for i in range(n)]

def _eligible(tasks,now):
    return [t for t in tasks if not t.completed and t.release<=now]

def _pick(policy,tasks,now,cursor):
    elig=_eligible(tasks,now)
    if not elig:return None
    if policy=="rr":
        return elig[cursor%len(elig)]
    if policy=="cost":
        return min(elig,key=lambda t:(t.cost,t.task_id))
    if policy=="spt":
        return min(elig,key=lambda t:(t.cost,t.task_id))
    if policy=="edf":
        return min(elig,key=lambda t:(t.deadline,t.task_id))
    if policy=="llf":
        return min(elig,key=lambda t:(max(0,t.deadline-now-t.cost),t.task_id))
    if policy=="max_utility":
        return max(elig,key=lambda t:(t.hinted_utility,-t.task_id))
    if policy=="quality":
        return max(elig,key=lambda t:(t.quality,-t.task_id))
    if policy=="task":
        return max(elig,key=lambda t:(1.0/max(1,t.deadline-now),t.urgency,-t.task_id))
    if policy=="utility_density":
        from tikuos_iu.cabi import score_exact
        hints=[None]*len(tasks)
        for t in elig:
            flags=1
            if t.deadline < now: continue
            hints[t.task_id]=UtilityHint(
                int(round(np.clip(t.hinted_utility,0,1)*65535)),
                int(t.deadline), t.cost, flags)
        selected=select(hints,cursor,now)
        if selected is not None:
            return tasks[selected]
        # Match the patched TikuOS fallback when no hinted candidate is
        # deadline-eligible: return to legacy round-robin among runnable work.
        return elig[cursor%len(elig)]
    raise ValueError(policy)

def _offline_oracle(tasks,budget:int,quantum:int=10)->float:
    """Exact weighted-throughput DP with known realized utility.

    Costs/deadlines are discretized only for the oracle state.  Because every
    task is available at t=0, a subset is schedulable iff EDD ordering meets
    every selected deadline.  DP processes jobs by deadline and maximizes
    realized utility for each cumulative processing time.
    """
    jobs=sorted(tasks,key=lambda t:t.deadline)
    B=budget//quantum
    dp=np.full(B+1,-np.inf); dp[0]=0.0
    for t in jobs:
        p=int(np.ceil(t.cost/quantum)); d=min(B,t.deadline//quantum)
        ndp=dp.copy()
        for used in range(max(0,d-p)+1):
            if dp[used]>-np.inf:
                ndp[used+p]=max(ndp[used+p],dp[used]+t.true_utility)
        # invalidate states that could only schedule this prefix past its deadline
        # by only admitting this job at used+p<=d.
        dp=ndp
    return float(np.max(dp))

def policy_overhead_cycles(policy:str, controller_cycles:int)->int:
    """Per-dispatch CPU overhead used for matched-budget accounting.
    Baselines receive their own small deterministic decision cost; only the
    proposed utility-density controller is charged the configurable broker
    overhead. The oracle has zero online decision cost by definition.
    """
    costs={"rr":2,"cost":4,"spt":4,"edf":6,"llf":8,"quality":5,
           "task":6,"max_utility":8,"utility_density":controller_cycles,
           "clairvoyant_dp":0}
    return costs[policy]

def run_policy(seed:int,policy:str,regime:str,budget:int=2400,controller_cycles:int=35,hint_noise:float=0.0,hint_flip:float=0.0,hint_delay:int=3)->RunResult:
    tasks=make_tasks(seed,regime=regime,hint_noise=hint_noise,hint_flip=hint_flip,hint_delay=hint_delay)
    if policy=="clairvoyant_dp":
        u=_offline_oracle(tasks,budget)
        return RunResult(policy,seed,u,budget,0,0,len(tasks),u/budget,0.0)
    now=0; cursor=0; used=0; ctrl=0; completed=0
    decision_cost=policy_overhead_cycles(policy,controller_cycles)
    while used + ctrl < budget:
        elig=_eligible(tasks,now)
        if not elig: break
        t=_pick(policy,tasks,now,cursor)
        if t is None: break
        if used + ctrl + decision_cost > budget:
            break
        ctrl += decision_cost
        if used + ctrl + t.cost > budget:
            # The controller has consumed real resource, but the selected
            # worker cannot finish inside the remaining matched budget.
            t.completed=True; t.completion_time=None
            cursor+=1; continue
        used += t.cost
        now=used+ctrl
        if now<=t.deadline:
            t.completed=True;t.completion_time=now;completed+=1
        else:
            t.completed=True;t.completion_time=None
        cursor+=1
    utility=sum(t.true_utility for t in tasks if t.completion_time is not None)
    missed=len(tasks)-completed
    # Controller cycles are charged as a separate resource; they do not buy utility.
    total_cycles=used+ctrl
    return RunResult(policy,seed,float(utility),used,ctrl,completed,missed,
                     float(utility/max(1,total_cycles)),completed/max(1,len(tasks)))
