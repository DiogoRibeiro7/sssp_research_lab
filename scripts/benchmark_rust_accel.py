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
    dijkstra_rust,
    dijkstra_rust_csr,
    graph_to_csr,
    rust_backend_available,
)
from sssp_lab.graph import Graph, PathResult  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402

Runner = Callable[[Graph, int], PathResult]
CSRRunner = Callable[[CSRGraph, int], PathResult]


def timed(name: str, backend: str, runner: Runner, graph: Graph, source: int) -> dict[str, object]:
    """Run one implementation and return timing metadata."""

    start = time.perf_counter()
    result = runner(graph, source)
    seconds = time.perf_counter() - start
    return {
        "algorithm": name,
        "backend": backend,
        "seconds": seconds,
        "reachable": sum(distance < float("inf") for distance in result.distances.values()),
        "result": result,
    }


def timed_csr(
    name: str,
    backend: str,
    runner: CSRRunner,
    csr: CSRGraph,
    source: int,
) -> dict[str, object]:
    """Run one implementation against a prebuilt CSR graph."""

    start = time.perf_counter()
    result = runner(csr, source)
    seconds = time.perf_counter() - start
    return {
        "algorithm": name,
        "backend": backend,
        "seconds": seconds,
        "reachable": sum(distance < float("inf") for distance in result.distances.values()),
        "result": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark optional Rust acceleration kernels.")
    parser.add_argument("--nodes", type=int, default=5000)
    parser.add_argument("--edges", type=int, default=25000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-weight", type=int, default=1)
    parser.add_argument("--max-weight", type=int, default=50)
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

    rows: list[dict[str, object]] = [
        timed("dijkstra", "python", dijkstra, graph, 0),
        timed("dial_circular", "python", dial_circular_sssp, graph, 0),
    ]
    reference = rows[0]["result"]
    if not isinstance(reference, PathResult):
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
                "reachable": len(csr.nodes),
                "result": reference,
            }
        )
        rows.extend(
            [
                timed("dijkstra", "rust", dijkstra_rust, graph, 0),
                timed("dial_circular", "rust", dial_circular_rust, graph, 0),
                timed_csr("dijkstra_csr_reused", "rust", dijkstra_rust_csr, csr, 0),
                timed_csr("dial_circular_csr_reused", "rust", dial_circular_rust_csr, csr, 0),
            ]
        )
    elif args.require_rust:
        raise RuntimeError("Rust backend is not installed")

    serializable_rows: list[dict[str, object]] = []
    for row in rows:
        result = row.pop("result")
        if not isinstance(result, PathResult):
            raise TypeError("runner returned unexpected result type")
        assert_same_distances(result.distances, reference.distances)
        serializable_rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(serializable_rows, indent=2), encoding="utf-8")
    csv_output = args.output.with_suffix(".csv")
    with csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serializable_rows[0]))
        writer.writeheader()
        writer.writerows(serializable_rows)

    print(f"Wrote {args.output}")
    print(f"Wrote {csv_output}")
    if not rust_backend_available():
        print("Rust backend is not installed; wrote Python-only comparison rows.")


if __name__ == "__main__":
    main()
