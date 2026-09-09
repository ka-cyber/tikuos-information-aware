# Reproducible Information-Utility Scheduling on TikuOS

A reproducible research prototype and evaluation artifact for a
**small, deterministic, application-agnostic utility contract at the TikuOS
worker-scheduling boundary**.

> **Evidence boundary:** checked-in quantitative results are host-model
> results. They are not MCU joule measurements, clinical validation, or proof
> that PIR is correct. The repository contains the implementation and
> measurement protocol required to take the next hardware step.

## Why I explored this on TikuOS

My previous work on physiological information reliability led me to a
systems question: if an application can estimate the downstream value of
different pieces of information, can a resource-constrained operating system
use that signal when deciding which work deserves scarce compute?

TikuOS provides a useful systems substrate for asking this question because
it already exposes constrained worker execution, cycle accounting, budgets,
and low-power mechanisms.

I therefore explored the smallest application-agnostic interface I could
identify between application-level information value and TikuOS scheduling,
without embedding physiology, PIR, ECG/PPG, or application semantics in the
kernel.

This prototype is intentionally a starting point, not a claim that the
abstraction is already correct. The question I want to investigate further is
whether this is the right systems boundary, and whether the idea remains
useful when moved from a host model to real ultra-low-power sensing,
communication, and embedded hardware.
## Research claim under test

**Question:** When runnable embedded tasks differ in expected downstream
decision utility, can a bounded utility contract let TikuOS allocate scarce
CPU opportunities more effectively than conventional scheduling policies,
and under what utility-estimation quality / controller-cost conditions does
that advantage disappear?

The kernel does **not** understand PIR, ECG, PPG, RLNC, physiology, or clinical
labels. Applications provide only:

- normalized expected marginal utility (`Q0.16`)
- optional hard deadline
- estimated CPU cost

The Stage-1 policy ranks eligible workers by integer utility density:

```text
floor(utility_q16 * 2^16 / estimated_cpu_cycles)
```

Deadline eligibility is separate from scoring. The scheduler's authoritative
runnable predicate is applied **before** utility ranking.

## What is implemented

### TikuOS integration

- exact supplied TikuOS snapshot under `upstream/tikuOS/`
- one reproducible patch under `patches/`
- opt-in `TIKU_UTILITY_ENABLE=1`
- bounded static storage
- fixed-point arithmetic; no floating point
- dynamic per-workload hints
- hard modular deadlines
- scheduler-level filtering of non-runnable / budget-exhausted workers
- hint reset on thread restart
- deterministic round-robin tie breaking
- exact legacy fallback when the feature is disabled or no eligible hint exists

### Scientific evaluation

Policies:

- RR
- SPT / cost-only
- EDF
- LLF
- quality-only
- task/deadline
- maximum predicted utility
- utility density
- offline clairvoyant DP reference

Workload regimes explicitly include favorable, neutral, shifted, noisy,
temporally stale, rank-corrupted, adversarial, deadline-stressed, and
controller-cost-dominant conditions.

The experiment separates:

```text
realized utility  !=  scheduling hint
```

so the proposed policy is not rewarded by simply reusing its own score as the
outcome.

### Application grounding

- CardioFusion is exposed through an adapter that produces workload-side
  signal-quality / event evidence.
- APC-RLNC is exposed through an adapter for communication-side reliability
  workload generation.
- Neither application is linked into the TikuOS kernel.

These adapters are **application-grounding mechanisms**, not evidence of a
full hardware CardioFusion -> TikuOS -> APC-RLNC deployment.

## Primary endpoint

For Stage 1:

```text
delivered downstream utility
---------------------------------
CPU cycles + policy decision cycles
```

This is deliberately called **cycle-normalized delivered utility**, not
energy efficiency.

For hardware:

```text
joules = integral(V(t) * I(t) dt)
```

must be measured, including sensing, CPU, memory, radio, accelerator and sleep
states where applicable. Cycle counts are retained as a separate explanatory
variable.

## Statistical protocol

The primary comparison is paired within workload seed:

```text
Î” = utility_density - RR
```

The repository reports:

- paired bootstrap 95% CI
- paired sign-flip permutation test
- Wilcoxon signed-rank sensitivity test
- Cohen's `d_z`
- Holm adjustment for regime-level exploratory p-values

The primary endpoint and policies are fixed in `configs/stage1.json`. Seeds
are workload realizations, not independent observations within a workload.

## Failure-boundary experiments

`experiments/sensitivity.py` varies:

- additive hint noise
- rank-flip corruption
- explicit hint delay
- controller cost

The scientific target is not "always win." It is the boundary:

```text
utility-estimation quality × controller overhead
                    |
                    v
          positive / neutral / harmful
```

A deliberately adversarial workload is retained even when the proposed policy
loses.

## Reproduction

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"

pytest -q
bash tests/c_host/run_host_test.sh
bash scripts/verify_patch.sh

python -m experiments.run_experiment --seeds 24 --budget 2400
python -m experiments.analyze_results results/stage1.json
python -m experiments.sensitivity --seeds 24
```

The last three commands regenerate the checked-in host-model analyses.

## Exact TikuOS patch

The patch is generated against the exact source snapshot checked into
`upstream/tikuOS/`.

```bash
cd /path/to/tikuOS-information-aware
rm -rf /tmp/tikuos-clean
cp -a upstream/tikuOS /tmp/tikuos-clean
cd /tmp/tikuos-clean
patch --dry-run -p1   -i /path/to/tikuOS-information-aware/patches/0001-information-utility-scheduler.patch
```

`bash scripts/verify_patch.sh` performs this check automatically.

For a future hardware release, record the upstream Git commit in the campaign
manifest in addition to the supplied-archive SHA-256.

## Repository map

```text
upstream/tikuOS/       exact supplied TikuOS snapshot
patches/               minimal OS modification
src/tikuos_iu/         canonical Python contract + C ABI bridge
experiments/            host execution model and statistics
vendor/cardiofusion/   supplied CardioFusion research asset
vendor/pir/            supplied PIR research asset
vendor/apc-rlnc/       supplied APC-RLNC research asset
tests/                  Python, C, lifecycle, deadline, and parity tests
hardware/               board measurement protocol
docs/                   architecture, methodology, limits, reproducibility
results/                checked-in reproducible host analyses
configs/                pre-specified experiment configuration
scripts/                verification/release helpers
```

## Scientific limits

This repository does not claim:

1. that utility-density scheduling is a novel scheduling algorithm;
2. that PIR is an established theory;
3. that a normalized utility score is a clinically validated utility function;
4. that cycle savings imply joule savings;
5. that CardioFusion/APC-RLNC are fully integrated into TikuOS hardware;
6. that host-model results establish superiority on a board.

The systems question explored here is narrower: a **tiny, bounded, generic OS
contract for application-provided expected marginal utility**, with explicit
correctness semantics and a measurable failure boundary.

## Next empirical gate

Before any energy-efficiency claim, run the same three-worker workload on a
supported TikuOS MCU and record:

- firmware commit and patch hash
- compiler/version/flags
- CPU frequency
- scheduler decisions and context switches
- CPU cycles and wall time
- supply voltage/current waveform
- integrated joules
- sleep/radio/sensing/accelerator activity
- deadline misses
- raw measurement hash

Only after that gate should the Stage-1 cycle result be compared with measured
joule-normalized utility.

## License and provenance

The project is Apache-2.0 unless a vendored component carries its own license.
See `vendor/` notices and `RELEASE_MANIFEST.json`.

The four supplied input archives are recorded by SHA-256 in the release
manifest.
