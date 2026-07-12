#!/usr/bin/env python
"""Benchmark Thorup-like integer SSSP scaffolding."""

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

from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.stats import OperationStats  # noqa: E402
from sssp_lab.algorithms.thorup_like import (  # noqa: E402
    build_component_hierarchy,
    build_distance_scale_buckets,
    thorup_integer_baseline,
)
from sssp_lab.graph import PathResult  # noqa: E402
from sssp_lab.utils import (  # noqa: E402
    assert_same_distances,
    make_random_graph,
    make_road_like_graph,
)


def make_graph(*, graph_family: str, nodes: int, edges: int, seed: int):
    """Construct a deterministic undirected positive-integer graph."""

    if graph_family == "random":
        return make_random_graph(
            nodes=nodes,
            edges=edges,
            directed=False,
            min_weight=1,
            max_weight=100,
            seed=seed,
        )
    if graph_family == "road_like":
        width = max(2, int(nodes**0.5))
        height = max(2, (nodes + width - 1) // width)
        return make_road_like_graph(width=width, height=height, seed=seed)
    raise ValueError(f"unknown graph family: {graph_family}")


def _reachable(result: PathResult) -> int:
    return sum(distance < float("inf") for distance in result.distances.values())


def _component_count(levels: tuple[tuple[object, ...], ...]) -> int:
    return sum(len(level) for level in levels)


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown table for Thorup-like benchmark rows."""

    lines = [
        "| algorithm | seconds | reachable | relaxations | hierarchy seconds | levels | components | buckets |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {algorithm} | {seconds:.6f} | {reachable} | {relaxations} | "
            "{hierarchy_seconds:.6f} | {hierarchy_levels} | {component_count} | "
            "{distance_buckets} |".format(**row)
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Thorup-like integer SSSP helpers.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=3000)
    parser.add_argument(
        "--graph-family",
        choices=["random", "road_like"],
        default="random",
        help="Undirected positive-integer graph family to benchmark.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--bucket-scale", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/thorup.json"))
    args = parser.parse_args()

    graph = make_graph(
        graph_family=args.graph_family,
        nodes=args.nodes,
        edges=args.edges,
        seed=args.seed,
    )

    hierarchy_start = time.perf_counter()
    hierarchy = build_component_hierarchy(graph)
    hierarchy_seconds = time.perf_counter() - hierarchy_start

    reference_stats = OperationStats()
    start = time.perf_counter()
    reference = dijkstra(graph, 0, stats=reference_stats)
    dijkstra_seconds = time.perf_counter() - start

    baseline_stats = OperationStats()
    start = time.perf_counter()
    baseline = thorup_integer_baseline(graph, 0, stats=baseline_stats)
    baseline_seconds = time.perf_counter() - start
    assert_same_distances(baseline.distances, reference.distances)

    buckets = build_distance_scale_buckets(baseline, scale=args.bucket_scale)
    hierarchy_levels = len(hierarchy.levels)
    component_count = _component_count(hierarchy.levels)

    rows: list[dict[str, object]] = [
        {
            "algorithm": "binary_heap_dijkstra",
            "seconds": dijkstra_seconds,
            "reachable": _reachable(reference),
            "hierarchy_seconds": hierarchy_seconds,
            "hierarchy_levels": hierarchy_levels,
            "component_count": component_count,
            "distance_buckets": len(buckets),
            **reference_stats.as_dict(),
        },
        {
            "algorithm": "thorup_integer_baseline",
            "seconds": baseline_seconds,
            "reachable": _reachable(baseline),
            "hierarchy_seconds": hierarchy_seconds,
            "hierarchy_levels": hierarchy_levels,
            "component_count": component_count,
            "distance_buckets": len(buckets),
            **baseline_stats.as_dict(),
        },
    ]

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
