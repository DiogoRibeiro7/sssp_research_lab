#!/usr/bin/env python
"""Benchmark selected SSSP algorithms on a random graph."""

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

from sssp_lab.algorithms.delta_stepping import delta_stepping  # noqa: E402
from sssp_lab.algorithms.dial import dial_sssp  # noqa: E402
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap  # noqa: E402
from sssp_lab.graph import Graph, PathResult  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402

Algorithm = Callable[[Graph, int], PathResult]


def timed(name: str, runner: Algorithm, graph: Graph, source: int) -> dict[str, object]:
    """Run one algorithm and return timing metadata."""

    start = time.perf_counter()
    result = runner(graph, source)
    elapsed = time.perf_counter() - start
    reachable = sum(distance < float("inf") for distance in result.distances.values())
    return {"algorithm": name, "seconds": elapsed, "reachable": reachable, "result": result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SSSP algorithms.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/benchmark.json"))
    args = parser.parse_args()

    graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=1,
        max_weight=20,
        seed=args.seed,
    )

    algorithms: dict[str, Algorithm] = {
        "binary_heap_dijkstra": dijkstra,
        "dial": dial_sssp,
        "radix_heap": dijkstra_radix_heap,
        "delta_stepping_delta_5": lambda g, s: delta_stepping(g, s, delta=5.0),
    }

    rows: list[dict[str, object]] = []
    reference: PathResult | None = None
    for name, runner in algorithms.items():
        row = timed(name, runner, graph, 0)
        result = row.pop("result")
        if not isinstance(result, PathResult):
            raise TypeError("runner returned unexpected result type")
        if reference is None:
            reference = result
        else:
            assert_same_distances(result.distances, reference.distances)
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    csv_output = args.output.with_suffix(".csv")
    with csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["algorithm", "seconds", "reachable"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {args.output}")
    print(f"Wrote {csv_output}")


if __name__ == "__main__":
    main()
