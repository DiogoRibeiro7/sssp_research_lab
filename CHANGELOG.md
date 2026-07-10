# Changelog

All notable changes are tracked here. This project uses short conventional
commit messages and keeps release notes focused on user-visible behavior,
validation changes, and benchmark-relevant implementation work.

## Unreleased

No unreleased changes.

## 1.0.0 - 2026-07-11

### Added

- Trimmed-mean Δ-selection policy for stepping experiments.
- Repeated-source Δ-stepping benchmark helper with sequential, thread, and
  process-pool modes plus JSON, CSV, and markdown exports.
- ALT landmark strategies for avoid-style pair sampling and coordinate
  bounding-box corners.
- Witness-aware Contraction Hierarchies ordering variants and candidate metrics.
- Finite-bound recursive BMSSP scaffold that composes bounded subproblems
  through frontier labels.
- Incomplete-vertex index for frontier experiments, including boundary-edge and
  boundary-label tracking.
- Thorup-style thresholded component hierarchy scaffold for undirected positive
  integer graphs.
- Simplified negative-weight decomposition experiment with sign decomposition,
  absolute-weight scale rounds, seeded vertex samples, and Bellman-Ford-checked
  Johnson results.
- Markdown summaries for benchmark scripts.
- Graph invariant tests covering distance optimality and predecessor chains.
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

- Roadmap and algorithm notes now reflect current coverage for Δ policies,
  repeated-source Δ-stepping, ALT landmarks, CH ordering, BMSSP recursion,
  frontier data structures, Thorup-style hierarchy scaffolding, and
  negative-weight decomposition experiments.
- ALT benchmark tooling now supports selectable landmark strategies.
- Frontier partition diagnostics now include incomplete-vertex and boundary-edge
  counts.
- GitHub Actions now builds the optional Rust extension, runs extension-backed
  tests, executes a benchmark smoke test, and executes a profiler smoke test.
- PyO3 was updated to `0.29.0`.
- Benchmark docs now include a realistic local Rust baseline and guidance to
  profile before moving more code into Rust.

### Fixed

- CH path queries now search the reverse of the downward graph for backward
  labels, fixing low-rank target cases.
- Negative-weight baseline instrumentation now reports operation counters for
  Johnson and reference runs.
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
