"""Dijkstra's algorithm using a radix heap."""

from __future__ import annotations

from sssp_lab.algorithms.radix_heap import RadixHeap
from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source


def dijkstra_radix_heap(graph: Graph, source: Node) -> PathResult:
    """Compute SSSP with radix-heap Dijkstra.

    The implementation assumes non-negative integer weights. It is a good
    practical companion to Dial's algorithm and helps illustrate the sorting
    bottleneck around Dijkstra's priority queue.
    """

    graph.require_non_negative_weights()
    graph.require_integer_weights()
    distances, predecessors = initialise_single_source(graph, source)
    queue: RadixHeap[Node] = RadixHeap(max_bits=64)
    queue.push(0, source)
    settled: set[Node] = set()

    while queue:
        distance, node = queue.pop()
        if node in settled:
            continue
        if distance != int(distances[node]):
            continue
        settled.add(node)
        for edge in graph.neighbors(node):
            candidate = int(distances[node] + edge.weight)
            if candidate < distances[edge.target]:
                distances[edge.target] = float(candidate)
                predecessors[edge.target] = node
                queue.push(candidate, edge.target)

    return PathResult(source=source, distances=distances, predecessors=predecessors)
