"""
Reliability Tracking Module (Section 3.4 / 5.1).

Each node i maintains an EWMA reliability score:
    s_i(t) = alpha * l_i(t) + (1 - alpha) * s_i(t - 1),     (Eq. 2)
where l_i(t) in [0, 1] is the instantaneous packet success rate and
alpha = 0.2 is the smoothing factor. s_i(t) estimates 1 - p_i(t).
"""
from __future__ import annotations
import numpy as np


class ReliabilityTracker:
    """Maintains per-node EWMA reliability scores s_i(t)."""

    def __init__(self, alpha: float = 0.2, init_score: float = 0.9):
        self.alpha = alpha
        self.init_score = init_score
        self._scores: dict[int, float] = {}

    def register(self, node_id: int, init_score: float | None = None) -> None:
        self._scores.setdefault(node_id, self.init_score if init_score is None else init_score)

    def update(self, node_id: int, instantaneous_success_rate: float) -> float:
        """Apply Eq. (2) for one node given l_i(t) in [0, 1]. Returns new s_i(t)."""
        l_t = float(np.clip(instantaneous_success_rate, 0.0, 1.0))
        prev = self._scores.get(node_id, self.init_score)
        s_t = self.alpha * l_t + (1 - self.alpha) * prev
        self._scores[node_id] = s_t
        return s_t

    def update_from_erasure(self, node_id: int, was_erased: bool) -> float:
        """Convenience: update from a single packet outcome (1 ACK trial)."""
        return self.update(node_id, 0.0 if was_erased else 1.0)

    def score(self, node_id: int) -> float:
        return self._scores.get(node_id, self.init_score)

    def scores(self) -> dict[int, float]:
        return dict(self._scores)

    def drop(self, node_id: int) -> None:
        self._scores.pop(node_id, None)

    def estimated_erasure(self, node_id: int) -> float:
        """s_i(t) estimates 1 - p_i(t), so p_i(t) estimate is 1 - s_i(t)."""
        return 1.0 - self.score(node_id)
