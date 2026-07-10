# Roadmap

## Phase 1 — Hardening the current repo

- Add operation counters to every algorithm. Current coverage includes core
  Dijkstra/Dial/radix/Delta/Bellman-Ford paths, BMSSP, stepping variants, ALT
  query stats, and the Johnson negative-weight baseline.
- Add property-style tests for random graphs. Current deterministic coverage
  checks distance optimality and predecessor invariants across generated graph
  families and negative DAGs.
- Add graph generators for grids, DAGs, road-like graphs, and heavy-tailed graphs.
- Add benchmark export to JSON and CSV.

## Phase 2 — Algorithm engineering

- Improve Δ selection policies. Current policies include median, mean,
  trimmed-mean, percentile, degree-adjusted, and adaptive bucket heuristics.
- Add parallel Δ-stepping using thread/process pools for educational benchmarks.
  Current coverage runs independent source queries through thread/process pools;
  it does not claim intra-bucket parallel relaxation.
- Improve ALT landmark selection: random, farthest, avoid, planar-style corners.
  Current coverage includes random, high-degree, farthest-first, avoid-style
  pair sampling, coordinate bounding-box corners, and row-major grid corners.
- Improve CH contraction order: edge difference, contracted neighbors, shortcut cover.
  Current coverage includes static scores and witness-aware dynamic variants for
  edge-difference, contracted-neighbor, shortcut-cover, and level heuristics.

## Phase 3 — Research-frontier implementations

- Replace `bmssp.py` primitive with a faithful implementation of BMSSP recursion.
  Current coverage adds finite-bound recursive splitting around the bounded
  multi-source primitive, with frontier labels carried between recursive levels.
- Develop data structures required by the 2026 faster directed SSSP paper.
  Current coverage includes an incomplete-vertex index with boundary-edge and
  boundary-label tracking for frontier experiments.
- Implement Thorup's component hierarchy for undirected integer SSSP.
  Current coverage includes thresholded connected-component hierarchy levels
  with parent links across increasing integer edge-weight scales.
- Implement simplified decomposition experiments for negative-weight near-linear SSSP.

## Phase 4 — Article series

1. Why Dijkstra sorts too much.
2. Buckets, radix heaps, and integer weights.
3. Δ-stepping and the cost of relaxing order.
4. BMSSP and bounded frontiers.
5. Preprocessing: ALT and Contraction Hierarchies.
6. Why negative weights change everything.
