# Buckets and Radix Heaps

Integer weights change the priority-queue problem. If all edge weights are
non-negative integers, tentative distances are monotone integer keys rather than
arbitrary real priorities.

Dial's algorithm exploits small integer weights with buckets. The simple
implementation allocates one bucket for every possible distance up to
`max_edge_weight * (n - 1)`. That is easy to reason about but can waste memory
when the maximum edge weight is large.

The circular Dial variant keeps only `C + 1` buckets for maximum edge weight
`C`. It advances a current distance pointer and uses modulo indexing. This keeps
memory bounded by the edge-weight range rather than the maximum path length.

Radix-heap Dijkstra uses a monotone integer priority queue. It accepts duplicate
keys, rejects keys below the last popped key, and avoids Dial's large sparse
bucket array. The repository tests the heap independently and then validates
radix-heap Dijkstra against binary-heap Dijkstra.

The tradeoff is practical:

- Simple Dial is direct and fast when weights are tiny.
- Circular Dial reduces bucket memory for bounded weights.
- Radix heaps handle wider integer ranges while preserving monotone ordering.
- Binary heaps remain the general non-negative reference.
