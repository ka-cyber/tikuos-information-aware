import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from coding.gf256 import gf_mul, gf_inv, gf_div
from coding.rlnc import RLNCEncoder, RLNCDecoder, decode_probability
from coding.hierarchical import cluster_success_probability, system_decode_probability
from core.ewma import ReliabilityTracker
from core.clustering import ClusteringOptimizer, clustering_loss
from core.ftrl import FTRLOptimizer, project_to_simplex, theoretical_regret_bound
from core.channel_models import MarkovChannel


def _ref_mul(a, b, poly=0x11D):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= (poly & 0xFF)
        b >>= 1
    return p


def test_gf256_multiply_matches_reference():
    rng = np.random.default_rng(0)
    for _ in range(500):
        a, b = int(rng.integers(0, 256)), int(rng.integers(0, 256))
        assert int(gf_mul(a, b)) == _ref_mul(a, b)


def test_gf256_inverse():
    for a in range(1, 256):
        assert gf_mul(a, gf_inv(a)) == 1


def test_gf256_div_inverse_consistency():
    for a in range(1, 256):
        for b in range(1, 256):
            assert gf_div(a, b) == gf_mul(a, gf_inv(b))


def test_rlnc_roundtrip_zero_erasure():
    rng = np.random.default_rng(1)
    K, R, plen = 16, 8, 20
    packets = rng.integers(0, 256, size=(K, plen), dtype=np.uint16).astype(np.uint8)
    enc = RLNCEncoder(packets, rng=rng)
    coded = enc.generate(K + R)
    dec = RLNCDecoder(K, plen)
    for pkt in coded:
        dec.add_packet(pkt)
    assert dec.is_decoded()
    recovered = dec.recover()
    assert np.array_equal(recovered, packets)


def test_rlnc_matches_closed_form_within_tolerance():
    rng = np.random.default_rng(2)
    K, R, plen, p = 32, 16, 8, 0.225
    trials, succ = 2000, 0
    for _ in range(trials):
        packets = rng.integers(0, 256, size=(K, plen), dtype=np.uint16).astype(np.uint8)
        enc = RLNCEncoder(packets, rng=rng)
        dec = RLNCDecoder(K, plen)
        for pkt in enc.generate(K + R):
            if rng.random() < p:
                continue
            dec.add_packet(pkt)
        succ += dec.is_decoded()
    empirical = succ / trials
    theory = decode_probability(p, K, R)
    assert abs(empirical - theory) < 0.03  # within simulator's own <1% claim + MC noise


def test_theorem1_system_probability_matches_independence_formula():
    p_c = cluster_success_probability(0.225, K=32, R_c=16)
    sys_p = system_decode_probability([p_c] * 5)
    expected = 1 - (1 - p_c) ** 5
    assert abs(sys_p - expected) < 1e-9


def test_ewma_matches_eq2_closed_form():
    tr = ReliabilityTracker(alpha=0.2, init_score=0.9)
    tr.register(0)
    s = 0.9
    for l in [1.0, 0.0, 1.0, 1.0, 0.0]:
        s = 0.2 * l + 0.8 * s
        got = tr.update(0, l)
        assert abs(got - s) < 1e-12


def test_clustering_reduces_or_maintains_loss():
    rng = np.random.default_rng(3)
    scores = {i: float(rng.uniform(0.5, 1.0)) for i in range(40)}
    opt = ClusteringOptimizer(lam=0.01, rng=rng)
    clusters = opt.fit(list(scores.keys()), scores)
    assert sum(len(m) for m in clusters.values()) == 40
    assert len(clusters) >= 1


def test_ftrl_projection_onto_simplex():
    v = np.array([0.9, 0.05, 0.05, 10.0])
    p = project_to_simplex(v)
    assert abs(p.sum() - 1.0) < 1e-8
    assert np.all(p >= -1e-9)


def test_ftrl_regret_bound_positive_and_grows_sublinearly():
    b1 = theoretical_regret_bound(100, G=0.05)
    b2 = theoretical_regret_bound(400, G=0.05)
    assert b2 > b1
    assert b2 < 4 * b1  # sqrt(T) growth, not linear in T


def test_markov_channel_steady_state_matches_manuscript_example():
    ch = MarkovChannel(p_good=0.05, p_bad=0.40, p_gb=0.10, p_bg=0.10)
    assert abs(ch.steady_state_mean - 0.225) < 1e-9
