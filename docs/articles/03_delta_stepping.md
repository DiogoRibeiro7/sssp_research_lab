# Delta Stepping

Delta stepping relaxes Dijkstra's strict global ordering. Instead of settling
one exact minimum at a time, it groups labels into buckets of width `Delta`.

Edges with weight at most `Delta` are light. They are repeatedly relaxed inside
the current bucket until no more vertices belong there. Heavier edges are
relaxed after that bucket closes.

The choice of `Delta` matters:

- Very small values behave more like strict ordering.
- Very large values can create crowded buckets and extra reprocessing.
- Graph structure and edge-weight distribution influence the best choice.
- A trimmed-mean policy is useful when a few extreme weights would pull the
  arithmetic mean away from the typical light-edge scale.

The repository includes a sweep script:

```bash
python scripts/benchmark_delta_sweep.py --deltas 1,2,5,10
```

It exports JSON, CSV, and markdown rows with runtime, bucket phases, light
relaxations, heavy relaxations, reinserts, and maximum bucket size.

The implementation is sequential and correctness-first. Python can illustrate
the algorithm's light/heavy split and batching behavior, but interpreter
overhead means it should not be used to claim parallel speedups.
