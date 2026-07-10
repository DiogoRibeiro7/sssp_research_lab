# Benchmarking Plan

The benchmark should compare algorithms under graph families where ordering pressure changes.

## Graph families

1. Sparse Erdős-Rényi directed graphs.
2. Grid graphs with local edges.
3. Road-like graphs with low degree and positive integer weights.
4. Heavy-tailed degree graphs.
5. Layered DAGs.
6. Graphs with many equal or near-equal weights.
7. Graphs with wide integer-weight ranges.
8. Graphs with negative edges but no negative cycles.

## Metrics

- Runtime.
- Number of relaxations.
- Number of queue pushes.
- Number of stale queue entries.
- Maximum bucket occupancy.
- Settled vertices per phase.
- Peak memory.
- Distance correctness against reference.

## Acceptance criteria

- Every non-negative SSSP algorithm must match binary-heap Dijkstra.
- Every negative-weight algorithm must match Bellman-Ford on small graphs.
- ALT and CH must match point-to-point Dijkstra for all sampled pairs.
- Benchmarks must include deterministic seeds.
- Results must be exported as JSON and CSV.
