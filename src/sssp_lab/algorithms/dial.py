"""Dial's bucket-based Dijkstra for non-negative integer weights."""

from __future__ import annotations

from collections import deque

from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def dial_sssp(graph: Graph, source: Node) -> PathResult:
    """Compute SSSP with Dial's algorithm.

    Dial's algorithm replaces heap ordering with integer buckets. It is useful
    when edge weights are small non-negative integers.
    """

    graph.require_non_negative_weights()
    graph.require_integer_weights()
    distances, predecessors = initialise_single_source(graph, source)
    max_distance = graph.max_edge_weight() * max(len(graph.nodes) - 1, 0)
    buckets: list[deque[Node]] = [deque() for _ in range(max_distance + 1)]
    buckets[0].append(source)
    settled: set[Node] = set()

    for bucket_distance, bucket in enumerate(buckets):
        while bucket:
            node = bucket.popleft()
            if node in settled:
                continue
            if int(distances[node]) != bucket_distance:
                continue
            settled.add(node)
            for edge in graph.neighbors(node):
                candidate = distances[node] + edge.weight
                if candidate < distances[edge.target]:
                    distances[edge.target] = candidate
                    predecessors[edge.target] = node
                    if candidate <= max_distance:
                        buckets[int(candidate)].append(edge.target)

    return PathResult(source=source, distances=distances, predecessors=predecessors)
