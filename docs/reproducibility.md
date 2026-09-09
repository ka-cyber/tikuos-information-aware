# Reproducibility

## Clean-room verification

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

The repository is installable; experiment modules are invoked with
`python -m`, avoiding an implicit `PYTHONPATH`.

## Upstream snapshot

`upstream/tikuOS/` is the exact supplied source snapshot. The patch is generated
against that clean tree and verified with `patch --dry-run -p1` before the host
scheduler test.

The release manifest records the SHA-256 of each supplied archive. A hardware
campaign must additionally record the upstream Git commit, board revision,
toolchain, optimization flags, and firmware image hash.

## Determinism

Seeds identify complete workload realizations. Policy comparisons reuse the
same realization. The C score is integer-only and Python/C parity is tested.

## Results provenance

Checked-in results are generated artifacts, not hand-edited headline numbers.
Regenerating the experiment overwrites them from source and configuration.

## Hardware measurement

The hardware protocol requires raw voltage/current traces and their hashes.
No cycle-to-joule conversion is permitted without calibration on the target
platform.
