#!/usr/bin/env python
"""Benchmark frontier-partition SSSP against comparison algorithms."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sssp_lab.algorithms.bmssp import bounded_multi_source_sssp  # noqa: E402
from sssp_lab.algorithms.delta_stepping import delta_stepping  # noqa: E402
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.frontier_sssp import FrontierStats, frontier_partition_sssp  # noqa: E402
from sssp_lab.algorithms.stats import OperationStats  # noqa: E402
from sssp_lab.graph import Graph, PathResult  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402


def _reachable(result: PathResult) -> int:
    return sum(distance < float("inf") for distance in result.distances.values())


def _frontier_summary(frontier_stats: FrontierStats | None) -> dict[str, int]:
    if frontier_stats is None:
        return {
            "rounds": 0,
            "max_frontier_size": 0,
            "max_incomplete": 0,
            "max_boundary_edges": 0,
        }
    return {
        "rounds": frontier_stats.rounds,
        "max_frontier_size": max(frontier_stats.frontier_counts, default=0),
        "max_incomplete": max(frontier_stats.incomplete_counts, default=0),
        "max_boundary_edges": max(frontier_stats.boundary_edge_counts, default=0),
    }


def _row(
    *,
    algorithm: str,
    seconds: float,
    result: PathResult,
    stats: OperationStats,
    frontier_stats: FrontierStats | None = None,
) -> dict[str, object]:
    return {
        "algorithm": algorithm,
        "seconds": seconds,
        "reachable": _reachable(result),
        **stats.as_dict(),
        **_frontier_summary(frontier_stats),
    }


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown table for frontier benchmark rows."""

    lines = [
        "| algorithm | seconds | reachable | relaxations | queue pops | rounds | max frontier |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {algorithm} | {seconds:.6f} | {reachable} | {relaxations} | {queue_pops} | "
            "{rounds} | {max_frontier_size} |".format(**row)
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare frontier-partition SSSP.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--delta", type=float, default=5.0)
    parser.add_argument("--initial-bound", type=float, default=5.0)
    parser.add_argument("--growth", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/frontier.json"))
    args = parser.parse_args()

    graph: Graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=1,
        max_weight=20,
        seed=args.seed,
    )

    rows: list[dict[str, object]] = []

    dijkstra_stats = OperationStats()
    start = time.perf_counter()
    reference = dijkstra(graph, 0, stats=dijkstra_stats)
    rows.append(
        _row(
            algorithm="binary_heap_dijkstra",
            seconds=time.perf_counter() - start,
            result=reference,
            stats=dijkstra_stats,
        )
    )

    bmssp_stats = OperationStats()
    start = time.perf_counter()
    bmssp = bounded_multi_source_sssp(
        graph,
        {0},
        bound=float("inf"),
        stats=bmssp_stats,
    )
    bmssp_result = PathResult(
        source=0,
        distances=bmssp.distances,
        predecessors=bmssp.predecessors,
    )
    assert_same_distances(bmssp_result.distances, reference.distances)
    rows.append(
        _row(
            algorithm="bounded_multi_source",
            seconds=time.perf_counter() - start,
            result=bmssp_result,
            stats=bmssp_stats,
        )
    )

    delta_stats = OperationStats()
    start = time.perf_counter()
    delta = delta_stepping(graph, 0, delta=args.delta, stats=delta_stats)
    assert_same_distances(delta.distances, reference.distances)
    rows.append(
        _row(
            algorithm=f"delta_stepping_delta_{args.delta:g}",
            seconds=time.perf_counter() - start,
            result=delta,
            stats=delta_stats,
        )
    )

    frontier_operation_stats = OperationStats()
    start = time.perf_counter()
    frontier, frontier_stats = frontier_partition_sssp(
        graph,
        0,
        initial_bound=args.initial_bound,
        growth=args.growth,
        stats=frontier_operation_stats,
    )
    assert_same_distances(frontier.distances, reference.distances)
    rows.append(
        _row(
            algorithm="frontier_partition",
            seconds=time.perf_counter() - start,
            result=frontier,
            stats=frontier_operation_stats,
            frontier_stats=frontier_stats,
        )
    )

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
