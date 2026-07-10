# SSSP Research Lab

A Python research repository for shortest-path algorithms around the theme:

> **How much ordering does a shortest-path algorithm really need?**

The repo is designed as an implementation lab for papers related to BMSSP and the sorting barrier in single-source shortest paths.

## What is implemented

| Module | Algorithm | Status | Weight type | Graph type |
|---|---|---:|---|---|
| `dijkstra_binary_heap.py` | Dijkstra with binary heap | working reference | non-negative real | directed/undirected |
| `dial.py` | Dial bucket Dijkstra | working | non-negative integer | directed/undirected |
| `radix_heap.py`, `dijkstra_radix.py` | Radix-heap Dijkstra | working | non-negative integer | directed/undirected |
| `delta_stepping.py` | Sequential Δ-stepping | working educational version | non-negative real | directed/undirected |
| `bellman_ford.py` | Bellman-Ford | working reference | negative allowed, no negative cycles | directed/undirected |
| `alt.py` | ALT point-to-point shortest paths | working | non-negative real | directed/undirected |
| `contraction_hierarchies.py` | Contraction Hierarchies | working small-graph educational version | non-negative real | directed/undirected |
| `bmssp.py` | Bounded multi-source SSSP primitive | working primitive, not a proof-level BMSSP paper implementation | non-negative real | directed/undirected |
| `frontier_sssp.py` | Frontier-partition SSSP experiment inspired by 2026 directed SSSP | experimental | non-negative real | directed |
| `thorup_like.py` | Integer SSSP lab helpers inspired by Thorup | experimental helper, not Thorup's full component hierarchy | non-negative integer | undirected |
| `negative_weight.py` | Johnson potentials + Bellman-Ford fallback | working educational baseline, not near-linear Bernstein-Nanongkai-Wulff-Nilsen | integer/real negative allowed | directed |

The research-frontier papers are difficult enough that a clean Python repository should be honest about what is exact, what is educational, and what is a scaffold for a coding agent. The prompts in `prompts/` are meant to harden the frontier modules step by step.

## Papers covered

See `docs/papers.md` and `references.bib`.

Main targets:

1. Duan et al. — *Breaking the Sorting Barrier for Directed Single-Source Shortest Paths*.
2. Duan et al. — *A Faster Directed Single-Source Shortest Path Algorithm*.
3. Meyer and Sanders — *Δ-stepping: a parallelizable shortest path algorithm*.
4. Dong et al. — *Efficient Stepping Algorithms and Implementations for Parallel Shortest Paths*.
5. Thorup — *Undirected Single-Source Shortest Paths with Positive Integer Weights in Linear Time*.
6. Goldberg and Harrelson — *Computing the Shortest Path: A* Search Meets Graph Theory*.
7. Geisberger et al. — *Contraction Hierarchies*.
8. Bernstein, Nanongkai, Wulff-Nilsen — *Negative-Weight Single-Source Shortest Paths in Near-linear Time*.

## Install

```bash
poetry install
poetry run pytest
```

Without Poetry:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest
pytest
```

## Example

```python
from sssp_lab.graph import Graph
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.delta_stepping import delta_stepping

edges = [
    (0, 1, 2.0),
    (0, 2, 5.0),
    (1, 2, 1.0),
    (2, 3, 3.0),
]

graph = Graph.from_edges(edges, directed=True)
print(dijkstra(graph, 0).distances)
print(delta_stepping(graph, 0, delta=2.0).distances)
```

## Repository goals

- Provide reliable reference implementations.
- Make algorithmic assumptions explicit.
- Compare ordering strategies: heap ordering, buckets, radix heaps, stepping, landmarks, preprocessing, and bounded frontiers.
- Keep research-frontier modules isolated from production-ready modules.
- Provide prompts that a coding agent can use to improve the repo without destroying correctness.

## Development commands

```bash
ruff check .
mypy src
pytest
python scripts/benchmark_sssp.py --nodes 1000 --edges 5000
```

## Optional Rust acceleration

The repository includes an optional PyO3/maturin extension under
`rust/sssp_accel` for CSR-based Dijkstra and circular Dial kernels. The Python
algorithms remain the correctness reference.

```bash
cd rust/sssp_accel
maturin develop
python -m pytest tests/test_rust_accel.py
```

See `docs/rust_acceleration.md` for the design boundary and wrapper API.
