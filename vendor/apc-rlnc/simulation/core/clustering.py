"""
Clustering Objective and Distributed Clustering Module (Section 3.5 / 5.2,
Algorithm 1).

At reconfiguration epochs, peers partition into C(t) clusters
{C_1,t, ..., C_C(t),t} by minimizing:
    L(C_1:C, t) = sum_c [ Var_{i in C_c}[s_i(t)] - lambda * |C_c| ]   (Eq. 3)
where Var penalizes intra-cluster heterogeneity and lambda > 0 rewards
larger clusters (discourages over-fragmentation).

Algorithm 1 (Distributed Adaptive Clustering):
    1. Initialize k = floor(sqrt(N)/2) cluster centers uniformly.
    2. For r = 1..R_max gossip rounds:
        a. each node broadcasts (s_i, clusterID_i)
        b. update local centroid estimates via weighted average
        c. reassign i to cluster c* = argmin_c |s_i - mu_c|
    3. Compute loss (Eq. 3) and merge/split clusters if beneficial.
    4. Return final clusters.

Because s_i(t) is a scalar reliability score, this reduces to 1-D k-means,
which is exactly what "gossip-based consensus" on (mean, variance) can
converge to in O(log N) rounds (Section 5.2, citing Boyd & Xiao 2004).
"""
from __future__ import annotations
import math
import numpy as np


def clustering_loss(clusters: dict[int, list[float]], lam: float) -> float:
    """Eq. (3): sum_c [Var(scores in c) - lambda * |c|]."""
    total = 0.0
    for members in clusters.values():
        if len(members) == 0:
            continue
        var = float(np.var(members)) if len(members) > 1 else 0.0
        total += var - lam * len(members)
    return total


class ClusteringOptimizer:
    """
    1-D k-means over EWMA reliability scores, matching Algorithm 1's
    "argmin_c |s_i - mu_c|" reassignment rule, plus the Eq. (3) loss used to
    decide whether to merge/split clusters at each reconfiguration epoch.
    """

    def __init__(self, lam: float = 0.01, r_max: int = 10,
                 rng: np.random.Generator | None = None):
        self.lam = lam
        self.r_max = r_max
        self.rng = rng or np.random.default_rng()
        self.centroids: np.ndarray | None = None

    @staticmethod
    def initial_k(n_nodes: int) -> int:
        return max(1, math.floor(math.sqrt(max(1, n_nodes)) / 2))

    def fit(self, node_ids: list[int], scores: dict[int, float],
            k: int | None = None) -> dict[int, list[int]]:
        """
        Runs Algorithm 1's gossip-round loop (simulated centrally here; the
        Go testbed daemon in testbed/clustering-go performs the literal
        peer-to-peer broadcast version of the same update rule) and returns
        cluster_id -> list of node_ids.
        """
        n = len(node_ids)
        if n == 0:
            return {}
        k = k or self.initial_k(n)
        k = max(1, min(k, n))

        s = np.array([scores.get(i, 0.9) for i in node_ids], dtype=np.float64)

        # Step 1: initialize k centers uniformly over the observed score range.
        lo, hi = float(s.min()), float(s.max())
        if hi - lo < 1e-9:
            centroids = np.full(k, lo)
        else:
            centroids = self.rng.uniform(lo, hi, size=k)
        centroids = np.sort(centroids)

        assignment = np.zeros(n, dtype=int)
        for _ in range(self.r_max):
            # c* = argmin_c |s_i - mu_c|
            dists = np.abs(s[:, None] - centroids[None, :])
            new_assignment = np.argmin(dists, axis=1)
            if np.array_equal(new_assignment, assignment) and _ > 0:
                assignment = new_assignment
                break
            assignment = new_assignment
            # weighted-average centroid update (gossip consensus surrogate)
            for c in range(k):
                members = s[assignment == c]
                if members.size > 0:
                    centroids[c] = members.mean()

        self.centroids = centroids
        clusters: dict[int, list[int]] = {c: [] for c in range(k)}
        for idx, node_id in enumerate(node_ids):
            clusters[int(assignment[idx])].append(node_id)

        clusters = self._merge_split(clusters, scores)
        return {cid: members for cid, members in clusters.items() if members}

    def _merge_split(self, clusters: dict[int, list[int]],
                      scores: dict[int, float]) -> dict[int, list[int]]:
        """
        Step 3 of Algorithm 1: merge two clusters if doing so lowers the
        Eq. (3) loss (discourages singleton/near-empty clusters that a
        larger lambda should have prevented from fragmenting off).
        """
        cluster_ids = [c for c, m in clusters.items() if m]
        changed = True
        clusters = {c: list(m) for c, m in clusters.items() if m}
        while changed and len(clusters) > 1:
            changed = False
            ids = list(clusters.keys())
            base_loss = clustering_loss(
                {c: [scores.get(i, 0.9) for i in m] for c, m in clusters.items()}, self.lam)
            for a_idx in range(len(ids)):
                for b_idx in range(a_idx + 1, len(ids)):
                    a, b = ids[a_idx], ids[b_idx]
                    trial = {c: m for c, m in clusters.items() if c not in (a, b)}
                    trial[a] = clusters[a] + clusters[b]
                    trial_loss = clustering_loss(
                        {c: [scores.get(i, 0.9) for i in m] for c, m in trial.items()}, self.lam)
                    if trial_loss < base_loss:
                        clusters = trial
                        changed = True
                        break
                if changed:
                    break
        return clusters
