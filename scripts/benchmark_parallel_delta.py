#!/usr/bin/env python
"""Benchmark repeated-source Δ-stepping with sequential and pool execution."""

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

from sssp_lab.algorithms.delta_stepping import (  # noqa: E402
    DeltaSteppingRun,
    delta_stepping,
    parallel_delta_stepping,
)
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.stats import OperationStats  # noqa: E402
from sssp_lab.graph import Graph  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402


def select_sources(graph: Graph, count: int) -> tuple[int, ...]:
    """Select deterministic source nodes for repeated-source benchmarks."""

    if count <= 0:
        raise ValueError("sources must be positive")
    nodes = tuple(sorted(graph.nodes))
    if count > len(nodes):
        raise ValueError("sources must not exceed number of graph nodes")
    return nodes[:count]


def sequential_delta_stepping(graph: Graph, sources: tuple[int, ...], delta: float) -> list[DeltaSteppingRun]:
    """Run repeated-source Δ-stepping sequentially with per-source counters."""

    runs: list[DeltaSteppingRun] = []
    for source in sources:
        stats = OperationStats()
        result = delta_stepping(graph, source, delta=delta, stats=stats)
        runs.append(DeltaSteppingRun(source=source, result=result, stats=stats))
    return runs


def timed_run(
    mode: str,
    graph: Graph,
    sources: tuple[int, ...],
    *,
    delta: float,
    workers: int,
) -> dict[str, object]:
    """Run one repeated-source mode and return benchmark metadata."""

    start = time.perf_counter()
    if mode == "sequential":
        runs = sequential_delta_stepping(graph, sources, delta)
    else:
        runs = parallel_delta_stepping(
            graph,
            sources,
            delta=delta,
            backend=mode,
            max_workers=workers,
        )
    seconds = time.perf_counter() - start
    return {
        "mode": mode,
        "workers": 1 if mode == "sequential" else workers,
        "seconds": seconds,
        "source_count": len(sources),
        "seconds_per_source": seconds / len(sources),
        "reachable": sum(
            distance < float("inf")
            for run in runs
            for distance in run.result.distances.values()
        ),
        "relaxations": sum(run.stats.relaxations for run in runs),
        "bucket_phases": sum(run.stats.bucket_phases for run in runs),
        "max_bucket_size": max((run.stats.max_bucket_size for run in runs), default=0),
        "runs": runs,
    }


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown summary table."""

    lines = [
        "| mode | workers | sources | seconds | seconds/source | relaxations | bucket phases |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {mode} | {workers} | {source_count} | {seconds:.6f} | "
            "{seconds_per_source:.6f} | {relaxations} | {bucket_phases} |".format(
                mode=row["mode"],
                workers=row["workers"],
                source_count=row["source_count"],
                seconds=float(row["seconds"]),
                seconds_per_source=float(row["seconds_per_source"]),
                relaxations=row["relaxations"],
                bucket_phases=row["bucket_phases"],
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_runs(
    rows: list[dict[str, object]],
    references: list[DeltaSteppingRun],
) -> list[dict[str, object]]:
    """Validate benchmark rows and remove non-serializable run objects."""

    serializable: list[dict[str, object]] = []
    for row in rows:
        runs = row.pop("runs")
        if not isinstance(runs, list) or not all(isinstance(run, DeltaSteppingRun) for run in runs):
            raise TypeError("runner returned unexpected result type")
        if len(runs) != len(references):
            raise AssertionError("runner returned an unexpected number of runs")
        for run, reference in zip(runs, references, strict=True):
            assert run.source == reference.source
            assert_same_distances(run.result.distances, reference.result.distances)
        serializable.append(row)
    return serializable


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark repeated-source Δ-stepping pools.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--sources", type=int, default=8)
    parser.add_argument("--delta", type=float, default=5.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--modes",
        default="sequential,thread,process",
        help="Comma-separated modes: sequential,thread,process.",
    )
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/parallel_delta.json"))
    args = parser.parse_args()

    modes = tuple(mode.strip() for mode in args.modes.split(",") if mode.strip())
    invalid_modes = set(modes) - {"sequential", "thread", "process"}
    if invalid_modes:
        raise ValueError(f"unknown modes: {sorted(invalid_modes)}")
    if not modes:
        raise ValueError("at least one mode is required")
    if args.workers <= 0:
        raise ValueError("workers must be positive")

    graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=1,
        max_weight=20,
        seed=args.seed,
    )
    sources = select_sources(graph, args.sources)
    for source in sources:
        reference = dijkstra(graph, source)
        delta_result = delta_stepping(graph, source, delta=args.delta)
        assert_same_distances(delta_result.distances, reference.distances)

    rows = [
        timed_run(mode, graph, sources, delta=args.delta, workers=args.workers)
        for mode in modes
    ]
    reference_runs_raw = rows[0]["runs"]
    if not isinstance(reference_runs_raw, list) or not all(
        isinstance(run, DeltaSteppingRun) for run in reference_runs_raw
    ):
        raise TypeError("runner returned unexpected result type")
    serializable_rows = validate_runs(rows, reference_runs_raw)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(serializable_rows, indent=2), encoding="utf-8")
    csv_output = args.output.with_suffix(".csv")
    with csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serializable_rows[0]))
        writer.writeheader()
        writer.writerows(serializable_rows)
    markdown_output = args.output.with_suffix(".md")
    write_markdown_summary(serializable_rows, markdown_output)

    print(f"Wrote {args.output}")
    print(f"Wrote {csv_output}")
    print(f"Wrote {markdown_output}")


if __name__ == "__main__":
    main()
