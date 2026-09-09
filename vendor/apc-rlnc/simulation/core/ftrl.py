"""
Online Optimization Regret (Section 4.2, Theorem 2).

x_t in Delta^C is the clustering assignment at epoch t (Delta^C = the
C-simplex). The loss l_t(x_t) measures clustering quality from Eq. (3).
Cumulative regret:
    Regret(T) = sum_t l_t(x_t) - min_{x* in Delta^C} sum_t l_t(x*)

Theorem 2 (Online Clustering Regret): under convex loss relaxation and
Lipschitz constant G, FTRL with squared-Euclidean regularization
psi(x) = 0.5*||x||^2 and learning rate eta_t = 1/sqrt(t) achieves:
    Regret(T) <= G^2 * sqrt(2T)

This module runs the actual FTRL iterate updates over a simplex (not just
the closed-form bound), so Regret(T) can be measured empirically per epoch
and compared against the theoretical curve.
"""
from __future__ import annotations
import numpy as np


def theoretical_regret_bound(T: int, G: float) -> float:
    """G^2 * sqrt(2T), per Theorem 2."""
    return (G ** 2) * np.sqrt(2 * T)


def project_to_simplex(v: np.ndarray) -> np.ndarray:
    """Euclidean projection of vector v onto the probability simplex."""
    v = np.asarray(v, dtype=np.float64)
    n = v.shape[0]
    u = np.sort(v)[::-1]
    css = np.cumsum(u) - 1
    idx = np.arange(1, n + 1)
    cond = u - css / idx > 0
    rho = idx[cond][-1]
    theta = css[cond][-1] / rho
    return np.maximum(v - theta, 0.0)


class FTRLOptimizer:
    """
    Follow-the-Regularized-Leader over the C-simplex with squared-Euclidean
    regularization psi(x) = 0.5*||x||_2^2 and eta_t = 1/sqrt(t), matching
    the Proof of Theorem 2 (standard FTRL analysis, Hazan 2016).
    """

    def __init__(self, C: int, lipschitz_G: float = 1.0):
        self.C = C
        self.G = lipschitz_G
        self.t = 0
        self._grad_sum = np.zeros(C, dtype=np.float64)
        self.x = np.full(C, 1.0 / C)
        self.losses: list[float] = []
        self.regret_trace: list[float] = []
        self._best_hindsight_grad_sum = np.zeros(C, dtype=np.float64)

    def step(self, loss_grad: np.ndarray, realized_loss: float) -> np.ndarray:
        """
        loss_grad: subgradient of l_t at the played point x_t (shape (C,)).
        realized_loss: scalar l_t(x_t), used only for regret bookkeeping.
        Returns the next iterate x_{t+1}.
        """
        self.t += 1
        eta_t = 1.0 / np.sqrt(self.t)
        self._grad_sum += loss_grad
        # FTRL update: x_{t+1} = argmin_x <grad_sum, x> + (1/eta_t)*psi(x)
        candidate = -eta_t * self._grad_sum
        self.x = project_to_simplex(candidate)
        self.losses.append(realized_loss)
        return self.x

    def regret(self, best_fixed_loss_sum: float) -> float:
        """Regret(T) = sum_t l_t(x_t) - min_{x*} sum_t l_t(x*)."""
        return float(sum(self.losses) - best_fixed_loss_sum)

    def bound(self) -> float:
        return theoretical_regret_bound(self.t, self.G)
