#!/usr/bin/env python
"""Benchmark Contraction Hierarchies queries against Dijkstra."""

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

from sssp_lab.algorithms.contraction_hierarchies import (  # noqa: E402
    build_ch_index,
    ch_query,
)
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.stats import OperationStats  # noqa: E402
from sssp_lab.graph import Graph  # noqa: E402
from sssp_lab.utils import make_random_graph, make_road_like_graph  # noqa: E402


def make_graph(*, graph_family: str, nodes: int, edges: int, seed: int) -> Graph:
    """Construct a deterministic undirected graph for CH benchmarking."""

    if graph_family == "random":
        return make_random_graph(
            nodes=nodes,
            edges=edges,
            directed=False,
            min_weight=1,
            max_weight=20,
            seed=seed,
        )
    if graph_family == "road_like":
        width = max(2, int(nodes**0.5))
        height = max(2, (nodes + width - 1) // width)
        return make_road_like_graph(width=width, height=height, seed=seed)
    raise ValueError(f"unknown graph family: {graph_family}")


def select_pairs(graph: Graph, count: int) -> list[tuple[int, int]]:
    """Select deterministic source-target query pairs."""

    if count <= 0:
        raise ValueError("pairs must be positive")
    nodes = sorted(graph.nodes)
    if not nodes:
        raise ValueError("graph must contain at least one node")
    return [(nodes[i % len(nodes)], nodes[-(i % len(nodes)) - 1]) for i in range(count)]


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown table for CH benchmark rows."""

    lines = [
        "| heuristic | source | target | dijkstra seconds | ch seconds | preprocessing seconds | shortcuts | settled |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {heuristic} | {source} | {target} | {dijkstra_seconds:.6f} | "
            "{ch_seconds:.6f} | {preprocessing_seconds:.6f} | {shortcut_count} | "
            "{ch_settled_nodes} |".format(
                heuristic=row["heuristic"],
                source=row["source"],
                target=row["target"],
                dijkstra_seconds=float(row["dijkstra_seconds"]),
                ch_seconds=float(row["ch_seconds"]),
                preprocessing_seconds=float(row["preprocessing_seconds"]),
                shortcut_count=row["shortcut_count"],
                ch_settled_nodes=row["ch_settled_nodes"],
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare CH and Dijkstra point-to-point queries.")
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--edges", type=int, default=300)
    parser.add_argument("--pairs", type=int, default=10)
    parser.add_argument(
        "--graph-family",
        choices=["random", "road_like"],
        default="random",
        help="Undirected graph family to benchmark.",
    )
    parser.add_argument(
        "--heuristic",
        default="witness_edge_difference",
        help="Contraction order heuristic passed to build_ch_index.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/ch.json"))
    args = parser.parse_args()

    graph = make_graph(
        graph_family=args.graph_family,
        nodes=args.nodes,
        edges=args.edges,
        seed=args.seed,
    )
    pairs = select_pairs(graph, args.pairs)

    start = time.perf_counter()
    index = build_ch_index(graph, heuristic=args.heuristic)
    preprocessing_seconds = time.perf_counter() - start

    rows: list[dict[str, object]] = []
    for source, target in pairs:
        start = time.perf_counter()
        reference = dijkstra(graph, source)
        dijkstra_seconds = time.perf_counter() - start

        stats = OperationStats()
        start = time.perf_counter()
        distance = ch_query(index, source, target, stats=stats)
        ch_seconds = time.perf_counter() - start
        if distance != reference.distances[target]:
            raise AssertionError(f"distance mismatch for pair {(source, target)}")
        rows.append(
            {
                "graph_family": args.graph_family,
                "heuristic": args.heuristic,
                "source": source,
                "target": target,
                "dijkstra_seconds": dijkstra_seconds,
                "ch_seconds": ch_seconds,
                "preprocessing_seconds": preprocessing_seconds,
                "shortcut_count": len(index.shortcuts),
                "ch_relaxations": stats.relaxations,
                "ch_queue_pushes": stats.queue_pushes,
                "ch_queue_pops": stats.queue_pops,
                "ch_stale_pops": stats.stale_pops,
                "ch_settled_nodes": stats.settled_nodes,
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
