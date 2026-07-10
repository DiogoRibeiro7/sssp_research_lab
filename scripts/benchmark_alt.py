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
    build_alt_index,
    random_landmarks,
)
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.graph import Graph  # noqa: E402
from sssp_lab.utils import make_random_graph  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ALT and Dijkstra queries.")
    parser.add_argument("--nodes", type=int, default=500)
    parser.add_argument("--edges", type=int, default=2500)
    parser.add_argument("--pairs", type=int, default=25)
    parser.add_argument("--landmarks", type=int, default=4)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/alt.json"))
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
    index = build_alt_index(graph, random_landmarks(graph, count=args.landmarks, seed=args.seed))

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
    print(f"Wrote {args.output}")
    print(f"Wrote {csv_output}")


if __name__ == "__main__":
    main()
