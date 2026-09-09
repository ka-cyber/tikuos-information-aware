"""
GF(256) finite field arithmetic for RLNC coding.

Implements F_256 = GF(2^8) using the primitive polynomial
x^8 + x^4 + x^3 + x^2 + 1 (0x11D) with generator g=2, via log/antilog
(Zech logarithm) tables for O(1) multiplication and division after an
O(256) setup cost. This is the same construction used by Reed-Solomon /
RLNC libraries such as kodo and gf-complete: 2 is a primitive element
under 0x11D (unlike AES's 0x11B modulus, under which 2 only has order 51),
so it generates the full order-255 multiplicative cycle needed for the
log/antilog tables.

This is the pure-Python/NumPy reference implementation referenced by the
README as `simulation/coding/`. A Cython-accelerated drop-in
(`gf256_accel.pyx`) is provided alongside it for the claimed 5x speedup;
this module is always correct on its own and does not require compilation.
"""
from __future__ import annotations
import numpy as np

PRIMITIVE_POLY = 0x11D  # x^8 + x^4 + x^3 + x^2 + 1, generator 2 has order 255

# --------------------------------------------------------------------------
# Build log / antilog tables once at import time.
# --------------------------------------------------------------------------
_EXP = np.zeros(512, dtype=np.uint16)   # antilog table, extended to avoid mod
_LOG = np.zeros(256, dtype=np.uint16)   # log table

def _build_tables() -> None:
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= PRIMITIVE_POLY
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]
    _LOG[0] = 0  # log(0) undefined; guarded explicitly in gf_div/gf_inv

_build_tables()


def gf_add(a, b):
    """Addition (and subtraction) in GF(2^8) is XOR."""
    return np.bitwise_xor(a, b)


def gf_mul(a, b):
    """Elementwise multiplication in GF(256). Accepts scalars or ndarrays."""
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    out = np.zeros(np.broadcast(a, b).shape, dtype=np.uint8)
    nz = (a != 0) & (b != 0)
    la = _LOG[a[nz]] if a.shape else _LOG[int(a)]
    lb = _LOG[b[nz]] if b.shape else _LOG[int(b)]
    if out.shape == ():
        if a != 0 and b != 0:
            out = np.uint8(_EXP[(int(_LOG[int(a)]) + int(_LOG[int(b)])) % 255])
        else:
            out = np.uint8(0)
        return out
    idx = (la.astype(np.int64) + lb.astype(np.int64)) % 255
    out[nz] = _EXP[idx].astype(np.uint8)
    return out


def _gf_mul_scalar_py(scalar: int, vec: np.ndarray) -> np.ndarray:
    """Pure-Python/NumPy fallback (always correct, no build step required)."""
    scalar = int(scalar) & 0xFF
    if scalar == 0:
        return np.zeros_like(vec)
    if scalar == 1:
        return vec.copy()
    ls = int(_LOG[scalar])
    vec = np.asarray(vec, dtype=np.uint8)
    out = np.zeros_like(vec)
    nz = vec != 0
    lv = _LOG[vec[nz].astype(np.int64)]
    idx = (lv.astype(np.int64) + ls) % 255
    out[nz] = _EXP[idx].astype(np.uint8)
    return out


try:
    # If `python setup.py build_ext --inplace` has been run, prefer the
    # compiled Cython path (README's claimed 5x speedup) for the hot loop.
    from .gf256_accel import gf_mul_scalar as _gf_mul_scalar_cy

    def gf_mul_scalar(scalar: int, vec: np.ndarray) -> np.ndarray:
        return _gf_mul_scalar_cy(int(scalar) & 0xFF, np.ascontiguousarray(vec, dtype=np.uint8))

except ImportError:
    gf_mul_scalar = _gf_mul_scalar_py


def gf_inv(a: int) -> int:
    a = int(a) & 0xFF
    if a == 0:
        raise ZeroDivisionError("GF(256) inverse of 0 is undefined")
    return int(_EXP[(255 - int(_LOG[a])) % 255])


def gf_div(a: int, b: int) -> int:
    a = int(a) & 0xFF
    b = int(b) & 0xFF
    if b == 0:
        raise ZeroDivisionError("division by zero in GF(256)")
    if a == 0:
        return 0
    return int(_EXP[(int(_LOG[a]) - int(_LOG[b])) % 255])


def random_nonzero_matrix(rows: int, cols: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform random coding coefficients in GF(256), alpha_{j,k} ~ Uniform(F_256)."""
    return rng.integers(0, 256, size=(rows, cols), dtype=np.uint16).astype(np.uint8)
