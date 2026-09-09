# Research Question and Falsifiable Hypothesis

## Research question

When runnable embedded work has different expected downstream decision value,
can a tiny application-agnostic utility contract at the TikuOS worker boundary
improve useful information delivered under a matched resource budget, and what
conditions make the adaptation cease to be worthwhile?

## H0 — no information-value advantage

At matched workload realization, deadline constraints, and total resource
budget, utility-density scheduling has no positive improvement in
cycle-normalized delivered utility over the legacy round-robin policy.

## H1 — conditional advantage

When application-provided expected marginal utility has predictive information
about realized downstream utility, utility-density scheduling has a positive
paired effect over round-robin. The effect should shrink to zero or become
negative as:

1. utility estimates lose rank information;
2. hints become temporally stale;
3. deployment distribution shifts;
4. adversarial correlation is introduced; or
5. controller overhead dominates the cost of the work being selected.

This is deliberately a **conditional** hypothesis, not a claim that
information-aware scheduling always wins.

## Variables

### Independent

- scheduler policy
- workload regime
- utility-estimation noise
- rank corruption
- hint delay
- controller cycles per decision
- matched CPU budget

### Dependent

Primary:
- delivered utility / total charged CPU cycles

Secondary:
- delivered utility
- deadline success rate
- completed work
- worker CPU cycles
- policy decision cycles
- missed deadlines

Hardware secondary:
- joules
- wall time
- current/voltage waveform
- sleep/radio/sensing/accelerator energy

### Controls

- identical workload realization per paired seed
- identical deadlines/costs
- identical budget
- deterministic tie-breaking
- no tuning on held-out seeds

## Statistical unit

A complete workload realization (seed). Repeated task rows inside one seed
are not treated as independent statistical observations.

## Falsification criteria

The mechanism is not supported if the primary paired CI includes zero on the
pre-specified representative workload family, or if any observed gain is
explained by a simpler standard scheduling policy, disappears when utility is
made independent of realized outcomes, or is erased by the controller's own
measured resource cost.

A failure boundary is itself a result.
