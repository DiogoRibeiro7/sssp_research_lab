#!/usr/bin/env python
"""Profile Python overhead around optional Rust SSSP acceleration."""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sssp_lab.algorithms.dial import dial_circular_sssp  # noqa: E402
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra  # noqa: E402
from sssp_lab.algorithms.rust_accel import (  # noqa: E402
    RustSsspWorkspace,
    dial_circular_rust,
    dijkstra_rust,
    rust_backend_available,
)
from sssp_lab.graph import Graph, PathResult  # noqa: E402
from sssp_lab.utils import assert_same_distances, make_random_graph  # noqa: E402

T = TypeVar("T")


def select_sources(graph: Graph, count: int) -> tuple[int, ...]:
    """Select deterministic source nodes for profiling."""

    if count <= 0:
        raise ValueError("sources must be positive")
    nodes = tuple(sorted(graph.nodes))
    if count > len(nodes):
        raise ValueError("sources must not exceed number of graph nodes")
    return nodes[:count]


def top_profile_entries(profile: cProfile.Profile, limit: int) -> list[dict[str, object]]:
    """Extract top cumulative-time profile entries."""

    stats = pstats.Stats(profile, stream=io.StringIO()).sort_stats("cumtime")
    entries: list[dict[str, object]] = []
    for (filename, line_number, function_name), raw in stats.stats.items():
        primitive_calls, total_calls, total_time, cumulative_time, _callers = raw
        entries.append(
            {
                "function": f"{Path(filename).name}:{line_number}:{function_name}",
                "primitive_calls": primitive_calls,
                "total_calls": total_calls,
                "total_time": total_time,
                "cumulative_time": cumulative_time,
            }
        )
    entries.sort(key=lambda entry: float(entry["cumulative_time"]), reverse=True)
    return entries[:limit]


def profiled_call(label: str, func: Callable[[], T], *, top: int) -> tuple[T, dict[str, object]]:
    """Run one callable under cProfile and return its result plus summary row."""

    profile = cProfile.Profile()
    start = time.perf_counter()
    profile.enable()
    result = func()
    profile.disable()
    seconds = time.perf_counter() - start
    return result, {
        "phase": label,
        "seconds": seconds,
        "top_cumulative": top_profile_entries(profile, top),
    }


def run_many(runner: Callable[[Graph, int], PathResult], graph: Graph, sources: tuple[int, ...]) -> list[PathResult]:
    """Run a graph-level SSSP callable for all sources."""

    return [runner(graph, source) for source in sources]


def run_prepared_many(
    runner: Callable[[int], PathResult],
    sources: tuple[int, ...],
) -> list[PathResult]:
    """Run a prepared SSSP callable for all sources."""

    return [runner(source) for source in sources]


def validate_results(
    rows: list[dict[str, object]],
    phase: str,
    results: list[PathResult],
    references: list[PathResult],
) -> None:
    """Validate profiled SSSP outputs against references and annotate a row."""

    if len(results) != len(references):
        raise AssertionError(f"{phase} returned an unexpected number of results")
    reachable = 0
    for result, reference in zip(results, references, strict=True):
        assert_same_distances(result.distances, reference.distances)
        reachable += sum(distance < float("inf") for distance in result.distances.values())
    row = rows[-1]
    row["source_count"] = len(results)
    row["reachable"] = reachable


def write_markdown_summary(rows: list[dict[str, object]], output: Path) -> None:
    """Write a compact markdown profile summary."""

    lines = [
        "| phase | seconds | sources | reachable | top cumulative functions |",
        "|---|---:|---:|---:|---|",
    ]
    for row in rows:
        top_entries = row["top_cumulative"]
        if not isinstance(top_entries, list):
            raise TypeError("top_cumulative must be a list")
        top_text = "<br>".join(
            "{function} ({seconds:.6f}s)".format(
                function=entry["function"],
                seconds=float(entry["cumulative_time"]),
            )
            for entry in top_entries[:3]
            if isinstance(entry, dict)
        )
        lines.append(
            "| {phase} | {seconds:.6f} | {sources} | {reachable} | {top} |".format(
                phase=row["phase"],
                seconds=float(row["seconds"]),
                sources=row.get("source_count", ""),
                reachable=row.get("reachable", ""),
                top=top_text,
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile Python overhead around Rust kernels.")
    parser.add_argument("--nodes", type=int, default=5000)
    parser.add_argument("--edges", type=int, default=25000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-weight", type=int, default=1)
    parser.add_argument("--max-weight", type=int, default=50)
    parser.add_argument("--sources", type=int, default=4)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path(".benchmarks/rust_profile.json"))
    parser.add_argument(
        "--require-rust",
        action="store_true",
        help="Fail instead of writing Python-only profile rows when the Rust extension is absent.",
    )
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    graph, row = profiled_call(
        "graph_generation",
        lambda: make_random_graph(
            nodes=args.nodes,
            edges=args.edges,
            directed=True,
            min_weight=args.min_weight,
            max_weight=args.max_weight,
            seed=args.seed,
        ),
        top=args.top,
    )
    rows.append(row)
    sources = select_sources(graph, args.sources)

    reference_results, row = profiled_call(
        "dijkstra_python_many",
        lambda: run_many(dijkstra, graph, sources),
        top=args.top,
    )
    rows.append(row)
    validate_results(rows, "dijkstra_python_many", reference_results, reference_results)

    dial_results, row = profiled_call(
        "dial_circular_python_many",
        lambda: run_many(dial_circular_sssp, graph, sources),
        top=args.top,
    )
    rows.append(row)
    validate_results(rows, "dial_circular_python_many", dial_results, reference_results)

    if rust_backend_available():
        workspace, row = profiled_call(
            "rust_workspace_prepare",
            lambda: RustSsspWorkspace.from_graph(graph),
            top=args.top,
        )
        rows.append(row)
        row["source_count"] = ""
        row["reachable"] = len(workspace.csr.nodes)

        rust_dijkstra, row = profiled_call(
            "dijkstra_rust_wrapper_many",
            lambda: run_many(dijkstra_rust, graph, sources),
            top=args.top,
        )
        rows.append(row)
        validate_results(rows, "dijkstra_rust_wrapper_many", rust_dijkstra, reference_results)

        prepared_dijkstra, row = profiled_call(
            "dijkstra_workspace_many",
            lambda: run_prepared_many(workspace.dijkstra, sources),
            top=args.top,
        )
        rows.append(row)
        validate_results(rows, "dijkstra_workspace_many", prepared_dijkstra, reference_results)

        batched_dijkstra, row = profiled_call(
            "dijkstra_workspace_batch",
            lambda: workspace.dijkstra_many(sources),
            top=args.top,
        )
        rows.append(row)
        validate_results(rows, "dijkstra_workspace_batch", batched_dijkstra, reference_results)

        rust_dial, row = profiled_call(
            "dial_circular_rust_wrapper_many",
            lambda: run_many(dial_circular_rust, graph, sources),
            top=args.top,
        )
        rows.append(row)
        validate_results(rows, "dial_circular_rust_wrapper_many", rust_dial, reference_results)

        prepared_dial, row = profiled_call(
            "dial_circular_workspace_many",
            lambda: run_prepared_many(workspace.dial_circular, sources),
            top=args.top,
        )
        rows.append(row)
        validate_results(rows, "dial_circular_workspace_many", prepared_dial, reference_results)

        batched_dial, row = profiled_call(
            "dial_circular_workspace_batch",
            lambda: workspace.dial_circular_many(sources),
            top=args.top,
        )
        rows.append(row)
        validate_results(rows, "dial_circular_workspace_batch", batched_dial, reference_results)
    elif args.require_rust:
        raise RuntimeError("Rust backend is not installed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    markdown_output = args.output.with_suffix(".md")
    write_markdown_summary(rows, markdown_output)

    print(f"Wrote {args.output}")
    print(f"Wrote {markdown_output}")
    if not rust_backend_available():
        print("Rust backend is not installed; wrote Python-only profile rows.")


if __name__ == "__main__":
    main()
