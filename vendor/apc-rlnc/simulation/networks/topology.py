"""
Network Topology and Dynamics (Section 3.1).

G_t = (V_t, E_t) at discrete time t = 0, 1, ..., T. Nodes depart with rate
lambda_leave and new nodes join to maintain expected size N. Churn follows
a Poisson process with per-step rate rho_churn in [0.02, 0.10].
"""
from __future__ import annotations
import itertools
import networkx as nx
import numpy as np


class DynamicTopology:
    def __init__(self, target_size: int, churn_rate: float = 0.02,
                 rng: np.random.Generator | None = None):
        self.target_size = target_size
        self.churn_rate = churn_rate
        self.rng = rng or np.random.default_rng()
        self._id_counter = itertools.count()
        self.graph = nx.Graph()
        for _ in range(target_size):
            self._add_node()

    def _add_node(self) -> int:
        nid = next(self._id_counter)
        self.graph.add_node(nid)
        return nid

    def node_ids(self) -> list[int]:
        return list(self.graph.nodes)

    def step_churn(self) -> tuple[list[int], list[int]]:
        """
        Poisson-process churn: each node independently departs with
        probability churn_rate this step; new nodes join to restore the
        expected population back toward target_size. Returns
        (departed_ids, joined_ids).
        """
        current = self.node_ids()
        n_leave = self.rng.poisson(self.churn_rate * len(current)) if current else 0
        n_leave = min(n_leave, len(current))
        departed = list(self.rng.choice(current, size=n_leave, replace=False)) if n_leave else []
        for d in departed:
            self.graph.remove_node(d)

        deficit = max(0, self.target_size - self.graph.number_of_nodes())
        n_join = self.rng.poisson(self.churn_rate * self.target_size)
        n_join = min(n_join + deficit, deficit + n_join)  # bias toward closing the deficit
        n_join = max(n_join, deficit)
        joined = [self._add_node() for _ in range(n_join)]

        return [int(d) for d in departed], joined

    def build_random_geometric(self, positions: dict[int, tuple[float, float]],
                                radius: float) -> None:
        """Rebuild edges from node positions using a communication radius."""
        self.graph.remove_edges_from(list(self.graph.edges))
        ids = self.node_ids()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if a not in positions or b not in positions:
                    continue
                (xa, ya), (xb, yb) = positions[a], positions[b]
                d = ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5
                if d <= radius:
                    self.graph.add_edge(a, b, distance=d)
