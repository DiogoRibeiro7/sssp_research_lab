# BMSSP Implementation Notes

The current code implements a bounded multi-source shortest-path subproblem,
not the full recursive BMSSP algorithm from Duan et al. It is useful as a
correctness-tested building block while the full data structures and recursion
are developed.

## Algorithm Blocks

Typed Python sketch of the implemented bounded subproblem:

```python
def bounded_multi_source_sssp(
    graph: Graph,
    sources: set[Node],
    *,
    bound: float,
    source_distances: dict[Node, float] | None,
) -> BoundedMultiSourceResult:
    distances = {node: inf for node in graph.nodes}
    queue = [(source_distance(source), source) for source in sources]
    while queue:
        distance, node = heappop(queue)
        if distance != distances[node]:
            continue
        if distance >= bound:
            frontier.add(node)
            continue
        settled.add(node)
        for edge in graph.neighbors(node):
            relax edge if it improves the target label
    return settled nodes below bound and frontier nodes at or above bound
```

## Invariants

- Settled labels are strictly below the absolute bound.
- Frontier labels are at or above the absolute bound.
- Settled and frontier sets are disjoint.
- All edge weights must be non-negative.
- Source offsets are absolute distances when supplied by a caller.

These invariants can be checked with `debug=True`.

## Paper Coverage

Implemented:

- Bounded multi-source exploration with absolute source labels.
- Frontier exposure for labels that reach or exceed the bound.
- Runtime counters and optional invariant checks.

Not implemented:

- Recursive BMSSP decomposition.
- Pivot selection and paper-specific frontier partitioning.
- The proof-level data structures and asymptotic guarantees.
- Stopping criteria from the full recursive algorithm.

## Python Limitations

The implementation uses `heapq` for clarity, so it intentionally does not break
the sorting barrier. It should be compared against Dijkstra for correctness and
used as a scaffold for future recursive experiments.
