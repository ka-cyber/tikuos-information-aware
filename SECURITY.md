# Security

The Stage-1 mechanism is an optional embedded scheduler extension. It is not a
security boundary and does not authenticate application-provided utility
hints. Callers must treat utility values and deadlines as trusted scheduling
inputs.

Report reproducible memory-safety, integer-overflow, scheduler-lifecycle, or
concurrency defects through the repository's issue tracker once a public
repository is established. Do not disclose sensitive device credentials or
measurement infrastructure secrets in experiment artifacts.
