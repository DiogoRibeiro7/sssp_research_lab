# Validation

This repository is expected to stay runnable with the standard Python toolchain:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
python scripts/benchmark_smoke_suite.py --output-dir .benchmarks/smoke_suite
```

The benchmark smoke suite writes JSON, CSV, and markdown outputs for the
installed CLI plus source-only benchmark scripts. The Rust acceleration
benchmark runs in Python-only fallback mode unless the optional extension is
installed. Files under `.benchmarks/` are local run artifacts and are not part
of the source distribution.

Optional Rust acceleration is checked in two layers:

```bash
python -m pytest tests/test_rust_accel.py tests/test_rust_correctness_corpus.py
```

Without `sssp_lab._sssp_accel`, extension-backed tests skip. With the extension
installed, the corpus cross-checks Dijkstra and circular-Dial against Python
references on disconnected, arbitrary-id, zero-weight, sparse, dense, grid,
road-like, heavy-tailed, layered, wide-integer, equal-weight, and float-weight
graphs.

Algorithm claims in the README and module docstrings are intentionally conservative:
reference implementations are separated from educational experiments, and
research-frontier modules state the gap between the Python code and the papers they
are inspired by.
