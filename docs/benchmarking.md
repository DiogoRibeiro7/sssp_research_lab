# Benchmarking Plan

The benchmark should compare algorithms under graph families where ordering pressure changes.

## Graph families

1. Sparse Erdős-Rényi directed graphs.
2. Grid graphs with local edges.
3. Road-like graphs with low degree and positive integer weights.
4. Heavy-tailed degree graphs.
5. Layered DAGs.
6. Graphs with many equal or near-equal weights.
7. Graphs with wide integer-weight ranges.
8. Graphs with negative edges but no negative cycles.

## Metrics

- Runtime.
- Number of relaxations.
- Number of queue pushes.
- Number of stale queue entries.
- Maximum bucket occupancy.
- Settled vertices per phase.
- Peak memory.
- Distance correctness against reference.

## Acceptance criteria

- Every non-negative SSSP algorithm must match binary-heap Dijkstra.
- Every negative-weight algorithm must match Bellman-Ford on small graphs.
- ALT and CH must match point-to-point Dijkstra for all sampled pairs.
- Benchmarks must include deterministic seeds.
- Results must be exported as JSON, CSV, and markdown summaries for quick review.

## Local commands

```bash
sssp-benchmark --nodes 1000 --edges 5000 --output .benchmarks/cli_sssp.json
python scripts/benchmark_sssp.py --nodes 1000 --edges 5000 --output .benchmarks/sssp.json
python scripts/benchmark_delta_sweep.py --nodes 1000 --edges 5000 --output .benchmarks/delta_sweep.json
python scripts/benchmark_stepping_policies.py --nodes 500 --edges 2500 --output .benchmarks/stepping_policies.json
python scripts/benchmark_parallel_delta.py --nodes 1000 --edges 5000 --sources 8 --output .benchmarks/parallel_delta.json
python scripts/benchmark_ch.py --nodes 100 --edges 300 --pairs 10 --output .benchmarks/ch.json
python scripts/benchmark_frontier.py --nodes 1000 --edges 5000 --output .benchmarks/frontier.json
python scripts/benchmark_negative.py --nodes 100 --edges 300 --output .benchmarks/negative.json
```

Each command writes `.json`, `.csv`, and `.md` files with the same base path.

## Rust acceleration baseline

Local baseline captured on 2026-07-10 with Python 3.13.5, rustc 1.88.0,
release-mode maturin build, Windows, and deterministic seed 17:

```powershell
python scripts\benchmark_rust_accel.py --nodes 20000 --edges 120000 --sources 16 --seed 17 --require-rust --output .benchmarks\rust_realistic_20k_120k_16.json
```

| algorithm | backend | sources | seconds | seconds/source | speedup vs python |
|---|---|---:|---:|---:|---:|
| dijkstra | python | 16 | 1.915420 | 0.119714 |  |
| dial_circular | python | 16 | 3.601862 | 0.225116 |  |
| csr_conversion | python | 16 | 0.056908 | 0.003557 |  |
| dijkstra | rust | 16 | 1.517154 | 0.094822 | 1.26x |
| dial_circular | rust | 16 | 1.943071 | 0.121442 | 1.85x |
| dijkstra_csr_reused | rust | 16 | 0.155608 | 0.009726 | 12.31x |
| dial_circular_csr_reused | rust | 16 | 0.149037 | 0.009315 | 24.17x |
| dijkstra_csr_batch | rust | 16 | 0.098891 | 0.006181 | 19.37x |
| dial_circular_csr_batch | rust | 16 | 0.060473 | 0.003780 | 59.56x |

Interpretation: wrapper-level Rust calls still pay Python graph conversion and result
materialization costs, while CSR reuse and batched source execution isolate the kernel
path and show the acceleration target more clearly.

Before adding more Rust code, capture a profile for the same graph shape:

```powershell
python scripts\profile_rust_accel.py --nodes 20000 --edges 120000 --sources 16 --seed 17 --require-rust --output .benchmarks\rust_profile_20k_120k_16.json
```

The profiler writes JSON and markdown summaries of top cumulative Python
functions per phase, separating graph generation, Python baselines, workspace
preparation, end-to-end Rust wrappers, prepared single-source calls, and prepared
batched calls.
