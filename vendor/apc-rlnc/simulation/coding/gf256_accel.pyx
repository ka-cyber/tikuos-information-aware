# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython-accelerated GF(256) arithmetic.

Drop-in accelerated versions of the hot-path operations in gf256.py
(elementwise vector multiply-by-scalar and add), used by RLNCEncoder /
RLNCDecoder's inner loops. Build with:

    python setup.py build_ext --inplace

After building, coding/rlnc.py and coding/hierarchical.py will
transparently prefer these if `coding.gf256_accel` is importable; if the
extension hasn't been compiled, everything falls back to the pure-Python
gf256.py path with identical results (just slower).
"""
import numpy as np
cimport numpy as cnp
from libc.stdint cimport uint8_t, uint16_t

cnp.import_array()

cdef uint16_t[512] EXP_TABLE
cdef uint16_t[256] LOG_TABLE
cdef int PRIMITIVE_POLY = 0x11D  # matches gf256.py -- generator 2 has order 255

cdef void _build_tables():
    cdef int i, x
    x = 1
    for i in range(255):
        EXP_TABLE[i] = x
        LOG_TABLE[x] = i
        x <<= 1
        if x & 0x100:
            x ^= PRIMITIVE_POLY
    for i in range(255, 512):
        EXP_TABLE[i] = EXP_TABLE[i - 255]
    LOG_TABLE[0] = 0

_build_tables()


def gf_mul_scalar(unsigned int scalar, cnp.ndarray[uint8_t, ndim=1] vec):
    """Multiply a byte-vector by a single GF(256) scalar, in-place-fast."""
    cdef Py_ssize_t n = vec.shape[0]
    cdef cnp.ndarray[uint8_t, ndim=1] out = np.zeros(n, dtype=np.uint8)
    cdef int ls, i, v, idx
    scalar &= 0xFF
    if scalar == 0:
        return out
    if scalar == 1:
        return vec.copy()
    ls = LOG_TABLE[scalar]
    for i in range(n):
        v = vec[i]
        if v != 0:
            idx = LOG_TABLE[v] + ls
            if idx >= 255:
                idx -= 255
            out[i] = EXP_TABLE[idx]
    return out


def gf_add(cnp.ndarray[uint8_t, ndim=1] a, cnp.ndarray[uint8_t, ndim=1] b):
    """XOR (GF(256) addition)."""
    return np.bitwise_xor(a, b)


def gf_inv(unsigned int a):
    a &= 0xFF
    if a == 0:
        raise ZeroDivisionError("GF(256) inverse of 0 is undefined")
    return EXP_TABLE[255 - LOG_TABLE[a]]
