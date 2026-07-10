# Validation

This repository is expected to stay runnable with the standard Python toolchain:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
python scripts/benchmark_sssp.py --nodes 50 --edges 150 --seed 7 --output .benchmarks/smoke.json
```

The benchmark command writes JSON and CSV outputs with deterministic graph generation
under the provided seed. Files under `.benchmarks/` are local run artifacts and are
not part of the source distribution.

Algorithm claims in the README and module docstrings are intentionally conservative:
reference implementations are separated from educational experiments, and
research-frontier modules state the gap between the Python code and the papers they
are inspired by.
