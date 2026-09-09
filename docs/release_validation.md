# Release Validation Report

Generated from the checked-in source tree on 2026-09-09.

## Automated gates

| Gate | Result |
|---|---|
| Python test suite | PASS — 13 passed |
| C/Python score parity | PASS |
| TikuOS patch dry-run | PASS |
| Patched TikuOS host scheduler | PASS |
| Release consistency scan | PASS |

The release script is `scripts/verify_release.sh`.

## Primary experiment

Configuration:

- 24 paired seeds
- 15 workload regimes
- 10 policies including EDF, LLF and offline DP
- 2400-cycle matched budget
- 35-cycle proposed-controller overhead per decision

Primary contrast:

`utility_density - rr`

The current host-model results show positive effects in several informative
regimes, a negative effect in the deliberately adversarial regime, and a
strong negative effect when controller overhead dominates worker cost.

Selected paired mean differences (cycle-normalized delivered utility):

| Regime | Mean Δ | 95% CI |
|---|---:|---:|
| homogeneous | 0.000378 | [0.000274, 0.000478] |
| independent | 0.001135 | [0.000943, 0.001319] |
| tight_deadlines | 0.000203 | [0.000116, 0.000283] |
| delayed_hint | 0.000232 | [0.000034, 0.000429] |
| adversarial | -0.000383 | [-0.000578, -0.000194] |
| controller_cost_dominant | -0.056603 | [-0.058236, -0.054875] |

These are **model outputs**, not measured energy results.

The rank-flip sensitivity approaches a zero-effect boundary, and the
controller-cost sweep also reaches a confidence interval crossing zero. These
failure boundaries are part of the scientific result.

## Hardware gate

No board-level energy claim is made. A hardware release must collect raw
current/voltage traces and report integrated joules, wall time, scheduler
overhead, and activity-specific energy. The cycle-level result is not allowed
to be relabeled as joule efficiency without this measurement.

## Provenance

`RELEASE_MANIFEST.json` records SHA-256 hashes of all four supplied input
archives. The TikuOS patch is generated against the exact supplied snapshot
under `upstream/tikuOS/`.
