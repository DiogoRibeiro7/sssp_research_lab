# Changelog

All notable changes are tracked here. This project uses short conventional
commit messages and keeps release notes focused on user-visible behavior,
validation changes, and benchmark-relevant implementation work.

## Unreleased

### Added

- Optional Rust acceleration package under `rust/sssp_accel` using PyO3 and
  maturin.
- CSR-based Rust kernels for Dijkstra and circular-Dial shortest paths.
- `RustSsspWorkspace` for preparing CSR data once and running repeated
  single-source or batched Rust queries.
- Rust benchmark tooling that writes JSON, CSV, and markdown summaries with
  `speedup_vs_python`.
- Rust profiling tooling that separates graph generation, Python baselines,
  workspace preparation, wrapper calls, prepared calls, and batched calls.
- Packaging helper for building the optional Rust wheel and installing the
  compiled extension into a source checkout for local benchmark runs.
- Extension-backed correctness corpus covering disconnected graphs, arbitrary
  node ids, zero weights, sparse/dense generated graphs, grid graphs,
  road-like graphs, heavy-tailed graphs, layered DAGs, wide integer weights,
  equal weights, and float weights.

### Changed

- GitHub Actions now builds the optional Rust extension, runs extension-backed
  tests, executes a benchmark smoke test, and executes a profiler smoke test.
- PyO3 was updated to `0.29.0`.
- Benchmark docs now include a realistic local Rust baseline and guidance to
  profile before moving more code into Rust.

### Fixed

- Linux CI cargo tests no longer require Python extension-module linker flags.
- Rust benchmark reporting now includes markdown summaries and baseline-relative
  speedups.

## 0.1.0 - Initial research lab

### Added

- Python graph primitives and reference shortest-path implementations.
- Educational and experimental modules for Dijkstra variants, Dial buckets,
  radix heaps, delta stepping, Bellman-Ford, ALT, contraction hierarchies,
  frontier-style SSSP, Thorup-inspired helpers, and negative-weight scaffolding.
- Deterministic graph generators, benchmark scripts, validation docs, and paper
  notes.
