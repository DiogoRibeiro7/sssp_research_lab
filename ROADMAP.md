# Roadmap

This repository is a shortest-path research lab. The near-term goal is a
polished, reproducible lab release with clear boundaries between reference
algorithms, educational implementations, and research-frontier scaffolds. The
longer-term goal is to move the BMSSP work from correctness-first scaffold
toward a faithful implementation of the paper's recursive machinery.

## Current Position

- Core reference algorithms are implemented and tested.
- Benchmark scripts export deterministic JSON, CSV, and markdown artifacts.
- Optional Rust acceleration exists for selected kernels, with Python as the
  correctness reference.
- BMSSP has a paper-shaped correctness scaffold: shared labels, pivots, base
  cases, derived parameters, queue semantics, and debug invariants.

## Next Priorities

1. **BMSSP queue internals**
   Replace the heap/dictionary `BMSSPQueue` internals with a block/list
   implementation while preserving the tested `Insert`, `BatchPrepend`, and
   `Pull` semantics.

2. **BMSSP partial execution accounting**
   Tighten `paper_bmssp(...)` work accounting so early returns more closely
   match the proof-level stopping rule.

3. **Tie ordering**
   Add deterministic comparison-addition tie handling for equal-length paths.

4. **Constant-degree transformation**
   Prototype the graph transformation needed by the BMSSP paper and validate
   that it preserves shortest-path distances.

5. **Benchmark realism**
   Expand benchmark coverage on larger generated graph families and record
   acceptance criteria for algorithm comparisons.

6. **Research-frontier triage**
   Decide whether the next deep implementation push after BMSSP should be
   faster directed SSSP frontier machinery, Thorup-style integer SSSP, or
   negative-weight decomposition experiments.

## Not Done

The repository does not yet claim:

- the BMSSP paper's asymptotic data-structure complexity,
- the constant-degree reduction,
- proof-level partial-execution accounting,
- comparison-addition tie-ordering,
- the `O(m log^(2/3) n)` BMSSP running time.

The detailed phase plan is in [docs/roadmap.md](docs/roadmap.md).
