# Algorithm Matrix

| Algorithm | Correct implementation? | Used as reference? | Main idea | Weakness |
|---|---:|---:|---|---|
| Binary-heap Dijkstra | yes | yes | strict global priority queue | sorting bottleneck |
| Dial | yes | no | integer buckets | large max distance is expensive |
| Radix-heap Dijkstra | yes | no | monotone integer priority queue | integer weights only |
| Δ-stepping | yes, sequential educational | no | buckets + light/heavy edges | Δ selection matters |
| Bellman-Ford | yes | yes for negative weights | repeated relaxation | slow |
| ALT | yes | no | A* with landmark lower bounds | preprocessing and landmark selection |
| Contraction Hierarchies | yes, small-graph educational | no | shortcuts + upward bidirectional search | contraction order and witness search complexity |
| Bounded multi-source primitive | yes | no | bounded frontier expansion | not full BMSSP theorem |
| Frontier partition SSSP | experimental | no | expanding bounded frontiers | not a published algorithm implementation |
| Incomplete-vertex index | experimental helper | no | boundary labels into unresolved vertices | not full 2026 machinery |
| Thorup-like lab | baseline only | no | integer component lab | not full Thorup hierarchy |
| Johnson SSSP | yes | no | potentials + Dijkstra | not near-linear negative SSSP |
