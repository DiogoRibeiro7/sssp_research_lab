#!/usr/bin/env python
"""Benchmark ALT queries against Dijkstra point-to-point lookups."""

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

from sssp_lab.algorithms.alt import (  # noqa: E402
    ALTQueryStats,
    alt_query,
    avoid_landmarks,
    build_alt_index,
    farthest_first_landmarks,
    high_degree_landmarks,
    random_landmarks,
)
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.graph import Graph  # noqa: E402
from sssp_lab.utils import make_random_graph  # noqa: E402


def select_landmarks(graph: Graph, *, strategy: str, count: int, seed: int) -> tuple[int, ...]:
    """Select ALT landmarks for one benchmark strategy."""

    if strategy == "random":
        return random_landmarks(graph, count=count, seed=seed)
    if strategy == "high-degree":
        return high_degree_landmarks(graph, count=count)
    if strategy == "farthest":
        return farthest_first_landmarks(graph, count=count)
    if strategy == "avoid":
        return avoid_landmarks(graph, count=count)
    raise ValueError(f"unknown landmark strategy: {strategy}")


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown table for ALT benchmark rows."""

    lines = [
        "| strategy | source | target | dijkstra seconds | alt seconds | heap pops | settled |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {landmark_strategy} | {source} | {target} | {dijkstra_seconds:.6f} | "
            "{alt_seconds:.6f} | {alt_heap_pops} | {alt_settled_nodes} |".format(
                landmark_strategy=row["landmark_strategy"],
                source=row["source"],
                target=row["target"],
                dijkstra_seconds=float(row["dijkstra_seconds"]),
                alt_seconds=float(row["alt_seconds"]),
                alt_heap_pops=row["alt_heap_pops"],
                alt_settled_nodes=row["alt_settled_nodes"],
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ALT and Dijkstra queries.")
    parser.add_argument("--nodes", type=int, default=500)
    parser.add_argument("--edges", type=int, default=2500)
    parser.add_argument("--pairs", type=int, default=25)
    parser.add_argument("--landmarks", type=int, default=4)
    parser.add_argument(
        "--strategy",
        choices=["random", "high-degree", "farthest", "avoid"],
        default="random",
        help="Landmark selection strategy.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/alt.json"))
    args = parser.parse_args()

    graph: Graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=1,
        max_weight=20,
        seed=args.seed,
    )
    nodes = sorted(graph.nodes)
    pairs = [(nodes[i % len(nodes)], nodes[-(i % len(nodes))-1]) for i in range(args.pairs)]
    landmarks = select_landmarks(
        graph,
        strategy=args.strategy,
        count=args.landmarks,
        seed=args.seed,
    )
    index = build_alt_index(graph, landmarks)

    rows: list[dict[str, object]] = []
    for source, target in pairs:
        start = time.perf_counter()
        reference = dijkstra(graph, source)
        dijkstra_seconds = time.perf_counter() - start
        stats = ALTQueryStats()
        distance, _ = alt_query(graph, source, target, index, stats=stats)
        if distance != reference.distances[target]:
            raise AssertionError(f"distance mismatch for pair {(source, target)}")
        rows.append(
            {
                "landmark_strategy": args.strategy,
                "landmarks": ",".join(str(landmark) for landmark in landmarks),
                "source": source,
                "target": target,
                "dijkstra_seconds": dijkstra_seconds,
                "alt_seconds": stats.seconds,
                "alt_heap_pops": stats.heap_pops,
                "alt_settled_nodes": stats.settled_nodes,
                "alt_heuristic_evaluations": stats.heuristic_evaluations,
            }
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
