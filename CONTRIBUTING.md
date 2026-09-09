# Contributing

This repository is a research artifact. Changes must preserve the distinction
between the generic TikuOS mechanism and application-specific utility
estimators.

Before opening a change:

```bash
python -m pytest -q
bash tests/c_host/run_host_test.sh
bash scripts/verify_patch.sh
```

Experimental changes must state whether they alter the pre-specified primary
endpoint, workload generator, policy set, or statistical protocol. Do not
delete negative regimes or tune on held-out seeds.

Kernel changes must remain bounded, deterministic, allocation-free, and
backward compatible unless a documented experiment explicitly studies a
different design.
