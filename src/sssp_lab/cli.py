"""Command-line helpers."""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable

from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dial import dial_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap
from sssp_lab.graph import Graph, PathResult
from sssp_lab.utils import assert_same_distances, make_random_graph

Algorithm = Callable[[Graph, int], PathResult]


def main() -> None:
    """Run a small benchmark from the command line."""

    parser = argparse.ArgumentParser(description="Benchmark SSSP algorithms.")
    parser.add_argument("--nodes", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    graph = make_random_graph(
        nodes=args.nodes,
        edges=args.edges,
        directed=True,
        min_weight=1,
        max_weight=20,
        seed=args.seed,
    )

    timings: dict[str, float] = {}
    start = time.perf_counter()
    reference = dijkstra(graph, 0)
    timings["binary_heap_dijkstra"] = time.perf_counter() - start

    algorithms: dict[str, Algorithm] = {
        "dial": dial_sssp,
        "radix_heap": dijkstra_radix_heap,
        "delta_stepping": lambda g, s: delta_stepping(g, s, delta=5.0),
    }

    for name, runner in algorithms.items():
        start = time.perf_counter()
        result = runner(graph, 0)
        timings[name] = time.perf_counter() - start
        assert_same_distances(result.distances, reference.distances)

    for name, seconds in sorted(timings.items(), key=lambda item: item[1]):
        print(f"{name}: {seconds:.6f}s")


if __name__ == "__main__":
    main()
