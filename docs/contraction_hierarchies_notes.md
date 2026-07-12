# Contraction Hierarchies Notes

The CH module is a small-graph educational implementation. It builds exact
shortcuts with bounded witness searches, stores upward and downward graphs, and
can unpack shortcut paths for query inspection.

Ordering support has two tiers:

- Static `contraction_order` heuristics score each node once from local graph
  structure: degree, edge difference, contracted-neighbor count, shortcut cover,
  and level.
- Witness-aware `witness_contraction_order` heuristics recompute priorities as
  nodes are selected. They estimate required shortcuts with bounded witness
  searches and update a working graph before choosing the next node.

`build_ch_index` accepts either an explicit order or a heuristic name. Prefix a
dynamic heuristic with `witness_`, for example:

```bash
python - <<'PY'
from sssp_lab.algorithms.contraction_hierarchies import build_ch_index
from sssp_lab.graph import Graph

graph = Graph.from_edges([(0, 1, 1), (1, 2, 1), (0, 2, 5)], directed=False)
index = build_ch_index(graph, heuristic="witness_edge_difference")
print(index.rank)
PY
```

These orderings are useful for inspection and small benchmarks, not for large
road-network preprocessing.

`ch_query` and `ch_query_path` accept `OperationStats` for query diagnostics.
Counters cover both upward searches used by the bidirectional query.
