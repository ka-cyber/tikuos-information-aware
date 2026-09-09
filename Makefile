# Research artifact command surface
.PHONY: test verify patch experiment sensitivity release clean

test:
	python -m pytest -q

verify:
	bash scripts/verify_release.sh

patch:
	bash scripts/verify_patch.sh

experiment:
	python -m experiments.run_experiment --seeds 24 --budget 2400

sensitivity:
	python -m experiments.sensitivity --seeds 24

release:
	bash scripts/verify_release.sh

clean:
	rm -rf build .pytest_cache
