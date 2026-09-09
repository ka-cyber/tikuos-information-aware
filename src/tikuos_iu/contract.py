"""Canonical Stage-1 information-utility contract.

This module is the executable specification for the C implementation under
``upstream/tikuOS/kernel/utility``.  The kernel contract intentionally accepts
*expected marginal downstream utility*, not application semantics.  PIR,
CardioFusion and APC-RLNC adapters compute that quantity outside the kernel.

Score = utility_q16 / estimated_cpu_cycles, preserving ordering exactly.
Deadlines are hard eligibility constraints.  There is no hidden uncertainty
multiplier: uncertainty only enters when an application derives expected
marginal utility.  This avoids double-counting and makes the hypothesis
falsifiable.
"""
from dataclasses import dataclass
from typing import Optional

Q16_MAX = 65535
DEADLINE_FLAG = 0x01

@dataclass(frozen=True)
class UtilityHint:
    utility_q16: int
    deadline_tick: int = 0
    cost_cycles: int = 1
    flags: int = 0
    def __post_init__(self):
        if not 0 <= self.utility_q16 <= Q16_MAX: raise ValueError("utility_q16 out of range")
        if self.cost_cycles <= 0: raise ValueError("cost_cycles must be > 0")
        if not 0 <= self.deadline_tick <= 0xffffffff: raise ValueError("deadline_tick out of range")
        if not 0 <= self.flags <= 255: raise ValueError("flags out of range")

def score(h: UtilityHint) -> int:
    return min(0xffffffff, (h.utility_q16 << 16) // h.cost_cycles)

def deadline_eligible(h: UtilityHint, now: int) -> bool:
    if not (h.flags & DEADLINE_FLAG): return True
    delta = (h.deadline_tick - now) & 0xffffffff
    return delta < 0x80000000

def select(hints: list[Optional[UtilityHint]], cursor: int, now: int) -> Optional[int]:
    best = None; best_score = -1
    n = len(hints)
    if n == 0: return None
    for off in range(n):
        i=(cursor+off)%n
        h=hints[i]
        if h is None or not deadline_eligible(h,now): continue
        s=score(h)
        if best is None or s > best_score:
            best=i; best_score=s
    return best
