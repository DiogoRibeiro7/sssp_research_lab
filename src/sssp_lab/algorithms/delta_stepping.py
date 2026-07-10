"""Sequential Δ-stepping for single-source shortest paths.

The original algorithm is designed for parallelism. This implementation keeps
its light/heavy edge structure but runs sequentially, which makes it useful for
validation and teaching.
"""

from __future__ import annotations

from collections import defaultdict
from math import floor

from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def _bucket_index(distance: float, delta: float) -> int:
    return int(floor(distance / delta))


def delta_stepping(graph: Graph, source: Node, *, delta: float) -> PathResult:
    """Compute SSSP with sequential Δ-stepping.

    Args:
        graph: Weighted graph with non-negative weights.
        source: Source node.
        delta: Bucket width. Edges with weight ``<= delta`` are treated as light.

    Returns:
        Shortest-path distances and predecessors.
    """

    if not isinstance(delta, (int, float)):
        raise TypeError("delta must be numeric")
    if delta <= 0:
        raise ValueError("delta must be positive")
    graph.require_non_negative_weights()
    distances, predecessors = initialise_single_source(graph, source)

    buckets: dict[int, set[Node]] = defaultdict(set)
    buckets[0].add(source)

    def relax(node: Node, candidate: float, predecessor: Node | None) -> None:
        if candidate < distances[node]:
            old_distance = distances[node]
            if old_distance != float("inf"):
                old_index = _bucket_index(old_distance, float(delta))
                buckets[old_index].discard(node)
            distances[node] = candidate
            predecessors[node] = predecessor
            buckets[_bucket_index(candidate, float(delta))].add(node)

    while buckets:
        current_index = min(buckets)
        current_bucket = buckets[current_index]
        if not current_bucket:
            del buckets[current_index]
            continue

        settled_in_bucket: set[Node] = set()
        while current_bucket:
            active = set(current_bucket)
            current_bucket.clear()
            settled_in_bucket.update(active)
            for node in active:
                for edge in graph.neighbors(node):
                    if edge.weight <= delta:
                        relax(edge.target, distances[node] + edge.weight, node)
        del buckets[current_index]

        for node in settled_in_bucket:
            for edge in graph.neighbors(node):
                if edge.weight > delta:
                    relax(edge.target, distances[node] + edge.weight, node)

    return PathResult(source=source, distances=distances, predecessors=predecessors)
