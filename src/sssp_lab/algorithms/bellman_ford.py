"""Bellman-Ford for graphs with negative edges and no negative cycles."""

from __future__ import annotations

from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


class NegativeCycleError(ValueError):
    """Raised when a reachable negative cycle is detected."""


def bellman_ford(graph: Graph, source: Node) -> PathResult:
    """Compute SSSP with Bellman-Ford.

    Args:
        graph: Weighted directed or undirected graph.
        source: Source node.

    Raises:
        NegativeCycleError: If a negative cycle is reachable from ``source``.
    """

    distances, predecessors = initialise_single_source(graph, source)

    for _ in range(max(len(graph.nodes) - 1, 0)):
        changed = False
        for edge in graph.iter_edges():
            if distances[edge.source] == float("inf"):
                continue
            candidate = distances[edge.source] + edge.weight
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                predecessors[edge.target] = edge.source
                changed = True
        if not changed:
            break

    for edge in graph.iter_edges():
        if distances[edge.source] == float("inf"):
            continue
        if distances[edge.source] + edge.weight < distances[edge.target]:
            raise NegativeCycleError("reachable negative cycle detected")

    return PathResult(source=source, distances=distances, predecessors=predecessors)
