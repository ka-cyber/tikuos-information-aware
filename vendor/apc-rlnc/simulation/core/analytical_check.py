"""
Validates the closed-form analytical claims in Section 4 against both
direct numerical evaluation and Monte-Carlo simulation.

Referenced from the README as:
    "Theorem 1 (Hierarchical Success Probability): Validated in
     simulation/core/analytical_check.py showing that empirical system
     performance aligns within 1% of the derived closed-form multi-tier
     success curve."

Run directly:  python -m core.analytical_check
"""
from __future__ import annotations
import numpy as np

from coding.rlnc import decode_probability, RLNCEncoder, RLNCDecoder
from coding.hierarchical import cluster_success_probability, system_decode_probability
from core.ftrl import theoretical_regret_bound


def monte_carlo_decode_rate(p_erasure: float, K: int, R: int, trials: int = 4000,
                             payload_len: int = 8, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    succ = 0
    for _ in range(trials):
        packets = rng.integers(0, 256, size=(K, payload_len), dtype=np.uint16).astype(np.uint8)
        enc = RLNCEncoder(packets, rng=rng)
        coded = enc.generate(K + R)
        dec = RLNCDecoder(K, payload_len)
        for pkt in coded:
            if rng.random() < p_erasure:
                continue
            dec.add_packet(pkt)
        if dec.is_decoded():
            succ += 1
    return succ / trials


def check_theorem1(K: int = 32, R_c: int = 16, p_bar: float = 0.225,
                    n_clusters: int = 5, trials: int = 4000) -> dict:
    closed_form = cluster_success_probability(p_bar, K, R_c)
    mc = monte_carlo_decode_rate(p_bar, K, R_c, trials=trials)
    system_closed_form = system_decode_probability([closed_form] * n_clusters)

    manuscript_claim_per_cluster = 0.989
    manuscript_claim_system = 0.99999

    rel_err_mc = abs(closed_form - mc) / closed_form
    rel_err_manuscript = abs(closed_form - manuscript_claim_per_cluster) / manuscript_claim_per_cluster

    return {
        'closed_form_per_cluster': closed_form,
        'monte_carlo_per_cluster': mc,
        'relative_error_closed_form_vs_mc': rel_err_mc,
        'system_closed_form_C5': system_closed_form,
        'manuscript_claim_per_cluster': manuscript_claim_per_cluster,
        'manuscript_claim_system_C5': manuscript_claim_system,
        'relative_error_vs_manuscript': rel_err_manuscript,
        'note': (
            "Eq. (1)/(5) evaluated exactly with p_bar=0.225, K=32, R_c=16 gives "
            f"{closed_form:.4f}, not the 0.989 printed in the manuscript. "
            "Matching 0.989 requires R_c ~= 18 at this erasure rate. This looks "
            "like a manuscript arithmetic/rounding slip, not a simulator bug -- "
            "the closed-form and Monte Carlo estimates agree with each other to "
            f"within {rel_err_mc*100:.2f}%. Recommend fixing R_c or the quoted "
            "probability before submission."
        ),
    }


def check_theorem2(T: int = 500, tau: int = 20, G: float = 0.05) -> dict:
    """
    Section 4.2 worked example: "For tau=20 reconfiguration period, total
    regret over T=500 steps is approximately 0.05*sqrt(500/20) ~= 0.25."
    NOTE: the manuscript's own bound is G^2*sqrt(2T); the worked example's
    arithmetic (0.05*sqrt(T/tau)) does not match Theorem 2 as stated either.
    We report both readings.
    """
    bound_theorem2 = theoretical_regret_bound(T, G)
    worked_example_literal = G * np.sqrt(T / tau)
    return {
        'theorem2_bound_G2_sqrt_2T': bound_theorem2,
        'worked_example_as_literally_written': worked_example_literal,
        'note': (
            "Theorem 2 as stated gives Regret(T) <= G^2*sqrt(2T). With G=0.05, "
            f"T=500 that bound is {bound_theorem2:.4f}, not ~0.25. The '~0.25' "
            "figure in the text matches G*sqrt(T/tau) instead -- a different "
            "(and undeclared) formula. Worth reconciling notation before submission."
        ),
    }


if __name__ == '__main__':
    import json
    print("=== Theorem 1 check ===")
    print(json.dumps(check_theorem1(), indent=2, default=float))
    print("\n=== Theorem 2 check ===")
    print(json.dumps(check_theorem2(), indent=2, default=float))
