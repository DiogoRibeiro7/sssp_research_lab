#!/usr/bin/env python
"""Compare Python SSSP implementations with optional Rust kernels."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sssp_lab.algorithms.dial import dial_circular_sssp  # noqa: E402
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.rust_accel import (  # noqa: E402
    CSRGraph,
    dial_circular_rust,
    dial_circular_rust_csr,
    dial_circular_rust_csr_many,
    dijkstra_rust,
    dijkstra_rust_csr,
    dijkstra_rust_csr_many,
    graph_to_csr,
    rust_backend_available,
)
from sssp_lab.graph import Graph, PathResult  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402

Runner = Callable[[Graph, int], PathResult]
CSRRunner = Callable[[CSRGraph, int], PathResult]
CSRBatchRunner = Callable[[CSRGraph, tuple[int, ...]], list[PathResult]]


def python_baseline_name(algorithm: str) -> str | None:
    """Map a benchmark row to the comparable Python baseline algorithm."""

    if algorithm.startswith("dijkstra"):
        return "dijkstra"
    if algorithm.startswith("dial_circular"):
        return "dial_circular"
    return None


def add_speedups(rows: list[dict[str, object]]) -> None:
    """Add speedup relative to matching Python baseline rows in place."""

    baselines = {
        str(row["algorithm"]): float(row["seconds"])
        for row in rows
        if row["backend"] == "python" and row["algorithm"] in {"dijkstra", "dial_circular"}
    }
    for row in rows:
        baseline_name = python_baseline_name(str(row["algorithm"]))
        baseline = baselines.get(baseline_name or "")
        if row["backend"] == "python" or baseline is None:
            row["speedup_vs_python"] = ""
        else:
            row["speedup_vs_python"] = baseline / float(row["seconds"])


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown benchmark summary."""

    lines = [
        "| algorithm | backend | sources | seconds | seconds/source | speedup vs python |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        speedup = row["speedup_vs_python"]
        speedup_text = "" if speedup == "" else f"{float(speedup):.2f}x"
        lines.append(
            "| {algorithm} | {backend} | {source_count} | {seconds:.6f} | "
            "{seconds_per_source:.6f} | {speedup} |".format(
                algorithm=row["algorithm"],
                backend=row["backend"],
                source_count=row["source_count"],
                seconds=float(row["seconds"]),
                seconds_per_source=float(row["seconds_per_source"]),
                speedup=speedup_text,
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def select_sources(graph: Graph, count: int) -> tuple[int, ...]:
    """Select deterministic source nodes for repeated-query benchmarks."""

    if count <= 0:
        raise ValueError("sources must be positive")
    nodes = tuple(sorted(graph.nodes))
    if count > len(nodes):
        raise ValueError("sources must not exceed number of graph nodes")
    return nodes[:count]


def timed_many(
    name: str,
    backend: str,
    runner: Runner,
    graph: Graph,
    sources: tuple[int, ...],
) -> dict[str, object]:
    """Run one implementation for several sources and return timing metadata."""

    results: list[PathResult] = []
    start = time.perf_counter()
    for source in sources:
        results.append(runner(graph, source))
    seconds = time.perf_counter() - start
    return {
        "algorithm": name,
        "backend": backend,
        "seconds": seconds,
        "source_count": len(sources),
        "seconds_per_source": seconds / len(sources),
        "reachable": sum(
            distance < float("inf")
            for result in results
            for distance in result.distances.values()
        ),
        "result": results,
    }


def timed_csr_many(
    name: str,
    backend: str,
    runner: CSRRunner,
    csr: CSRGraph,
    sources: tuple[int, ...],
) -> dict[str, object]:
    """Run one implementation against a prebuilt CSR graph for several sources."""

    results: list[PathResult] = []
    start = time.perf_counter()
    for source in sources:
        results.append(runner(csr, source))
    seconds = time.perf_counter() - start
    return {
        "algorithm": name,
        "backend": backend,
        "seconds": seconds,
        "source_count": len(sources),
        "seconds_per_source": seconds / len(sources),
        "reachable": sum(
            distance < float("inf")
            for result in results
            for distance in result.distances.values()
        ),
        "result": results,
    }


def timed_csr_batch(
    name: str,
    backend: str,
    runner: CSRBatchRunner,
    csr: CSRGraph,
    sources: tuple[int, ...],
) -> dict[str, object]:
    """Run one batched implementation against a prebuilt CSR graph."""

    start = time.perf_counter()
    results = runner(csr, sources)
    seconds = time.perf_counter() - start
    return {
        "algorithm": name,
        "backend": backend,
        "seconds": seconds,
        "source_count": len(sources),
        "seconds_per_source": seconds / len(sources),
        "reachable": sum(
            distance < float("inf")
            for result in results
            for distance in result.distances.values()
        ),
        "result": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark optional Rust acceleration kernels.")
    parser.add_argument("--nodes", type=int, default=5000)
    parser.add_argument("--edges", type=int, default=25000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-weight", type=int, default=1)
    parser.add_argument("--max-weight", type=int, default=50)
    parser.add_argument("--sources", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/rust_accel.json"))
    parser.add_argument(
        "--require-rust",
        action="store_true",
        help="Fail instead of writing Python-only rows when the Rust extension is absent.",
    )
    args = parser.parse_args()

    graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=args.min_weight,
        max_weight=args.max_weight,
        seed=args.seed,
    )
    sources = select_sources(graph, args.sources)

    rows: list[dict[str, object]] = [
        timed_many("dijkstra", "python", dijkstra, graph, sources),
        timed_many("dial_circular", "python", dial_circular_sssp, graph, sources),
    ]
    reference_results = rows[0]["result"]
    if not isinstance(reference_results, list) or not all(
        isinstance(result, PathResult) for result in reference_results
    ):
        raise TypeError("runner returned unexpected result type")

    if rust_backend_available():
        conversion_start = time.perf_counter()
        csr = graph_to_csr(graph)
        conversion_seconds = time.perf_counter() - conversion_start
        rows.append(
            {
                "algorithm": "csr_conversion",
                "backend": "python",
                "seconds": conversion_seconds,
                "source_count": len(sources),
                "seconds_per_source": conversion_seconds / len(sources),
                "reachable": len(csr.nodes),
                "result": reference_results,
            }
        )
        rows.extend(
            [
                timed_many("dijkstra", "rust", dijkstra_rust, graph, sources),
                timed_many("dial_circular", "rust", dial_circular_rust, graph, sources),
                timed_csr_many("dijkstra_csr_reused", "rust", dijkstra_rust_csr, csr, sources),
                timed_csr_many(
                    "dial_circular_csr_reused",
                    "rust",
                    dial_circular_rust_csr,
                    csr,
                    sources,
                ),
                timed_csr_batch("dijkstra_csr_batch", "rust", dijkstra_rust_csr_many, csr, sources),
                timed_csr_batch(
                    "dial_circular_csr_batch",
                    "rust",
                    dial_circular_rust_csr_many,
                    csr,
                    sources,
                ),
            ]
        )
    elif args.require_rust:
        raise RuntimeError("Rust backend is not installed")

    serializable_rows: list[dict[str, object]] = []
    for row in rows:
        results = row.pop("result")
        if not isinstance(results, list) or not all(
            isinstance(result, PathResult) for result in results
        ):
            raise TypeError("runner returned unexpected result type")
        if len(results) != len(reference_results):
            raise AssertionError("runner returned an unexpected number of results")
        for result, reference in zip(results, reference_results, strict=True):
            assert_same_distances(result.distances, reference.distances)
        serializable_rows.append(row)
    add_speedups(serializable_rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(serializable_rows, indent=2), encoding="utf-8")
    csv_output = args.output.with_suffix(".csv")
    with csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serializable_rows[0]))
        writer.writeheader()
        writer.writerows(serializable_rows)
    markdown_output = args.output.with_suffix(".md")
    write_markdown_summary(serializable_rows, markdown_output)

    print(f"Wrote {args.output}")
    print(f"Wrote {csv_output}")
    print(f"Wrote {markdown_output}")
    if not rust_backend_available():
        print("Rust backend is not installed; wrote Python-only comparison rows.")


if __name__ == "__main__":
    main()
