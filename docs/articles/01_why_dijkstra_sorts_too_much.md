# Why Dijkstra Sorts Too Much

Dijkstra's algorithm solves single-source shortest paths on directed or
undirected graphs with non-negative weights. The non-negative assumption is what
makes settling a vertex final: once the smallest tentative label is removed from
the priority queue, no future path can improve it.

The reference implementation uses a global binary heap:

```python
heap: list[tuple[float, Node]] = [(0.0, source)]
...
distance, node = heapq.heappop(heap)
...
heapq.heappush(heap, (candidate, edge.target))
```

That heap is a global ordering device. Every improvement competes with every
other tentative label, even when many labels are close enough that a coarser
ordering would still be correct.

Lazy heaps also create stale entries. If a better distance is discovered after
an older heap entry was pushed, the old entry remains until popped and skipped.
The repository instruments these events as queue pushes, pops, stale pops,
relaxations, and settled nodes.

A small worked graph:

- `0 -> 1` with weight `2`
- `0 -> 2` with weight `5`
- `1 -> 2` with weight `1`
- `2 -> 3` with weight `3`

Dijkstra settles `0`, improves `1` and `2`, then improves `2` again through
`1`. The stale `(5, 2)` entry remains in the heap even though the final label
for `2` is `3`.

The checked-in smoke benchmark reports:

| algorithm | seconds | reachable |
|---|---:|---:|
| binary heap Dijkstra | 0.000209596 | 98 |
| Dial buckets | 0.003914479 | 98 |
| radix heap | 0.000427765 | 98 |
| delta stepping | 0.000340120 | 98 |

These numbers are not universal performance claims; they show why the lab keeps
multiple ordering strategies around. Buckets, radix heaps, stepping algorithms,
and bounded frontiers all ask how much ordering shortest paths really need.
