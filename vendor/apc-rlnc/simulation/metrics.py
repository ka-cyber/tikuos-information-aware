"""
Metrics matching Section 7.1's four evaluation columns:

* PDR: fraction of generations decoded successfully.
* Latency: (proxy, ms) time from first packet transmission to decoding
  completion -- approximated here as coded-packets-until-decode * a fixed
  per-packet transmission time, since we don't model a physical radio.
* Overhead: redundancy ratio R / (K + R).
* Retention: fraction of nodes remaining in their assigned cluster across
  consecutive reconfiguration epochs.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

MS_PER_PACKET = 1.0  # calibration constant: simulated per-packet airtime (ms)


@dataclass
class RunMetrics:
    decoded_flags: list[bool] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)
    overheads: list[float] = field(default_factory=list)
    retentions: list[float] = field(default_factory=list)
    energy_joules: list[float] = field(default_factory=list)

    def record_generation(self, decoded: bool, packets_until_decode: int,
                           redundancy_ratio: float) -> None:
        self.decoded_flags.append(decoded)
        self.latencies_ms.append(packets_until_decode * MS_PER_PACKET)
        self.overheads.append(redundancy_ratio)

    def record_retention(self, fraction_retained: float) -> None:
        self.retentions.append(fraction_retained)

    def record_energy(self, joules_per_generation: float) -> None:
        self.energy_joules.append(joules_per_generation)

    def summary(self) -> dict:
        def m(x):
            return float(np.mean(x)) if x else float('nan')

        def s(x):
            return float(np.std(x)) if x else float('nan')

        return {
            'pdr_pct': m(self.decoded_flags) * 100,
            'pdr_std_pct': s(self.decoded_flags) * 100,
            'latency_ms': m(self.latencies_ms),
            'latency_std_ms': s(self.latencies_ms),
            'overhead_pct': m(self.overheads) * 100,
            'overhead_std_pct': s(self.overheads) * 100,
            'retention_pct': m(self.retentions) * 100 if self.retentions else float('nan'),
            'retention_std_pct': s(self.retentions) * 100 if self.retentions else float('nan'),
            'energy_j': m(self.energy_joules) if self.energy_joules else float('nan'),
        }


def aggregate_runs(run_summaries: list[dict]) -> dict:
    """Mean +/- std across independent runs, matching Table 1/2 formatting."""
    keys = run_summaries[0].keys() if run_summaries else []
    out = {}
    for k in keys:
        vals = [r[k] for r in run_summaries if not np.isnan(r[k])]
        out[k] = {'mean': float(np.mean(vals)) if vals else float('nan'),
                   'std': float(np.std(vals)) if vals else float('nan')}
    return out
