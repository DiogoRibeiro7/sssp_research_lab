# Negative-Weight Near-Linear Notes

The repository contains Bellman-Ford and Johnson-style baselines. It does not
implement the Bernstein, Nanongkai, and Wulff-Nilsen near-linear randomized
algorithm.

## Extracted Subroutine Placeholders

Current toy helpers in `negative_weight.py`:

- `decompose_by_edge_sign(graph)` separates negative and non-negative edges.
- `scale_layers(graph, scale=...)` groups edges by absolute weight scale.
- `seeded_vertex_sample(graph, probability=..., seed=...)` provides
  reproducible random choices.
- `negative_decomposition_experiment(...)` composes these helpers into
  cumulative absolute-weight scale rounds, records deterministic sampled
  vertices and reachable sets, then returns an exact Johnson result checked
  against Bellman-Ford.
- `check_against_bellman_ford(...)` records the correctness oracle used for
  experiments.

These helpers are deterministic except for functions that explicitly accept a
seed. They are scaffolding for experiments, not a claim of near-linear behavior.

## Missing Algorithmic Components

- The paper's graph decomposition.
- Recursive or layered randomized structure.
- The paper's scale-sensitive relaxation schedule.
- Probability analysis and high-probability correctness proof.

## Cycle Handling

Bellman-Ford detects reachable negative cycles. Johnson reweighting uses
Bellman-Ford on an augmented graph, so it also raises when a negative cycle is
present. Any future randomized implementation must state whether it detects
cycles or assumes they are absent.
