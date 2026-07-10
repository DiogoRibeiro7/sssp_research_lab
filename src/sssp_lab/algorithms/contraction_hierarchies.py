"""Small-graph Contraction Hierarchies implementation.

This is an educational implementation. It contracts nodes in a supplied order,
adds exact witness shortcuts using local Dijkstra, and answers queries with a
bidirectional upward search.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.graph import Edge, Graph, Node


@dataclass(frozen=True, slots=True)
class Shortcut:
    """Shortcut edge added during contraction."""

    source: Node
    target: Node
    weight: float
    via: Node


@dataclass(frozen=True, slots=True)
class CHIndex:
    """Preprocessed contraction hierarchy."""

    upward: Graph
    downward: Graph
    rank: dict[Node, int]
    shortcuts: tuple[Shortcut, ...]


def _without_node(graph: Graph, blocked: Node) -> Graph:
    filtered = Graph(directed=True)
    for node in graph.nodes:
        if node != blocked:
            filtered.add_node(node)
    for edge in graph.iter_edges():
        if edge.source != blocked and edge.target != blocked:
            filtered.add_edge(edge.source, edge.target, edge.weight)
    return filtered


def _incoming_edges(graph: Graph, node: Node) -> list[Edge]:
    return [edge for edge in graph.iter_edges() if edge.target == node]


def build_ch_index(graph: Graph, order: list[Node] | tuple[Node, ...] | None = None) -> CHIndex:
    """Build a small-graph contraction hierarchy.

    Args:
        graph: Directed or undirected graph with non-negative weights.
        order: Optional contraction order. If omitted, nodes are contracted by
            increasing degree.
    """

    graph.require_non_negative_weights()
    if order is None:
        order = tuple(sorted(graph.nodes, key=lambda n: len(graph.neighbors(n))))
    if set(order) != set(graph.nodes):
        raise ValueError("order must contain exactly the graph nodes")

    rank = {node: i for i, node in enumerate(order)}
    work = Graph(directed=True)
    for node in graph.nodes:
        work.add_node(node)
    for edge in graph.iter_edges():
        work.add_edge(edge.source, edge.target, edge.weight)

    shortcuts: list[Shortcut] = []
    contracted: set[Node] = set()
    for node in order:
        incoming = [edge for edge in _incoming_edges(work, node) if edge.source not in contracted]
        outgoing = [edge for edge in work.neighbors(node) if edge.target not in contracted]
        witness_graph = _without_node(work, node)
        for in_edge in incoming:
            for out_edge in outgoing:
                if in_edge.source == out_edge.target:
                    continue
                shortcut_weight = in_edge.weight + out_edge.weight
                witness = dijkstra(witness_graph, in_edge.source).distances[out_edge.target]
                if shortcut_weight < witness:
                    work.add_edge(in_edge.source, out_edge.target, shortcut_weight)
                    shortcuts.append(
                        Shortcut(
                            source=in_edge.source,
                            target=out_edge.target,
                            weight=shortcut_weight,
                            via=node,
                        )
                    )
        contracted.add(node)

    upward = Graph(directed=True)
    downward = Graph(directed=True)
    for node in graph.nodes:
        upward.add_node(node)
        downward.add_node(node)
    for edge in work.iter_edges():
        if rank[edge.source] < rank[edge.target]:
            upward.add_edge(edge.source, edge.target, edge.weight)
            downward.add_edge(edge.target, edge.source, edge.weight)
        elif rank[edge.target] < rank[edge.source]:
            upward.add_edge(edge.target, edge.source, edge.weight)
            downward.add_edge(edge.source, edge.target, edge.weight)

    return CHIndex(upward=upward, downward=downward, rank=rank, shortcuts=tuple(shortcuts))


def _search_upward(graph: Graph, source: Node) -> dict[Node, float]:
    distances = {node: float("inf") for node in graph.nodes}
    distances[source] = 0.0
    queue: list[tuple[float, Node]] = [(0.0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        for edge in graph.neighbors(node):
            candidate = distance + edge.weight
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                heapq.heappush(queue, (candidate, edge.target))
    return distances


def ch_query(index: CHIndex, source: Node, target: Node) -> float:
    """Return the shortest-path distance using the CH index."""

    index.upward.require_node(source)
    index.upward.require_node(target)
    forward = _search_upward(index.upward, source)
    backward = _search_upward(index.downward, target)
    return min(forward[node] + backward[node] for node in index.upward.nodes)
