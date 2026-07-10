"""Frontier-partition SSSP experiment.

This module explores the design idea that shortest paths can be found by
expanding bounded frontiers rather than by globally sorting all active labels.
It is inspired by recent directed-SSSP papers, but it is not a theorem-level
implementation of those papers.
"""

from __future__ import annotations

from dataclasses import dataclass

from sssp_lab.algorithms.bmssp import bounded_multi_source_sssp
from sssp_lab.graph import Graph, Node, PathResult


@dataclass(frozen=True, slots=True)
class FrontierStats:
    """Diagnostics for frontier-partition SSSP."""

    rounds: int
    settled_counts: tuple[int, ...]
    frontier_counts: tuple[int, ...]


def frontier_partition_sssp(
    graph: Graph,
    source: Node,
    *,
    initial_bound: float = 1.0,
    growth: float = 2.0,
) -> tuple[PathResult, FrontierStats]:
    """Compute SSSP by increasing bounded multi-source exploration windows.

    The function is useful for experiments on ordering pressure. It should be
    compared against Dijkstra in all benchmarks.
    """

    if initial_bound <= 0:
        raise ValueError("initial_bound must be positive")
    if growth <= 1:
        raise ValueError("growth must be greater than one")
    graph.require_node(source)
    graph.require_non_negative_weights()

    current_sources: set[Node] = {source}
    bound = float(initial_bound)
    global_distances: dict[Node, float] = {node: float("inf") for node in graph.nodes}
    global_predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
    global_distances[source] = 0.0
    settled_total: set[Node] = set()
    settled_counts: list[int] = []
    frontier_counts: list[int] = []
    rounds = 0

    while len(settled_total) < len(graph.nodes) and current_sources:
        rounds += 1
        result = bounded_multi_source_sssp(
            graph,
            current_sources,
            bound=bound,
            source_distances={node: global_distances[node] for node in current_sources},
        )
        for node, distance in result.distances.items():
            if distance < global_distances[node]:
                global_distances[node] = distance
                global_predecessors[node] = result.predecessors[node]
        settled_total.update(result.settled)
        settled_counts.append(len(result.settled))
        frontier_counts.append(len(result.frontier))
        current_sources = set(result.frontier)
        bound *= growth

        if rounds > max(len(graph.nodes) * 4, 16):
            # Defensive guard. Falling back to Dijkstra would hide the failure,
            # so we expose the issue to the caller.
            raise RuntimeError("frontier expansion did not converge")

    return (
        PathResult(source=source, distances=global_distances, predecessors=global_predecessors),
        FrontierStats(
            rounds=rounds,
            settled_counts=tuple(settled_counts),
            frontier_counts=tuple(frontier_counts),
        ),
    )
