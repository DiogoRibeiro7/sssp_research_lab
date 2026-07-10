"""Dijkstra's algorithm using Python's binary heap.

This is the reference implementation used in most tests. It is intentionally
plain and readable.
"""

from __future__ import annotations

import heapq

from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def dijkstra(graph: Graph, source: Node, *, stats: OperationStats | None = None) -> PathResult:
    """Compute SSSP with Dijkstra's algorithm.

    Assumptions: directed or undirected graph, non-negative real weights,
    single source, all reachable targets. Complexity is ``O((V + E) log V)``
    with Python's binary heap and lazy stale-entry skipping.

    Args:
        graph: Weighted graph with non-negative edge weights.
        source: Source node.
        stats: Optional mutable operation counters.

    Returns:
        A :class:`PathResult` containing distances and predecessors.
    """

    counters = stats if stats is not None else OperationStats()
    graph.require_non_negative_weights()
    distances, predecessors = initialise_single_source(graph, source)
    heap: list[tuple[float, Node]] = [(0.0, source)]
    counters.queue_pushes += 1
    settled: set[Node] = set()

    while heap:
        distance, node = heapq.heappop(heap)
        counters.queue_pops += 1
        if node in settled:
            counters.stale_pops += 1
            continue
        if distance != distances[node]:
            counters.stale_pops += 1
            continue
        settled.add(node)
        counters.settled_nodes += 1
        for edge in graph.neighbors(node):
            counters.relaxations += 1
            candidate = distance + edge.weight
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                predecessors[edge.target] = node
                heapq.heappush(heap, (candidate, edge.target))
                counters.queue_pushes += 1

    return PathResult(source=source, distances=distances, predecessors=predecessors)
