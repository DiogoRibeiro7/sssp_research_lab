# Roadmap

## Phase 1 — Hardening the current repo

- Add operation counters to every algorithm.
- Add property-based tests for random graphs.
- Add graph generators for grids, DAGs, road-like graphs, and heavy-tailed graphs.
- Add benchmark export to JSON and CSV.

## Phase 2 — Algorithm engineering

- Improve Δ selection policies.
- Add parallel Δ-stepping using thread/process pools for educational benchmarks.
- Improve ALT landmark selection: random, farthest, avoid, planar-style corners.
- Improve CH contraction order: edge difference, contracted neighbors, shortcut cover.

## Phase 3 — Research-frontier implementations

- Replace `bmssp.py` primitive with a faithful implementation of BMSSP recursion.
- Develop data structures required by the 2026 faster directed SSSP paper.
- Implement Thorup's component hierarchy for undirected integer SSSP.
- Implement simplified decomposition experiments for negative-weight near-linear SSSP.

## Phase 4 — Article series

1. Why Dijkstra sorts too much.
2. Buckets, radix heaps, and integer weights.
3. Δ-stepping and the cost of relaxing order.
4. BMSSP and bounded frontiers.
5. Preprocessing: ALT and Contraction Hierarchies.
6. Why negative weights change everything.
