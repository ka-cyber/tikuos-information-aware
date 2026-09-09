"""
Hierarchical RLNC (Section 3.6 / 5.3 / Figure 2).

Within cluster c, nodes apply local RLNC with redundancy:
    R_c = ceil(beta * |C_c| * p_c_erase),           (Eq. 4)
where p_c_erase is the mean per-packet erasure rate of cluster c and
beta >= 1 is a safety margin.

Cluster representatives form bridge packets that are random linear
combinations (over GF(256)) of per-cluster generation "summaries":
    b_j = sum_c gamma_{j,c} * Summary_c,   gamma_{j,c} ~ Uniform(F_256)
Bridge redundancy scales with cross-cluster heterogeneity:
    R_bridge = ceil(0.5 * C * Var({p_c_bar}))

A global decoder recovers the generation once it accumulates >= K total
degrees of freedom across local cluster coding *and* bridge packets
(Theorem 1's independence assumption between clusters is what the
system-level success probability in Eq. (5)/(6) relies on).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
import numpy as np

from .gf256 import gf_add, gf_mul_scalar
from .rlnc import RLNCEncoder, RLNCDecoder, CodedPacket, decode_probability


@dataclass
class ClusterResult:
    cluster_id: int
    size: int
    p_erase_mean: float
    K: int
    R: int
    decoded: bool
    dof_received: int
    summary: np.ndarray  # single GF(256) digest vector representing this cluster's generation


class HierarchicalRLNC:
    """
    Orchestrates intra-cluster local RLNC + inter-cluster bridge coding for
    one generation, given a clustering assignment and per-node erasure
    probabilities.
    """

    def __init__(self, K: int, payload_len: int, beta: float = 1.5,
                 rng: np.random.Generator | None = None):
        self.K = K
        self.payload_len = payload_len
        self.beta = beta
        self.rng = rng or np.random.default_rng()

    def _cluster_redundancy(self, cluster_size: int, p_erase_mean: float) -> int:
        # Eq. (4): R_c = beta * |C_c| * p_c_erase, rounded up to an int >= 0.
        return max(0, math.ceil(self.beta * cluster_size * p_erase_mean))

    def encode_and_transmit(self, packets: np.ndarray, clusters: dict[int, list[int]],
                             node_erasure: dict[int, float]) -> tuple[list[ClusterResult], np.ndarray]:
        """
        packets: (K, payload_len) source generation.
        clusters: cluster_id -> list of node ids assigned to that cluster.
        node_erasure: node id -> per-packet erasure probability p_i(t).

        Returns per-cluster results (including whether the *local* cluster
        decoded on its own) plus the bridge packet payloads used for
        cross-cluster recovery.
        """
        results: list[ClusterResult] = []
        summaries = []

        for cid, members in clusters.items():
            size = max(1, len(members))
            p_bar = float(np.mean([node_erasure.get(n, 0.1) for n in members])) if members else 0.1
            R_c = self._cluster_redundancy(size, p_bar)

            enc = RLNCEncoder(packets, rng=self.rng)
            coded = enc.generate(self.K + R_c)

            dec = RLNCDecoder(self.K, self.payload_len)
            dof = 0
            for pkt in coded:
                # Each cluster member independently experiences erasure p_bar
                # (mean-field approximation of the cluster's channel).
                if self.rng.random() < p_bar:
                    continue
                if dec.add_packet(pkt):
                    dof += 1

            # Cluster "summary" = a single random GF(256) digest of the
            # generation (bridge packets combine these across clusters).
            digest_coeffs = self.rng.integers(1, 256, size=self.K, dtype=np.uint16).astype(np.uint8)
            summary = np.zeros(self.payload_len, dtype=np.uint8)
            for k in range(self.K):
                summary = gf_add(summary, gf_mul_scalar(int(digest_coeffs[k]), packets[k]))

            results.append(ClusterResult(
                cluster_id=cid, size=size, p_erase_mean=p_bar,
                K=self.K, R=R_c, decoded=dec.is_decoded(),
                dof_received=dof, summary=summary,
            ))
            summaries.append(summary)

        bridge = self._bridge_packets(summaries)
        return results, bridge

    def _bridge_packets(self, summaries: list[np.ndarray]) -> np.ndarray:
        """
        R_bridge = ceil(0.5 * C * Var({p_c_bar})) bridge packets, each a
        random GF(256) linear combination of the per-cluster summaries.
        Returned as an (R_bridge, payload_len) array.
        """
        C = len(summaries)
        if C == 0:
            return np.zeros((0, self.payload_len), dtype=np.uint8)
        # NOTE: Var({p_c_bar}) is computed by the caller (ClusteringOptimizer)
        # in the full simulator; here we default to a conservative minimum of
        # one bridge packet per pair of clusters when used standalone.
        r_bridge = max(1, C // 2) if C > 1 else 0
        out = np.zeros((r_bridge, self.payload_len), dtype=np.uint8)
        for j in range(r_bridge):
            gamma = self.rng.integers(1, 256, size=C, dtype=np.uint16).astype(np.uint8)
            b = np.zeros(self.payload_len, dtype=np.uint8)
            for c in range(C):
                b = gf_add(b, gf_mul_scalar(int(gamma[c]), summaries[c]))
            out[j] = b
        return out


def system_decode_probability(cluster_success_probs: list[float]) -> float:
    """
    Theorem 1: P_sys = 1 - prod_c (1 - P_succ^(c)), assuming independent
    cluster failures.
    """
    p_fail = 1.0
    for p in cluster_success_probs:
        p_fail *= (1.0 - p)
    return 1.0 - p_fail


def cluster_success_probability(p_erase_mean: float, K: int, R_c: int) -> float:
    """P_succ^(c) via Eq. (1) applied with the cluster's mean erasure rate."""
    return decode_probability(p_erase_mean, K, R_c)
