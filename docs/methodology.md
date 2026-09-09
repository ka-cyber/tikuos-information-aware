# Experimental Methodology

## 1. Unit of experimentation

One seed generates one complete workload realization. Every policy receives the
same realization, deadlines, costs, true utility, and initial cursor. Policy
comparisons are therefore paired within seed.

The host model has all tasks released at tick zero. A dispatched task consumes
its modeled CPU cost atomically; if it would exceed the matched budget or
deadline, it contributes no delivered utility.

## 2. Policies

The pre-specified policy set is:

| Policy | Decision rule |
|---|---|
| RR | legacy round-robin |
| SPT | smallest processing time |
| EDF | earliest absolute deadline |
| LLF | least laxity (`deadline - now - cost`) |
| Quality | highest workload quality |
| Task | deadline/urgency heuristic |
| Max utility | highest predicted utility |
| Utility density | canonical Q0.16 utility / estimated CPU cost |
| Clairvoyant DP | offline reference using realized utility |

EDF and LLF are included because hard deadlines make canonical real-time
scheduling baselines mandatory. They are not strawman replacements for the
legacy scheduler.

Each online policy has an explicit decision-overhead cost in the matched
budget. The proposed utility controller uses the configured
`controller_cycles_per_decision`; simpler baselines use smaller fixed costs.
The offline DP has zero online decision cost by definition and is reported as
an upper/reference bound for the host model, never as a TikuOS oracle.

## 3. Workload regimes

The experiment deliberately spans:

- homogeneous utility
- independent utility/quality
- high uncertainty
- tight deadlines
- misleading quality
- utility/cost anti-correlation
- non-stationarity
- adversarial ranking
- high compute cost
- controller-cost-dominant work
- noisy hints
- temporally delayed hints
- affine miscalibration
- rank corruption
- distribution shift

The adversarial regime intentionally makes the supplied hint uninformative
and cost-biased so utility-density can lose to RR. The result is retained.

## 4. Information-estimate error taxonomy

The repository distinguishes:

- **calibration error:** monotone bias/scale without necessarily changing rank
- **rank error:** predicted ordering differs from realized utility ordering
- **temporal error:** hint describes an earlier state
- **distribution shift:** deployment relationship differs from calibration
- **adversarial error:** high predicted value is systematically associated with
  low realized utility

`delayed_hint` is an actual temporal shift: the hint at time/index `t` is
derived from a configurable earlier realization rather than merely adding
noise.

## 5. Primary endpoint

The primary Stage-1 endpoint is:

`delivered_downstream_utility / (CPU_cycles + policy_decision_cycles)`

This is a modeled cycle-normalized resource metric. It is not joules.

The hardware endpoint will replace the denominator with measured integrated
energy while retaining CPU cycles and wall time as explanatory metrics.

## 6. Statistical analysis

Primary paired contrast:

`Δ = utility_density - RR`

For each regime the artifact reports mean paired difference, paired bootstrap
95% CI, sign-flip permutation p-value, Wilcoxon signed-rank sensitivity, and
Cohen's `d_z`.

Regime-level p-values are exploratory and Holm-adjusted. No regime-level
result is allowed to replace the pre-specified primary endpoint.

## 7. Reproducibility controls

- same seed across policies
- no test-set tuning
- deterministic integer kernel score
- explicit tie-breaking
- explicit controller overhead
- exact TikuOS patch verification
- Python/C score parity test
- C host scheduler execution test
- checked-in generated results
- input archive hashes

## 8. What would falsify the mechanism

Evidence against the hypothesis includes:

- no positive effect on representative workloads;
- effect disappearing under independent/permuted utility;
- EDF/LLF or a simpler policy matching the proposed method;
- utility estimates becoming unreliable enough that the proposed policy is
  harmful;
- controller overhead consuming the resource advantage;
- hardware joule measurements failing to reproduce the cycle-level advantage.

Negative regimes are therefore first-class outputs, not errors to suppress.
