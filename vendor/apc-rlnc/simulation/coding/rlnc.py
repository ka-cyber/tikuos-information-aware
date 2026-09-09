"""
Random Linear Network Coding (RLNC) over GF(256).

Implements the generation model from Section 3.2 of the paper:

    A generation consists of K original packets {p_1, ..., p_K} over F_256.
    An encoder transmits K + R coded packets:
        c_j = sum_k alpha_{j,k} p_k,   alpha_{j,k} ~ Uniform(F_256).
    Decoding succeeds once the receiver collects >= K linearly independent
    coded packets (Eq. 1 gives the closed-form success probability).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from .gf256 import gf_mul_scalar, gf_inv, gf_add


@dataclass
class CodedPacket:
    coefficients: np.ndarray  # shape (K,), GF(256) coding vector
    payload: np.ndarray       # shape (payload_len,), GF(256) coded symbols


class RLNCEncoder:
    """Encodes a generation of K source packets into K+R coded packets."""

    def __init__(self, packets: np.ndarray, rng: np.random.Generator | None = None):
        """
        packets: array of shape (K, payload_len), dtype uint8.
        """
        self.packets = np.asarray(packets, dtype=np.uint8)
        self.K, self.payload_len = self.packets.shape
        self.rng = rng or np.random.default_rng()

    def generate(self, n_coded: int) -> list[CodedPacket]:
        """Produce n_coded random linear combinations (K+R coded packets)."""
        out = []
        for _ in range(n_coded):
            coeffs = self.rng.integers(1, 256, size=self.K, dtype=np.uint16).astype(np.uint8)
            payload = np.zeros(self.payload_len, dtype=np.uint8)
            for k in range(self.K):
                if coeffs[k] != 0:
                    payload = gf_add(payload, gf_mul_scalar(int(coeffs[k]), self.packets[k]))
            out.append(CodedPacket(coefficients=coeffs, payload=payload))
        return out


class RLNCDecoder:
    """
    Incrementally ingests coded packets and performs online Gaussian
    elimination over GF(256). is_decoded() becomes True once rank == K.
    """

    def __init__(self, K: int, payload_len: int):
        self.K = K
        self.payload_len = payload_len
        self._coeff_rows: list[np.ndarray] = []   # reduced coefficient rows
        self._payload_rows: list[np.ndarray] = []  # matching reduced payloads
        self._pivots: dict[int, int] = {}          # pivot column -> row index

    def rank(self) -> int:
        return len(self._coeff_rows)

    def is_decoded(self) -> bool:
        return self.rank() >= self.K

    def add_packet(self, packet: CodedPacket) -> bool:
        """
        Reduce an incoming coded packet against the current basis.
        Returns True if it increased the rank (i.e. was innovative).
        """
        coeffs = packet.coefficients.copy().astype(np.uint8)
        payload = packet.payload.copy().astype(np.uint8)

        for pivot_col, row_idx in sorted(self._pivots.items()):
            if coeffs[pivot_col] != 0:
                factor = int(coeffs[pivot_col])
                coeffs = gf_add(coeffs, gf_mul_scalar(factor, self._coeff_rows[row_idx]))
                payload = gf_add(payload, gf_mul_scalar(factor, self._payload_rows[row_idx]))

        nz = np.nonzero(coeffs)[0]
        if nz.size == 0:
            return False  # not innovative (linearly dependent / erased)

        pivot_col = int(nz[0])
        inv = gf_inv(int(coeffs[pivot_col]))
        coeffs = gf_mul_scalar(inv, coeffs)
        payload = gf_mul_scalar(inv, payload)

        row_idx = len(self._coeff_rows)
        self._coeff_rows.append(coeffs)
        self._payload_rows.append(payload)
        self._pivots[pivot_col] = row_idx
        return True

    def recover(self) -> np.ndarray | None:
        """
        Back-substitute to recover the original K packets, or None if not
        yet full rank.
        """
        if not self.is_decoded():
            return None
        # Full Gauss-Jordan back-substitution over the K pivot rows.
        order = [self._pivots[c] for c in range(self.K)]
        coeff_mat = np.stack([self._coeff_rows[i] for i in order])
        payload_mat = np.stack([self._payload_rows[i] for i in order])

        for i in range(self.K - 1, -1, -1):
            for j in range(i):
                factor = int(coeff_mat[j, i])
                if factor != 0:
                    coeff_mat[j] = gf_add(coeff_mat[j], gf_mul_scalar(factor, coeff_mat[i]))
                    payload_mat[j] = gf_add(payload_mat[j], gf_mul_scalar(factor, payload_mat[i]))
        return payload_mat


def decode_probability(p_erasure: float, K: int, R: int) -> float:
    """
    Closed-form Eq. (1):
        P_decode(p_i; K, R) = sum_{k=K}^{K+R} C(K+R, k) (1-p_i)^k p_i^{K+R-k}
    i.e. the probability of receiving at least K of the K+R transmitted
    coded packets (each independently erased w.p. p_i), which for
    random GF(256) coefficients with K+R >> log2(256) is an excellent
    approximation to the true innovative-packet probability.
    """
    from math import comb
    n = K + R
    return float(sum(
        comb(n, k) * (1 - p_erasure) ** k * p_erasure ** (n - k)
        for k in range(K, n + 1)
    ))
