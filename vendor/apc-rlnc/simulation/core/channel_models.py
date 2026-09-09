"""
Heterogeneous Channel Models (Section 3.3).

Three erasure-probability generators, one per node/link:

* Bernoulli:              p_i ~ Uniform(0.05, 0.25), i.i.d. per node, static.
* 2-state Markov:         alternates good (p_g=0.05) / bad (p_b=0.40) with
                           transition probabilities P_gb = P_bg = 0.10.
* Velocity-dependent:     p_i(t) = p_base + beta * |v_i(t)|, beta=0.003 s/m,
                           for vehicular (Doppler-driven) scenarios.

Also implements the random-waypoint path-loss model used to seed p_base in
the vehicular case (Section 3.1):
    p_ij(t) = min(1, p0 * (d_ij(t) / d0)^alpha),  alpha=3.5, p0=0.05, d0=50m
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


class BernoulliChannel:
    def __init__(self, low: float = 0.05, high: float = 0.25,
                 rng: np.random.Generator | None = None):
        self.low, self.high = low, high
        self.rng = rng or np.random.default_rng()
        self._p: dict[int, float] = {}

    def assign(self, node_ids: list[int]) -> None:
        for n in node_ids:
            self._p.setdefault(n, float(self.rng.uniform(self.low, self.high)))

    def step(self, node_ids: list[int]) -> dict[int, float]:
        self.assign(node_ids)
        return {n: self._p[n] for n in node_ids}

    def drop(self, node_id: int) -> None:
        self._p.pop(node_id, None)


class MarkovChannel:
    """2-state Gilbert-Elliott-style channel per node (Section 3.3)."""

    def __init__(self, p_good: float = 0.05, p_bad: float = 0.40,
                 p_gb: float = 0.10, p_bg: float = 0.10,
                 rng: np.random.Generator | None = None):
        self.p_good, self.p_bad = p_good, p_bad
        self.p_gb, self.p_bg = p_gb, p_bg
        self.rng = rng or np.random.default_rng()
        self._state: dict[int, str] = {}  # 'good' | 'bad'

    def assign(self, node_ids: list[int]) -> None:
        for n in node_ids:
            self._state.setdefault(n, 'good' if self.rng.random() < 0.5 else 'bad')

    def step(self, node_ids: list[int]) -> dict[int, float]:
        self.assign(node_ids)
        out = {}
        for n in node_ids:
            state = self._state[n]
            if state == 'good' and self.rng.random() < self.p_gb:
                state = 'bad'
            elif state == 'bad' and self.rng.random() < self.p_bg:
                state = 'good'
            self._state[n] = state
            out[n] = self.p_good if state == 'good' else self.p_bad
        return out

    @classmethod
    def from_burst_duration(cls, burst_duration_packets: float, p_good: float = 0.05,
                             p_bad: float = 0.40, p_gb: float = 0.10,
                             rng: np.random.Generator | None = None) -> "MarkovChannel":
        """
        Mean dwell time in the bad state of a 2-state Markov chain is
        1 / p_bg packets. Figure 3 sweeps "burst duration (packets)" on the
        x-axis; we realize that sweep by setting p_bg = 1 / burst_duration
        (clamped to (0, 1]) so longer bursts correspond to "stickier" bad
        states, holding p_gb fixed.
        """
        burst_duration_packets = max(1.0, float(burst_duration_packets))
        p_bg = min(1.0, 1.0 / burst_duration_packets)
        return cls(p_good=p_good, p_bad=p_bad, p_gb=p_gb, p_bg=p_bg, rng=rng)

    @property
    def steady_state_mean(self) -> float:
        """pi_g = pi_b = 0.5 under symmetric transition rates (Section 4.1)."""
        pi_bad = self.p_gb / (self.p_gb + self.p_bg)
        pi_good = 1 - pi_bad
        return pi_good * self.p_good + pi_bad * self.p_bad

    def drop(self, node_id: int) -> None:
        self._state.pop(node_id, None)


class VelocityFadingChannel:
    """Vehicular Doppler-driven erasure: p_i(t) = p_base + beta*|v_i(t)| (Section 3.3)."""

    def __init__(self, p_base: float = 0.05, beta: float = 0.003,
                 v_low: float = 5.0, v_high: float = 30.0,
                 rng: np.random.Generator | None = None):
        self.p_base, self.beta = p_base, beta
        self.v_low, self.v_high = v_low, v_high
        self.rng = rng or np.random.default_rng()
        self._velocity: dict[int, float] = {}

    def assign(self, node_ids: list[int]) -> None:
        for n in node_ids:
            self._velocity.setdefault(n, float(self.rng.uniform(self.v_low, self.v_high)))

    def step(self, node_ids: list[int]) -> dict[int, float]:
        self.assign(node_ids)
        out = {}
        for n in node_ids:
            # velocity performs a small random walk each step (mobility jitter)
            v = self._velocity[n] + self.rng.normal(0, 0.5)
            v = float(np.clip(v, self.v_low, self.v_high))
            self._velocity[n] = v
            out[n] = float(np.clip(self.p_base + self.beta * abs(v), 0.0, 1.0))
        return out

    def drop(self, node_id: int) -> None:
        self._velocity.pop(node_id, None)


@dataclass
class PathLossModel:
    """p_ij(t) = min(1, p0 * (d_ij(t)/d0)^alpha) (Section 3.1)."""
    p0: float = 0.05
    d0: float = 50.0
    alpha: float = 3.5

    def erasure(self, distance: float) -> float:
        if distance <= 0:
            return 0.0
        return float(min(1.0, self.p0 * (distance / self.d0) ** self.alpha))


CHANNEL_REGISTRY = {
    'bernoulli': BernoulliChannel,
    'markov': MarkovChannel,
    'velocity': VelocityFadingChannel,
}
