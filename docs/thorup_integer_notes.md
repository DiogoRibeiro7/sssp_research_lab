# Thorup Integer SSSP Notes

Thorup's linear-time undirected SSSP algorithm relies on a component hierarchy,
integer buckets over components, and word-RAM assumptions. The repository does
not implement that hierarchy yet.

## Current Code

`thorup_like.py` provides:

- validation for the target setting: undirected graphs with positive integer
  weights,
- a radix-heap Dijkstra baseline for correctness checks,
- distance-scale buckets that are useful when experimenting with future
  component hierarchy code.

## Missing Algorithmic Components

- Component hierarchy construction.
- Component-level bucket traversal rules.
- Word-RAM integer priority operations.
- Proof-level invariants for the hierarchy.

## Validation Strategy

Until the hierarchy is implemented, all experiments should compare against both
binary-heap Dijkstra and radix-heap Dijkstra on undirected integer graphs,
including trees, cycles, sparse graphs, and disconnected components.

Python can validate correctness of ideas, but it cannot directly demonstrate
Thorup's word-RAM linear-time guarantee.
