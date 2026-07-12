# Faster Directed SSSP Notes

The `frontier_sssp` module is a correctness-first experiment inspired by recent
directed SSSP work. It is not a faithful implementation of the 2026 algorithm.

## Interfaces in the Code

- `construct_frontier(result)` extracts the next expansion frontier from a
  bounded multi-source result.
- `incomplete_vertices(graph, distances)` identifies vertices that still have
  infinite labels.
- `build_incomplete_vertex_index(...)` records complete/incomplete vertices,
  boundary edges crossing into incomplete vertices, and the best boundary label
  for each reachable incomplete vertex.
- `bounded_exploration_round(...)` runs one bounded search from absolute source
  offsets and can accumulate shared `OperationStats`.
- `check_frontier_invariants(...)` verifies that frontier sources carry finite
  labels and that bounds grow monotonically.
- `frontier_partition_sssp(...)` iteratively increases a bound and compares
  naturally against Dijkstra, bounded multi-source exploration, and Δ-stepping.
  It returns round-level frontier diagnostics and accepts `OperationStats` for
  operation-count comparisons.

## Relationship to BMSSP

Shared idea:

- Both experiments expose frontiers instead of globally settling every active
  label through one priority queue.

Differences:

- The current frontier experiment uses geometric bound growth.
- It does not implement the paper's recursive decomposition.
- It implements a small deterministic incomplete-vertex tracker for experiments,
  but not the 2026 paper's full machinery or complexity guarantees.
- It uses heap-based bounded exploration internally, so no asymptotic claim is
  made from the Python implementation.

## Correctness Boundary

The implementation is tested against Dijkstra on directed non-negative graphs.
Source offsets are absolute distances; using local offsets in later rounds would
produce incorrect labels, so tests include a case that exercises this boundary.
