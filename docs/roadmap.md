# Roadmap

This roadmap tracks the repository as a research lab, not as a promise that
every referenced paper has a proof-level implementation. The current checkpoint
has solid reference algorithms, benchmark/export infrastructure, and a
correctness-first BMSSP scaffold. The remaining work is mostly algorithmic
fidelity for the research-frontier modules.

## Current Checkpoint

- Core reference algorithms are in place: binary-heap Dijkstra, Dial,
  radix-heap Dijkstra, delta-stepping, Bellman-Ford, Johnson, ALT, and
  small-graph Contraction Hierarchies.
- Benchmark scripts export deterministic JSON, CSV, and markdown artifacts.
- Graph generators cover random, grid, road-like, layered DAG, heavy-tailed,
  equal-weight, and wide integer-weight families.
- Optional Rust acceleration exists for selected non-negative integer and CSR
  kernels; Python remains the correctness reference.
- BMSSP has moved beyond the original bounded primitive into a paper-shaped
  correctness scaffold with shared labels, pivots, base cases, derived
  parameters, queue semantics, and debug invariants.

## Phase 1 - Core Hardening

Status: mostly complete.

- Operation counters cover the major algorithms and benchmark paths.
- Property-style tests check generated graph families, predecessor invariants,
  negative DAGs, and Rust/Python parity where applicable.
- Benchmark export paths are deterministic and documented.
- Remaining work: keep coverage current as experimental algorithms change.

## Phase 2 - Algorithm Engineering

Status: active but stable enough for experiments.

- Delta-stepping has multiple delta-selection policies: median, mean,
  trimmed-mean, percentile, degree-adjusted, and adaptive bucket heuristics.
- Parallel delta experiments run independent source queries through thread and
  process pools. They do not claim intra-bucket parallel relaxation.
- ALT supports random, high-degree, farthest-first, avoid-style pair sampling,
  coordinate bounding-box corners, and row-major grid corners.
- Contraction Hierarchies include static and witness-aware dynamic contraction
  scoring for edge-difference, contracted-neighbor, shortcut-cover, and level
  heuristics.
- Remaining work: improve benchmarks that compare these policies on larger and
  more realistic graph families.

## Phase 3 - BMSSP And Sorting-Barrier Work

Status: correctness-first scaffold implemented; proof-level BMSSP unfinished.

Implemented:

- `bounded_multi_source_sssp(...)` with explicit frontier labels.
- `recursive_bmssp(...)` as a finite-bound recursive scaffold.
- `BMSSPQueue` semantic interface for `Insert`, `BatchPrepend`, and `Pull`.
- `find_pivots(...)` over shared tentative labels and predecessors.
- `bmssp_base_case(...)` as a distinct level-zero helper.
- `derive_bmssp_parameters(...)`, `BMSSPParameters`, and
  `BMSSPConfig.from_graph(...)`.
- `paper_bmssp(...)` under a separate experimental name.
- Tests for random directed graphs, layered ties, disconnected vertices,
  adversarial bound thresholds, derived parameters, and debug predecessor-chain
  invariants.

Next BMSSP work:

1. Replace `BMSSPQueue` internals with a block/list implementation while
   preserving the current tested semantic interface.
2. Add stronger accounting for partial execution so `work_limit` behavior more
   closely matches the proof-level stopping rule.
3. Add deterministic tie-ordering machinery for equal-length paths.
4. Add constant-degree graph transformation experiments.
5. Only after the above, evaluate whether `paper_bmssp(...)` can replace or
   supersede `recursive_bmssp(...)`.

Not yet claimed:

- the paper's asymptotic data-structure complexity,
- the constant-degree reduction,
- comparison-addition tie-ordering,
- the `O(m log^(2/3) n)` running time.

## Phase 4 - Other Research-Frontier Modules

Status: experimental scaffolds.

- Faster directed SSSP notes and frontier experiments currently include
  incomplete-vertex indexing with boundary-edge and boundary-label tracking.
- Thorup-like integer SSSP currently includes thresholded component hierarchy
  levels and radix-based baselines, not Thorup's full linear-time algorithm.
- Negative-weight experiments include sign decomposition, absolute-weight scale
  rounds, seeded vertex samples, Bellman-Ford checks, and Johnson baselines.
- Remaining work: decide which frontier module should receive the next deep
  implementation push after BMSSP queue internals.

## Phase 5 - Documentation And Articles

Status: partially complete.

- README and BMSSP implementation notes now describe the current BMSSP scaffold
  without claiming proof-level completion.
- Algorithm matrix distinguishes stable references, educational versions, and
  experimental scaffolds.
- Article topics remain:
  1. Why Dijkstra sorts too much.
  2. Buckets, radix heaps, and integer weights.
  3. Delta-stepping and the cost of relaxing order.
  4. BMSSP and bounded frontiers.
  5. Preprocessing: ALT and Contraction Hierarchies.
  6. Why negative weights change everything.

## Definition Of Done For "Finished"

The repo can be considered finished as a polished research-lab release when:

- README, roadmap, algorithm matrix, and implementation notes agree.
- The full Python suite passes on supported Python versions.
- Benchmark scripts produce documented artifacts from a clean install.
- Experimental modules are clearly labeled and do not overclaim paper fidelity.
- Release metadata, changelog, citation metadata, and package version are in
  sync.

It can only be considered finished as a faithful BMSSP-paper implementation
after the block/list data structure, proof-level partial accounting,
tie-ordering machinery, constant-degree transformation, and empirical validation
are complete.
