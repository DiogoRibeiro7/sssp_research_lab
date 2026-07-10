"""Dijkstra's algorithm using Python's binary heap.

This is the reference implementation used in most tests. It is intentionally
plain and readable.
"""

from __future__ import annotations

import heapq

from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def dijkstra(graph: Graph, source: Node) -> PathResult:
    """Compute SSSP with Dijkstra's algorithm.

    Args:
        graph: Weighted graph with non-negative edge weights.
        source: Source node.

    Returns:
        A :class:`PathResult` containing distances and predecessors.
    """

    graph.require_non_negative_weights()
    distances, predecessors = initialise_single_source(graph, source)
    heap: list[tuple[float, Node]] = [(0.0, source)]
    settled: set[Node] = set()

    while heap:
        distance, node = heapq.heappop(heap)
        if node in settled:
            continue
        if distance != distances[node]:
            continue
        settled.add(node)
        for edge in graph.neighbors(node):
            candidate = distance + edge.weight
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                predecessors[edge.target] = node
                heapq.heappush(heap, (candidate, edge.target))

    return PathResult(source=source, distances=distances, predecessors=predecessors)
