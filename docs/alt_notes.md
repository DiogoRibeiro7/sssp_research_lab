# ALT Notes

ALT combines A* search, landmarks, and triangle-inequality lower bounds.

For an undirected graph, a landmark `L` gives the admissible lower bound
`abs(d(L, target) - d(L, node))`. Directed graphs need both directions:

- distances from each landmark in the original graph,
- distances to each landmark, computed by running Dijkstra on the reversed
  graph.

The query uses the maximum valid lower bound across landmarks. This keeps the
heuristic admissible, so reported distances are checked against Dijkstra in
tests and benchmarks.

Landmark selection strategies in the package include random, farthest-first,
high-degree, avoid-style pair sampling, coordinate bounding-box corners, and
row-major grid corners. The precomputed distances are cached in `ALTIndex`;
repeated queries should reuse the same index.

The avoid-style selector is intentionally deterministic and educational. It
samples source-target pairs, looks for a large gap between the exact distance and
the current ALT lower bound, then adds a node from that path that is far from the
existing landmarks.
