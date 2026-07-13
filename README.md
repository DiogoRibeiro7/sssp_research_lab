# SSSP Research Lab

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21302832.svg)](https://doi.org/10.5281/zenodo.21302832)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

SSSP Research Lab is a Python implementation lab for single-source shortest
path algorithms, especially algorithms that try to reduce or restructure the
ordering work normally done by Dijkstra's priority queue.

The central question is:

> How much ordering does a shortest-path algorithm really need?

The repository mixes stable reference implementations, educational versions of
classic techniques, and research-frontier scaffolds. It is intentionally honest
about those boundaries: the BMSSP work here is a correctness-first experimental
implementation path, not a proof of the paper's asymptotic running time.

## Current Scope

| Module | What it contains | Status |
|---|---|---|
| `dijkstra_binary_heap.py` | Binary-heap Dijkstra | working reference |
| `dial.py` | Dial bucket Dijkstra | working, integer weights |
| `radix_heap.py`, `dijkstra_radix.py` | Radix heap and radix Dijkstra | working, integer weights |
| `delta_stepping.py` | Sequential delta-stepping | working educational implementation |
| `bellman_ford.py` | Bellman-Ford | working reference for negative edges without negative cycles |
| `alt.py` | ALT point-to-point search | working educational implementation |
| `contraction_hierarchies.py` | Contraction Hierarchies | working small-graph educational implementation |
| `bmssp.py` | Bounded multi-source SSSP, recursive scaffold, and paper-shaped BMSSP helpers | correctness-first research scaffold |
| `frontier_sssp.py` | Frontier-partition experiments | experimental |
| `thorup_like.py` | Integer SSSP lab helpers inspired by Thorup | scaffold plus radix baseline |
| `negative_weight.py` | Johnson, Bellman-Ford, and negative-weight decomposition experiments | working baselines and experiments |

See [docs/algorithm_matrix.md](docs/algorithm_matrix.md) for the compact
algorithm status matrix.

## BMSSP Status

The BMSSP module now has two layers:

- `bounded_multi_source_sssp(...)` and `recursive_bmssp(...)`: stable bounded
  primitives used by other experiments.
- `BMSSPQueue`, `find_pivots(...)`, `bmssp_base_case(...)`,
  `derive_bmssp_parameters(...)`, and `paper_bmssp(...)`: a paper-shaped,
  shared-label BMSSP driver built for correctness experiments.

The paper-shaped driver has randomized parity tests against the bounded
multi-source oracle, coverage for close labels and ties, disconnected directed
graphs, adversarial bound thresholds, derived graph-size parameters, and debug
checks for predecessor chains.

What it does not claim:

- the paper's block/list data-structure complexity,
- the constant-degree graph transformation,
- comparison-addition tie-ordering machinery,
- the claimed `O(m log^(2/3) n)` bound.

Implementation notes live in
[docs/bmssp_implementation_notes.md](docs/bmssp_implementation_notes.md).

## Install

Python 3.10 through 3.12 is supported.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

macOS/Linux:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

For development checks:

```bash
python -m pip install -e . pytest ruff mypy
python -m pytest
python -m ruff check .
python -m mypy src
```

Poetry also works:

```bash
poetry install
poetry run pytest
```

## Quick Example

```python
from sssp_lab.graph import Graph
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.delta_stepping import delta_stepping

graph = Graph.from_edges(
    [
        (0, 1, 2.0),
        (0, 2, 5.0),
        (1, 2, 1.0),
        (2, 3, 3.0),
    ],
    directed=True,
)

print(dijkstra(graph, 0).distances)
print(delta_stepping(graph, 0, delta=2.0).distances)
```

BMSSP experiment:

```python
from sssp_lab.algorithms.bmssp import derive_bmssp_parameters, paper_bmssp

parameters = derive_bmssp_parameters(graph)
labels = {node: float("inf") for node in graph.nodes}
predecessors = {node: None for node in graph.nodes}
labels[0] = 0.0

result = paper_bmssp(
    graph,
    {0},
    bound=float("inf"),
    level=parameters.max_level,
    labels=labels,
    predecessors=predecessors,
    config=parameters.to_config(),
    debug=True,
)

print(labels)
print(result.complete_vertices)
```

## Command Line

The package installs one benchmark command:

```bash
sssp-benchmark --nodes 1000 --edges 5000 --seed 7
sssp-benchmark --nodes 1000 --edges 5000 --output .benchmarks/cli_sssp.json
```

When `--output` is supplied, the command writes JSON, CSV, and markdown files
with the same base path.

## Benchmarks

Benchmark scripts live in [scripts/](scripts). They generate deterministic
graphs and write outputs under `.benchmarks/`.

Common scripts:

| Script | Purpose |
|---|---|
| `scripts/benchmark_sssp.py` | Compare core SSSP algorithms on one graph |
| `scripts/benchmark_delta_sweep.py` | Sweep delta-stepping parameters |
| `scripts/benchmark_frontier.py` | Compare frontier partitioning, BMSSP primitives, and delta-stepping |
| `scripts/benchmark_alt.py` | ALT point-to-point benchmark |
| `scripts/benchmark_ch.py` | Contraction Hierarchies point-to-point benchmark |
| `scripts/benchmark_negative.py` | Negative-weight baselines and decomposition experiments |
| `scripts/benchmark_thorup.py` | Thorup-like integer diagnostics |
| `scripts/benchmark_rust_accel.py` | Optional Rust acceleration comparison |

See [docs/benchmarking.md](docs/benchmarking.md) for metrics and file formats.

## Optional Rust Acceleration

The optional PyO3/maturin extension under `rust/sssp_accel` provides CSR-based
Dijkstra and circular Dial kernels. The Python algorithms remain the correctness
reference.

```bash
python -m pip install maturin
python scripts/build_rust_extension.py --install-source
python -m pytest tests/test_rust_accel.py
python scripts/benchmark_rust_accel.py --require-rust
```

See [docs/rust_acceleration.md](docs/rust_acceleration.md) and
[docs/packaging.md](docs/packaging.md).

## Papers And Notes

Primary paper notes and references:

- [docs/papers.md](docs/papers.md)
- [docs/bmssp_implementation_notes.md](docs/bmssp_implementation_notes.md)
- [docs/faster_directed_sssp_notes.md](docs/faster_directed_sssp_notes.md)
- [docs/benchmarking.md](docs/benchmarking.md)
- [references.bib](references.bib)

Main topics covered include BMSSP and the sorting barrier, faster directed
SSSP, delta-stepping, stepping policies, Thorup-style integer SSSP, ALT,
Contraction Hierarchies, and negative-weight SSSP baselines.

## Development

Useful checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
python -m compileall -q src
```

Release notes live in [CHANGELOG.md](CHANGELOG.md). The repeatable release
checklist lives in [docs/release_process.md](docs/release_process.md).

## Citation

If you use this repository in academic work, cite the software metadata in
[CITATION.cff](CITATION.cff). For BibTeX:

```bibtex
@software{ribeiro_sssp_research_lab_2026,
  author    = {Ribeiro, Diogo},
  title     = {{SSSP Research Lab: Implementable Shortest-Path Algorithms
               Inspired by Sorting-Barrier SSSP Research}},
  year      = {2026},
  version   = {1.0.0},
  doi       = {10.5281/zenodo.21302833},
  url       = {https://github.com/DiogoRibeiro7/sssp_research_lab}
}
```

## License

This work is licensed under the
[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
The full license text is in [LICENSE](LICENSE).
