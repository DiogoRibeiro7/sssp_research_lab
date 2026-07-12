# SSSP Research Lab

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21302832.svg)](https://doi.org/10.5281/zenodo.21302832)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

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
| `bmssp.py` | Bounded multi-source SSSP + recursive scaffold | working scaffold, not a proof-level BMSSP paper implementation | non-negative real | directed/undirected |
| `frontier_sssp.py` | Frontier-partition SSSP experiment inspired by 2026 directed SSSP | experimental | non-negative real | directed |
| `thorup_like.py` | Integer SSSP lab helpers inspired by Thorup | component hierarchy scaffold + radix baseline, not Thorup's full algorithm | non-negative integer | undirected |
| `negative_weight.py` | Johnson, Bellman-Ford, and decomposition experiments | working educational baseline, not near-linear Bernstein-Nanongkai-Wulff-Nilsen | integer/real negative allowed | directed |

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

## Command Line

The package installs a small benchmark command:

```bash
sssp-benchmark --nodes 1000 --edges 5000 --seed 7
sssp-benchmark --nodes 1000 --edges 5000 --output .benchmarks/cli_sssp.json
```

When `--output` is supplied, the command writes JSON, CSV, and markdown files
with the same base path.

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

Release notes live in `CHANGELOG.md`; the repeatable release checklist is in
`docs/release_process.md`.

## Benchmark outputs

Every benchmark script is deterministic (seeded) and writes three files that
share a base path under `.benchmarks/`: a machine-readable `.json`, a flat
`.csv` for spreadsheets, and a `.md` summary table for quick review. See
`docs/benchmarking.md` for the graph families, metrics, and acceptance criteria.

| Script | Output base (`.json` / `.csv` / `.md`) | What it measures |
|---|---|---|
| `scripts/benchmark_sssp.py` | `.benchmarks/sssp.*` | Per-algorithm runtime and reachable-node count on one graph. |
| `scripts/benchmark_delta_sweep.py` | `.benchmarks/delta_sweep.*` | Δ-stepping across a range of Δ values with relaxation/queue/bucket instrumentation. |
| `scripts/benchmark_stepping_policies.py` | `.benchmarks/stepping_policies.*` | Stepping policies compared across graph families and seeds. |
| `scripts/benchmark_parallel_delta.py` | `.benchmarks/parallel_delta.*` | Multi-source Δ-stepping across worker counts, with per-source timing. |
| `scripts/benchmark_alt.py` | `.benchmarks/alt.*` | ALT vs. plain Dijkstra for sampled point-to-point queries. |
| `scripts/benchmark_ch.py` | `.benchmarks/ch.*` | Contraction Hierarchies vs. Dijkstra for sampled point-to-point queries. |
| `scripts/benchmark_frontier.py` | `.benchmarks/frontier.*` | Frontier-partition SSSP vs. Dijkstra, BMSSP primitive, and Δ-stepping. |
| `scripts/benchmark_negative.py` | `.benchmarks/negative.*` | Bellman-Ford, Johnson, and negative-weight decomposition experiments on negative DAGs. |
| `scripts/benchmark_rust_accel.py` | `.benchmarks/rust_accel.*` | Rust vs. Python kernels with `speedup_vs_python`. |
| `scripts/profile_rust_accel.py` | `.benchmarks/rust_profile.*` | Top cumulative Python functions per phase (`.json` / `.md` only). |

### Data dictionary

Columns are a union across the benchmark outputs; each file contains the subset
relevant to its script.

| Field | Type | Meaning |
|---|---|---|
| `algorithm` | string | Algorithm/kernel variant identifier (e.g. `binary_heap_dijkstra`, `delta_stepping_delta_5`). |
| `backend` | string | Execution backend: `python` or `rust` (Rust benchmarks only). |
| `graph_family` | string | Generated graph family (see `docs/benchmarking.md`), e.g. `road_like`, `layered_dag`. |
| `policy` | string | Stepping policy under test (stepping-policy benchmark). |
| `mode` | string | Parallel execution mode for multi-source Δ-stepping. |
| `delta` | number | Δ value used by the stepping algorithm. |
| `seed` | integer | Deterministic RNG seed used to generate the graph. |
| `source` / `target` | integer | Endpoint node ids for point-to-point (ALT) queries. |
| `source_count` / `workers` | integer | Number of sources queried / worker threads used. |
| `seconds` | number | Wall-clock runtime for the run, in seconds. |
| `seconds_per_source` | number | `seconds` divided by `source_count` for multi-source runs. |
| `dijkstra_seconds` / `alt_seconds` | number | Per-query runtime for the Dijkstra baseline and ALT (ALT benchmark). |
| `speedup_vs_python` | number | Rust runtime speedup relative to the Python baseline (Rust benchmark). |
| `reachable` | integer | Number of nodes reached from the source(s). |
| `relaxations` | integer | Total edge relaxations performed. |
| `light_relaxations` / `heavy_relaxations` | integer | Light- vs. heavy-edge relaxations (Δ-stepping). |
| `queue_pushes` / `queue_pops` | integer | Priority-queue insertions and extractions. |
| `stale_pops` | integer | Queue extractions discarded as outdated. |
| `settled_nodes` | integer | Nodes finalized with a confirmed shortest distance. |
| `bucket_phases` | integer | Number of bucket-processing phases (Δ-stepping / Dial). |
| `bucket_insertions` / `bucket_reinserts` | integer | Bucket insertions and re-insertions from relaxations. |
| `max_bucket_size` | integer | Peak occupancy of any single bucket. |
| `heuristic_evaluations` / `alt_heuristic_evaluations` | integer | Landmark/heuristic lower-bound evaluations. |
| `alt_heap_pops` / `alt_settled_nodes` | integer | Heap extractions / settled nodes for the ALT query. |
| `phase` | string | Profiler phase (graph generation, Python baseline, workspace prep, wrapper, prepared, batched). |
| `top_cumulative` | list | Top cumulative-time Python functions for the phase (profiler output). |

## Optional Rust acceleration

The repository includes an optional PyO3/maturin extension under
`rust/sssp_accel` for CSR-based Dijkstra and circular Dial kernels. The Python
algorithms remain the correctness reference.

```bash
python -m pip install maturin
python scripts/build_rust_extension.py --install-source
python -m pytest tests/test_rust_accel.py
python scripts/benchmark_rust_accel.py --require-rust
```

See `docs/rust_acceleration.md` for the design boundary and wrapper API, and
`docs/packaging.md` for Python-only, local-extension, and wheel install flows.

## How to cite

If you use this repository in academic work, please cite it. Citation metadata
lives in `CITATION.cff` (GitHub renders a "Cite this repository" button from it,
and tools such as `cffconvert` can export BibTeX/APA/RIS).

For the source repository, cite:

```bibtex
@software{ribeiro_sssp_research_lab_2026,
  author    = {Ribeiro, Diogo},
  title      = {{SSSP Research Lab: Implementable Shortest-Path Algorithms
                Inspired by Sorting-Barrier SSSP Research}},
  year       = {2026},
  version    = {1.0.0},
  doi        = {10.5281/zenodo.21302833},
  url        = {https://github.com/DiogoRibeiro7/sssp_research_lab}
}
```

After Zenodo archives a release, prefer the version DOI for exact
reproducibility or the concept DOI to cite the latest archived release.

## License

This work is licensed under the [Creative Commons Attribution 4.0 International
License (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/). You are free
to share and adapt the material for any purpose, including commercially, provided
you give appropriate credit. The full legal code is in `LICENSE`.

## Publishing

Releases are archived on [Zenodo](https://zenodo.org) via its GitHub integration
so that each tagged release receives a citable DOI.

1. Ensure the repository is **public** on GitHub and `main` is pushed and
   CI-green.
2. Enable the repository at
   <https://zenodo.org/account/settings/github/> (toggle it **ON**) **before**
   creating the release.
3. Tag and publish a release:

   ```bash
   git tag -a v1.0.0 -m "First public release"
   git push origin v1.0.0
   gh release create v1.0.0 --title "v1.0.0" --notes "First public release."
   ```

4. Zenodo mints a **concept DOI** (always-latest) and a **version DOI** for the
   release. Add the concept DOI badge after the record exists, and use the
   version DOI for versioned citations. On the Zenodo record, link the
   affiliation to its **ROR** and attach the author **ORCID**.

Keep the version in `pyproject.toml` and `CITATION.cff` in sync, and record
user-visible changes in `CHANGELOG.md`. The repeatable checklist lives in
`docs/release_process.md`.
