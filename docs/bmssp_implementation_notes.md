# BMSSP Implementation Notes

The current code implements a bounded multi-source shortest-path subproblem and
a recursive finite-bound scaffold inspired by BMSSP. It is useful as a
correctness-tested building block while the full paper data structures are
developed.

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

Typed Python sketch of the recursive scaffold:

```python
def recursive_bmssp(graph, sources, *, bound, depth, split_factor):
    if depth == 0 or bound is infinite:
        return bounded_multi_source_sssp(graph, sources, bound=bound)
    midpoint = min_source_label + (bound - min_source_label) / split_factor
    lower = recursive_bmssp(graph, sources, bound=midpoint, depth=depth - 1)
    upper = recursive_bmssp(
        graph,
        lower.frontier,
        source_distances=lower.frontier_labels,
        bound=bound,
        depth=depth - 1,
    )
    return merged lower/upper labels, settled sets, and final frontier
```

## Invariants

- Settled labels are strictly below the absolute bound.
- Frontier labels are at or above the absolute bound.
- Settled and frontier sets are disjoint.
- All edge weights must be non-negative.
- Source offsets are absolute distances when supplied by a caller.
- Recursive leaf subproblems record their source set, bound, settled set, and
  frontier for inspection.

These invariants can be checked with `debug=True`.

## Paper Coverage

Implemented:

- Bounded multi-source exploration with absolute source labels.
- Frontier exposure for labels that reach or exceed the bound.
- Runtime counters and optional invariant checks.
- Recursive finite-bound splitting that composes bounded subproblems and carries
  frontier labels forward as absolute source offsets.

Not implemented:

- Pivot selection and paper-specific frontier partitioning.
- The proof-level data structures and asymptotic guarantees.
- Stopping criteria from the full recursive algorithm.

## Python Limitations

The implementation uses `heapq` for clarity, so it intentionally does not break
the sorting barrier. It should be compared against Dijkstra for correctness and
used as a scaffold for future recursive experiments.
