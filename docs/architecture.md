# Architecture

## Design principle

TikuOS does not learn application semantics. The kernel receives a bounded
contract representing **expected marginal downstream utility**.

```text
PIR / CardioFusion / APC-RLNC / other application logic
                    |
                    | expected marginal utility
                    | deadline + estimated CPU cost
                    v
        +---------------------------+
        | TikuOS utility contract   |
        | Q0.16 / static / bounded  |
        +---------------------------+
                    |
                    v
        existing worker scheduler
                    |
                    v
        CPU worker + existing budget
```

The kernel contains no ECG, PPG, PIR, RLNC, cardiovascular, or clinical
structures.

## Stage-1 scope

Stage 1 intentionally changes only CPU worker selection. It is not yet a
general radio/NPU/sensing/memory broker.

The long-term resource-broker question is separate:

```text
Stage 1  worker selection
Stage 2  compute allocation
Stage 3  sensing allocation
Stage 4  communication allocation
Stage 5  cross-resource allocation
```

No Stage-2+ mechanism is claimed by this repository.

## Canonical contract

A hint contains:

- `utility_q16`: normalized expected marginal utility, Q0.16
- `deadline_tick`: optional absolute deadline
- `cost_cycles`: estimated CPU cost, strictly positive
- `flags`
- `valid`

The kernel score is:

`floor(utility_q16 * 2^16 / cost_cycles)`

Deadline eligibility is evaluated separately with modular 32-bit time. The
validity assumption is a deadline distance less than `2^31` ticks.

## Candidate correctness

The scheduler's existing `worker_runnable()` predicate remains authoritative.
Before utility ranking, the scheduler constructs a candidate view containing
only runnable workers. Therefore DONE, UNUSED, and budget-exhausted workers
cannot win the utility ranking.

If no eligible utility hint exists, the scheduler falls back to the exact
legacy round-robin path.

## Lifecycle correctness

Hints are workload-instance state. `tiku_thread_start()` clears an old hint,
including when a DONE TCB is restarted. A new workload therefore cannot inherit
stale utility information.

## Determinism and resource bounds

- static hint storage sized to `TIKU_THREADS_MAX`
- O(T) bounded lookup/selection
- integer arithmetic
- no dynamic allocation
- no floating point
- deterministic cursor-based tie breaking
- compile-time opt-in
- backward-compatible fallback

The interface is deliberately small because the scientific question concerns
whether exposing *any* bounded utility signal is worthwhile, not whether the
kernel should become an application-specific optimizer.
