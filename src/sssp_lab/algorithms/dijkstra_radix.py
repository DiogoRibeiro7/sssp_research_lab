"""Dijkstra's algorithm using a radix heap."""

from __future__ import annotations

from sssp_lab.algorithms.radix_heap import RadixHeap
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def dijkstra_radix_heap(
    graph: Graph,
    source: Node,
    *,
    stats: OperationStats | None = None,
) -> PathResult:
    """Compute SSSP with radix-heap Dijkstra.

    The implementation assumes non-negative integer weights. It is a good
    practical companion to Dial's algorithm and helps illustrate the sorting
    bottleneck around Dijkstra's priority queue. Complexity is ``O(E log C)``
    in terms of the integer key range represented by the configured heap bits.
    """

    counters = stats if stats is not None else OperationStats()
    graph.require_non_negative_weights()
    graph.require_integer_weights()
    distances, predecessors = initialise_single_source(graph, source)
    queue: RadixHeap[Node] = RadixHeap(max_bits=64)
    queue.push(0, source)
    counters.queue_pushes += 1
    settled: set[Node] = set()

    while queue:
        distance, node = queue.pop()
        counters.queue_pops += 1
        if node in settled:
            counters.stale_pops += 1
            continue
        if distance != int(distances[node]):
            counters.stale_pops += 1
            continue
        settled.add(node)
        counters.settled_nodes += 1
        for edge in graph.neighbors(node):
            counters.relaxations += 1
            candidate = int(distances[node] + edge.weight)
            if candidate < distances[edge.target]:
                distances[edge.target] = float(candidate)
                predecessors[edge.target] = node
                queue.push(candidate, edge.target)
                counters.queue_pushes += 1

    return PathResult(source=source, distances=distances, predecessors=predecessors)
