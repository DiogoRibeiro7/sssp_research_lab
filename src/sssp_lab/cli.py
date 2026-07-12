"""Command-line helpers."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dial import dial_circular_sssp, dial_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph, PathResult
from sssp_lab.utils import assert_same_distances, make_random_graph

Algorithm = Callable[[Graph, int, OperationStats], PathResult]


def timed(name: str, runner: Algorithm, graph: Graph, source: int) -> dict[str, object]:
    """Run one algorithm and return timing metadata."""

    stats = OperationStats()
    start = time.perf_counter()
    result = runner(graph, source, stats)
    seconds = time.perf_counter() - start
    return {
        "algorithm": name,
        "seconds": seconds,
        "reachable": sum(distance < float("inf") for distance in result.distances.values()),
        "result": result,
        **stats.as_dict(),
    }


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown summary table next to exported benchmark data."""

    lines = [
        "| algorithm | seconds | reachable | relaxations | queue pops | bucket insertions |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {algorithm} | {seconds:.6f} | {reachable} | {relaxations} | {queue_pops} | "
            "{bucket_insertions} |".format(
                algorithm=cast(str, row["algorithm"]),
                seconds=cast(float, row["seconds"]),
                reachable=cast(int, row["reachable"]),
                relaxations=cast(int, row["relaxations"]),
                queue_pops=cast(int, row["queue_pops"]),
                bucket_insertions=cast(int, row["bucket_insertions"]),
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_exports(rows: list[dict[str, object]], output: Path) -> None:
    """Write JSON, CSV, and markdown benchmark artifacts."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    csv_output = output.with_suffix(".csv")
    with csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_markdown_summary(rows, output.with_suffix(".md"))


def main() -> None:
    """Run a small benchmark from the command line."""

    parser = argparse.ArgumentParser(description="Benchmark SSSP algorithms.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-weight", type=int, default=1)
    parser.add_argument("--max-weight", type=int, default=20)
    parser.add_argument("--delta", type=float, default=5.0)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. CSV and markdown summaries use the same base path.",
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

    algorithms: dict[str, Algorithm] = {
        "binary_heap_dijkstra": lambda g, s, stats: dijkstra(g, s, stats=stats),
        "dial": lambda g, s, stats: dial_sssp(g, s, stats=stats),
        "dial_circular": lambda g, s, stats: dial_circular_sssp(g, s, stats=stats),
        "radix_heap": lambda g, s, stats: dijkstra_radix_heap(g, s, stats=stats),
        f"delta_stepping_delta_{args.delta:g}": lambda g, s, stats: delta_stepping(
            g,
            s,
            delta=args.delta,
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

    for row in sorted(rows, key=lambda item: cast(float, item["seconds"])):
        print(f"{cast(str, row['algorithm'])}: {cast(float, row['seconds']):.6f}s")

    if args.output is not None:
        write_exports(rows, args.output)
        print(f"Wrote {args.output}")
        print(f"Wrote {args.output.with_suffix('.csv')}")
        print(f"Wrote {args.output.with_suffix('.md')}")


if __name__ == "__main__":
    main()
