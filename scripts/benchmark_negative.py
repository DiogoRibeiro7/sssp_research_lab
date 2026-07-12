#!/usr/bin/env python
"""Benchmark negative-weight SSSP baselines on deterministic DAGs."""

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

from sssp_lab.algorithms.bellman_ford import bellman_ford  # noqa: E402
from sssp_lab.algorithms.negative_weight import (  # noqa: E402
    johnson_sssp,
    negative_decomposition_experiment,
)
from sssp_lab.algorithms.stats import OperationStats  # noqa: E402
from sssp_lab.graph import PathResult  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_negative_dag  # noqa: E402


def _reachable(result: PathResult) -> int:
    return sum(distance < float("inf") for distance in result.distances.values())


def _row(
    *,
    algorithm: str,
    seconds: float,
    result: PathResult,
    stats: OperationStats,
    negative_edges: int = 0,
    scale_rounds: int = 0,
    sampled_vertices: int = 0,
) -> dict[str, object]:
    return {
        "algorithm": algorithm,
        "seconds": seconds,
        "reachable": _reachable(result),
        "negative_edges": negative_edges,
        "scale_rounds": scale_rounds,
        "sampled_vertices": sampled_vertices,
        **stats.as_dict(),
    }


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown table for negative-weight benchmark rows."""

    lines = [
        "| algorithm | seconds | reachable | negative edges | relaxations | queue pops | scale rounds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {algorithm} | {seconds:.6f} | {reachable} | {negative_edges} | "
            "{relaxations} | {queue_pops} | {scale_rounds} |".format(**row)
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare negative-weight SSSP baselines.")
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--edges", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--sample-probability", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/negative.json"))
    args = parser.parse_args()

    graph = make_negative_dag(nodes=args.nodes, edges=args.edges, seed=args.seed)

    rows: list[dict[str, object]] = []

    reference_stats = OperationStats()
    start = time.perf_counter()
    reference = bellman_ford(graph, 0, stats=reference_stats)
    rows.append(
        _row(
            algorithm="bellman_ford",
            seconds=time.perf_counter() - start,
            result=reference,
            stats=reference_stats,
        )
    )

    johnson_stats = OperationStats()
    start = time.perf_counter()
    johnson = johnson_sssp(graph, 0, stats=johnson_stats)
    assert_same_distances(johnson.distances, reference.distances)
    rows.append(
        _row(
            algorithm="johnson",
            seconds=time.perf_counter() - start,
            result=johnson,
            stats=johnson_stats,
        )
    )

    decomposition_stats = OperationStats()
    start = time.perf_counter()
    decomposition = negative_decomposition_experiment(
        graph,
        0,
        scale=args.scale,
        sample_probability=args.sample_probability,
        seed=args.seed,
        stats=decomposition_stats,
    )
    assert_same_distances(decomposition.result.distances, reference.distances)
    rows.append(
        _row(
            algorithm="negative_decomposition",
            seconds=time.perf_counter() - start,
            result=decomposition.result,
            stats=decomposition_stats,
            negative_edges=len(decomposition.sign_decomposition.negative_edges),
            scale_rounds=len(decomposition.rounds),
            sampled_vertices=sum(len(round.sampled_vertices) for round in decomposition.rounds),
        )
    )

    negative_edge_count = rows[-1]["negative_edges"]
    for row in rows[:-1]:
        row["negative_edges"] = negative_edge_count

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
