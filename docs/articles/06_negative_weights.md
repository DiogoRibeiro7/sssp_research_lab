# Negative Weights

Negative edges break Dijkstra's final-settling rule. A vertex that looks final
can later be improved through a negative edge.

Counterexample:

- `0 -> 1` with weight `1`
- `0 -> 2` with weight `5`
- `2 -> 1` with weight `-10`

If `1` is settled too early, the later path `0 -> 2 -> 1` improves it to `-5`.
Bellman-Ford remains the reference baseline because it repeatedly relaxes all
edges and detects reachable negative cycles.

Johnson reweighting computes potentials with Bellman-Ford, then transforms edge
weights so Dijkstra can run on non-negative reduced costs. Final distances are
converted back with the potentials.

Negative cycles are different from negative edges. If a reachable cycle has
negative total weight, no finite shortest path exists for affected vertices.

Near-linear negative-weight SSSP is a separate research problem. The repository
includes deterministic toy helpers for sign decomposition, scale layers, and
seeded sampling, but it does not claim to implement the near-linear randomized
algorithm.
