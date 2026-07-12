# Release Process

This repository is still a research lab, so releases should be lightweight but
repeatable. A release should make clear what is reference implementation work,
what is experimental, and what is optional acceleration.

## Pre-release checks

Run the source-only checks from a clean checkout:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
python scripts/benchmark_smoke_suite.py --output-dir .benchmarks/release_smoke_suite
```

Run the optional Rust extension checks:

```bash
python scripts/build_rust_extension.py --install-source
python -m pytest tests/test_rust_accel.py tests/test_rust_correctness_corpus.py
python scripts/benchmark_rust_accel.py --nodes 5000 --edges 25000 --sources 8 --require-rust --output .benchmarks/release_rust_accel.json
python scripts/profile_rust_accel.py --nodes 5000 --edges 25000 --sources 8 --require-rust --output .benchmarks/release_rust_profile.json
```

Remove the local compiled extension before committing:

```bash
rm -f src/sssp_lab/_sssp_accel*.so src/sssp_lab/_sssp_accel*.pyd src/sssp_lab/_sssp_accel*.dylib
```

On Windows PowerShell:

```powershell
Remove-Item src\sssp_lab\_sssp_accel*.so, src\sssp_lab\_sssp_accel*.pyd, src\sssp_lab\_sssp_accel*.dylib -ErrorAction SilentlyContinue
```

## Version notes

Before tagging:

- Move relevant `CHANGELOG.md` entries from `Unreleased` into a dated version
  section.
- Confirm `pyproject.toml`, `rust/sssp_accel/pyproject.toml`, and
  `rust/sssp_accel/Cargo.toml` versions agree when publishing both Python and
  Rust artifacts.
- Record benchmark/profile commands and the generated local artifact paths in
  the release notes when performance is part of the release.
- Keep claims conservative: Python implementations remain correctness
  references; Rust is optional acceleration.

## Tag and publish

Use an annotated tag:

```bash
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

Build the optional Rust wheel for each target platform and Python ABI:

```bash
python scripts/build_rust_extension.py
```

GitHub release notes should include:

- Summary of user-visible algorithm, benchmark, packaging, and validation
  changes.
- Test status from GitHub Actions.
- Any benchmark/profile caveats, including machine, Python, Rust, graph size,
  seed, and source count.
- Whether a compiled Rust wheel is attached for the target platform.
