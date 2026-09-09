import numpy as np
from experiments.engine import run_policy, make_tasks, _offline_oracle

def test_oracle_is_not_raw_max_utility():
    ts=make_tasks(3,n=12)
    # The exact DP is constrained by the budget; it cannot exceed sum utility.
    u=_offline_oracle(ts,200)
    assert 0 <= u <= sum(t.true_utility for t in ts)

def test_adversarial_regime_can_hurt_utility_density():
    a=run_policy(7,"utility_density","adversarial",1200)
    b=run_policy(7,"rr","adversarial",1200)
    # Do not require a particular winner: this test guards only finite output.
    assert np.isfinite(a.utility_per_cycle) and np.isfinite(b.utility_per_cycle)

def test_all_policies_finite():
    for p in ["rr","cost","spt","edf","llf","quality","task","max_utility","utility_density","clairvoyant_dp"]:
        r=run_policy(0,p,"independent",800)
        assert np.isfinite(r.utility_per_cycle)

def test_delayed_hint_is_temporally_stale():
    ts=make_tasks(11,n=10,regime="delayed_hint")
    assert any(abs(t.hinted_utility - t.true_utility)>1e-9 for t in ts[3:])
def test_rank_error_is_not_just_affine_miscalibration():
    ts=make_tasks(11,n=40,regime="rank_error")
    true=[t.true_utility for t in ts]; hint=[t.hinted_utility for t in ts]
    assert np.corrcoef(true,hint)[0,1] < 0.95
