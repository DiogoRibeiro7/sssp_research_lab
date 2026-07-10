#!/usr/bin/env python
"""Benchmark engineering Δ policies for the generic stepping engine."""

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

from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.stepping_variants import (  # noqa: E402
    DeltaPolicy,
    adaptive_bucket_delta,
    degree_adjusted_delta,
    mean_weight_delta,
    median_weight_delta,
    percentile_weight_delta,
    run_stepping_policy,
    trimmed_mean_weight_delta,
)
from sssp_lab.graph import Graph  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402

GraphFactory = Callable[[int, int, int], Graph]


def equal_weight_graph(nodes: int, edges: int, seed: int) -> Graph:
    """Return a graph family where most policies choose similar Δ values."""

    return make_random_graph(
        nodes=nodes,
        edges=edges,
        directed=True,
        min_weight=5,
        max_weight=5,
        seed=seed,
    )


def wide_weight_graph(nodes: int, edges: int, seed: int) -> Graph:
    """Return a graph family where high-percentile Δ can create large buckets."""

    return make_random_graph(
        nodes=nodes,
        edges=edges,
        directed=True,
        min_weight=1,
        max_weight=1000,
        seed=seed,
    )


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown summary table for policy comparisons."""

    lines = [
        "| graph family | policy | delta | seconds | relaxations | bucket phases | max bucket size |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {graph_family} | {policy} | {delta:.6f} | {seconds:.6f} | "
            "{relaxations} | {bucket_phases} | {max_bucket_size} |".format(
                graph_family=row["graph_family"],
                policy=row["policy"],
                delta=float(row["delta"]),
                seconds=float(row["seconds"]),
                relaxations=row["relaxations"],
                bucket_phases=row["bucket_phases"],
                max_bucket_size=row["max_bucket_size"],
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare stepping Δ policies.")
    parser.add_argument("--nodes", type=int, default=500)
    parser.add_argument("--edges", type=int, default=2500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/stepping_policies.json"))
    args = parser.parse_args()

    families: dict[str, GraphFactory] = {
        "equal_weights": equal_weight_graph,
        "wide_integer_weights": wide_weight_graph,
    }
    policies: dict[str, DeltaPolicy] = {
        "median": median_weight_delta,
        "mean": mean_weight_delta,
        "trimmed_mean_10": trimmed_mean_weight_delta(0.10),
        "p90": percentile_weight_delta(90),
        "degree_adjusted": degree_adjusted_delta,
        "adaptive": adaptive_bucket_delta,
    }

    rows: list[dict[str, object]] = []
    for family_name, factory in families.items():
        graph = factory(args.nodes, args.edges, args.seed)
        reference = dijkstra(graph, 0)
        for policy_name, policy in policies.items():
            start = time.perf_counter()
            run = run_stepping_policy(graph, 0, policy_name=policy_name, delta_policy=policy)
            seconds = time.perf_counter() - start
            assert_same_distances(run.result.distances, reference.distances)
            rows.append(
                {
                    "policy": run.policy_name,
                    "graph_family": family_name,
                    "seed": args.seed,
                    "delta": run.delta,
                    "seconds": seconds,
                    **run.stats.as_dict(),
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
