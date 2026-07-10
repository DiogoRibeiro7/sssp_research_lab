"""Sequential Δ-stepping for single-source shortest paths.

The original algorithm is designed for parallelism. This implementation keeps
its light/heavy edge structure but runs sequentially, which makes it useful for
validation and teaching.
"""

from __future__ import annotations

from collections import defaultdict
from math import floor

from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def _bucket_index(distance: float, delta: float) -> int:
    return int(floor(distance / delta))


def delta_stepping(
    graph: Graph,
    source: Node,
    *,
    delta: float,
    stats: OperationStats | None = None,
) -> PathResult:
    """Compute SSSP with sequential Δ-stepping.

    The bucket width Δ controls how much ordering is relaxed. Edges with weight
    ``<= Δ`` are light and are repeatedly relaxed until the current bucket is
    closed. Heavier edges are relaxed once afterward from nodes settled in that
    bucket. Assumptions: directed or undirected graph, non-negative real
    weights, single source.

    Args:
        graph: Weighted graph with non-negative weights.
        source: Source node.
        delta: Bucket width. Edges with weight ``<= delta`` are treated as light.
        stats: Optional mutable operation counters.

    Returns:
        Shortest-path distances and predecessors.
    """

    counters = stats if stats is not None else OperationStats()
    if not isinstance(delta, (int, float)):
        raise TypeError("delta must be numeric")
    if delta <= 0:
        raise ValueError("delta must be positive")
    graph.require_non_negative_weights()
    distances, predecessors = initialise_single_source(graph, source)

    buckets: dict[int, set[Node]] = defaultdict(set)
    buckets[0].add(source)
    counters.bucket_insertions += 1
    counters.max_bucket_size = max(counters.max_bucket_size, 1)

    def relax(node: Node, candidate: float, predecessor: Node | None) -> None:
        if candidate < distances[node]:
            old_distance = distances[node]
            if old_distance != float("inf"):
                old_index = _bucket_index(old_distance, float(delta))
                buckets[old_index].discard(node)
                counters.bucket_reinserts += 1
            distances[node] = candidate
            predecessors[node] = predecessor
            new_index = _bucket_index(candidate, float(delta))
            buckets[new_index].add(node)
            counters.bucket_insertions += 1
            counters.max_bucket_size = max(counters.max_bucket_size, len(buckets[new_index]))

    while buckets:
        current_index = min(buckets)
        current_bucket = buckets[current_index]
        if not current_bucket:
            del buckets[current_index]
            continue

        counters.bucket_phases += 1
        settled_in_bucket: set[Node] = set()
        while current_bucket:
            active = set(current_bucket)
            current_bucket.clear()
            settled_in_bucket.update(active)
            for node in active:
                for edge in graph.neighbors(node):
                    if edge.weight <= delta:
                        counters.relaxations += 1
                        counters.light_relaxations += 1
                        relax(edge.target, distances[node] + edge.weight, node)
        del buckets[current_index]

        for node in settled_in_bucket:
            for edge in graph.neighbors(node):
                if edge.weight > delta:
                    counters.relaxations += 1
                    counters.heavy_relaxations += 1
                    relax(edge.target, distances[node] + edge.weight, node)
        counters.settled_nodes += len(settled_in_bucket)

    return PathResult(source=source, distances=distances, predecessors=predecessors)
