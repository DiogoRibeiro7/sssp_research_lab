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
from sssp_lab.algorithms.dial import dial_circular_sssp, dial_sssp  # noqa: E402
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap  # noqa: E402
from sssp_lab.algorithms.stats import OperationStats  # noqa: E402
from sssp_lab.graph import Graph, PathResult  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402

Algorithm = Callable[[Graph, int, OperationStats], PathResult]


def timed(name: str, runner: Algorithm, graph: Graph, source: int) -> dict[str, object]:
    """Run one algorithm and return timing metadata."""

    stats = OperationStats()
    start = time.perf_counter()
    result = runner(graph, source, stats)
    elapsed = time.perf_counter() - start
    reachable = sum(distance < float("inf") for distance in result.distances.values())
    return {
        "algorithm": name,
        "seconds": elapsed,
        "reachable": reachable,
        "result": result,
        **stats.as_dict(),
    }


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown summary table next to benchmark artifacts."""

    lines = [
        "| algorithm | seconds | reachable | relaxations | queue pops | bucket insertions |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {algorithm} | {seconds:.6f} | {reachable} | {relaxations} | {queue_pops} | "
            "{bucket_insertions} |".format(**row)
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SSSP algorithms.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-weight", type=int, default=1)
    parser.add_argument("--max-weight", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/benchmark.json"))
    args = parser.parse_args()

    graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=args.min_weight,
        max_weight=args.max_weight,
        seed=args.seed,
    )

    algorithms: dict[str, Algorithm] = {
        "binary_heap_dijkstra": lambda g, s, stats: dijkstra(g, s, stats=stats),
        "dial": lambda g, s, stats: dial_sssp(g, s, stats=stats),
        "dial_circular": lambda g, s, stats: dial_circular_sssp(g, s, stats=stats),
        "radix_heap": lambda g, s, stats: dijkstra_radix_heap(g, s, stats=stats),
        "delta_stepping_delta_5": lambda g, s, stats: delta_stepping(
            g,
            s,
            delta=5.0,
            stats=stats,
        ),
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
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    markdown_output = args.output.with_suffix(".md")
    write_markdown_summary(rows, markdown_output)

    print(f"Wrote {args.output}")
    print(f"Wrote {csv_output}")
    print(f"Wrote {markdown_output}")


if __name__ == "__main__":
    main()
