#!/usr/bin/env python
"""Benchmark sequential Δ-stepping over several Δ values."""

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

from sssp_lab.algorithms.delta_stepping import delta_stepping  # noqa: E402
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.stats import OperationStats  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402


def parse_deltas(raw: str) -> list[float]:
    """Parse a comma-separated list of positive Δ values."""

    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values or any(value <= 0 for value in values):
        raise ValueError("deltas must contain positive values")
    return values


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown summary table for a Δ sweep."""

    lines = [
        "| delta | seconds | reachable | relaxations | bucket phases | max bucket size |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {delta:g} | {seconds:.6f} | {reachable} | {relaxations} | "
            "{bucket_phases} | {max_bucket_size} |".format(
                delta=float(row["delta"]),
                seconds=float(row["seconds"]),
                reachable=row["reachable"],
                relaxations=row["relaxations"],
                bucket_phases=row["bucket_phases"],
                max_bucket_size=row["max_bucket_size"],
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep Δ values for sequential Δ-stepping.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--deltas", default="1,2,5,10")
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/delta_sweep.json"))
    args = parser.parse_args()

    graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=1,
        max_weight=20,
        seed=args.seed,
    )
    reference = dijkstra(graph, 0)

    rows: list[dict[str, object]] = []
    for delta in parse_deltas(args.deltas):
        stats = OperationStats()
        start = time.perf_counter()
        result = delta_stepping(graph, 0, delta=delta, stats=stats)
        seconds = time.perf_counter() - start
        assert_same_distances(result.distances, reference.distances)
        rows.append(
            {
                "algorithm": "delta_stepping",
                "delta": delta,
                "seconds": seconds,
                "reachable": sum(distance < float("inf") for distance in result.distances.values()),
                **stats.as_dict(),
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
