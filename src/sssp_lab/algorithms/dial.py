"""Dial's bucket-based Dijkstra for non-negative integer weights."""

from __future__ import annotations

from collections import deque
from warnings import warn

from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def dial_sssp(graph: Graph, source: Node, *, stats: OperationStats | None = None) -> PathResult:
    """Compute SSSP with Dial's algorithm.

    Dial's algorithm replaces heap ordering with integer buckets. It is useful
    when edge weights are small non-negative integers. Assumptions: directed or
    undirected graph, non-negative integer weights, single source. Complexity is
    ``O(V * C + E)`` for maximum edge weight ``C`` in this simple bucket layout.
    """

    counters = stats if stats is not None else OperationStats()
    graph.require_non_negative_weights()
    graph.require_integer_weights()
    distances, predecessors = initialise_single_source(graph, source)
    max_distance = graph.max_edge_weight() * max(len(graph.nodes) - 1, 0)
    if max_distance > 1_000_000:
        warn(
            "simple Dial buckets may allocate a large sparse bucket array; "
            "consider dial_circular_sssp or radix-heap Dijkstra",
            RuntimeWarning,
            stacklevel=2,
        )
    buckets: list[deque[Node]] = [deque() for _ in range(max_distance + 1)]
    buckets[0].append(source)
    counters.bucket_insertions += 1
    counters.max_bucket_size = max(counters.max_bucket_size, 1)
    settled: set[Node] = set()

    for bucket_distance, bucket in enumerate(buckets):
        while bucket:
            node = bucket.popleft()
            counters.queue_pops += 1
            if node in settled:
                counters.stale_pops += 1
                continue
            if int(distances[node]) != bucket_distance:
                counters.stale_pops += 1
                continue
            settled.add(node)
            counters.settled_nodes += 1
            for edge in graph.neighbors(node):
                counters.relaxations += 1
                candidate = distances[node] + edge.weight
                if candidate < distances[edge.target]:
                    distances[edge.target] = candidate
                    predecessors[edge.target] = node
                    if candidate <= max_distance:
                        buckets[int(candidate)].append(edge.target)
                        counters.bucket_insertions += 1
                        counters.max_bucket_size = max(
                            counters.max_bucket_size,
                            len(buckets[int(candidate)]),
                        )

    return PathResult(source=source, distances=distances, predecessors=predecessors)
