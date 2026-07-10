"""Small-graph Contraction Hierarchies implementation.

This is an educational implementation. It contracts nodes in a supplied order,
adds exact witness shortcuts using local Dijkstra, and answers queries with a
bidirectional upward search.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

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
    shortcut_lookup: dict[tuple[Node, Node], Shortcut]


@dataclass(frozen=True, slots=True)
class ContractionCandidate:
    """Dynamic score for contracting one node."""

    node: Node
    shortcut_count: int
    edge_difference: int
    contracted_neighbors: int
    level: int


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


def _active_incoming_edges(graph: Graph, node: Node, contracted: set[Node]) -> list[Edge]:
    return [edge for edge in _incoming_edges(graph, node) if edge.source not in contracted]


def _active_outgoing_edges(graph: Graph, node: Node, contracted: set[Node]) -> list[Edge]:
    return [edge for edge in graph.neighbors(node) if edge.target not in contracted]


def _required_shortcuts(graph: Graph, node: Node, contracted: set[Node]) -> list[Shortcut]:
    incoming = _active_incoming_edges(graph, node, contracted)
    outgoing = _active_outgoing_edges(graph, node, contracted)
    witness_graph = _without_node(graph, node)
    shortcuts: list[Shortcut] = []
    for in_edge in incoming:
        for out_edge in outgoing:
            if in_edge.source == out_edge.target:
                continue
            shortcut_weight = in_edge.weight + out_edge.weight
            witness = _bounded_witness_distance(
                witness_graph,
                in_edge.source,
                out_edge.target,
                shortcut_weight,
            )
            if shortcut_weight < witness:
                shortcuts.append(
                    Shortcut(
                        source=in_edge.source,
                        target=out_edge.target,
                        weight=shortcut_weight,
                        via=node,
                    )
                )
    return shortcuts


def _contracted_neighbor_count(graph: Graph, node: Node, contracted: set[Node]) -> int:
    neighbors = {edge.source for edge in _incoming_edges(graph, node)}
    neighbors.update(edge.target for edge in graph.neighbors(node))
    return len(neighbors & contracted)


def contraction_order(graph: Graph, *, heuristic: str = "degree") -> tuple[Node, ...]:
    """Return an educational contraction order for small graphs."""

    if heuristic.startswith("witness_"):
        return witness_contraction_order(graph, heuristic=heuristic.removeprefix("witness_"))

    incoming_counts = {node: 0 for node in graph.nodes}
    for edge in graph.iter_edges():
        incoming_counts[edge.target] += 1

    def key(node: Node) -> tuple[int, int]:
        outgoing = len(graph.neighbors(node))
        incoming = incoming_counts[node]
        if heuristic == "degree":
            score = incoming + outgoing
        elif heuristic == "edge_difference":
            score = (incoming * outgoing) - incoming - outgoing
        elif heuristic == "contracted_neighbor_count":
            score = len({edge.target for edge in graph.neighbors(node)}) + incoming
        elif heuristic == "shortcut_cover":
            score = incoming * outgoing
        elif heuristic == "level":
            score = max(incoming, outgoing)
        else:
            raise ValueError(f"unknown contraction heuristic: {heuristic}")
        return (score, node)

    return tuple(sorted(graph.nodes, key=key))


def contraction_candidate(
    graph: Graph,
    node: Node,
    *,
    contracted: set[Node] | None = None,
    level: dict[Node, int] | None = None,
) -> ContractionCandidate:
    """Estimate the dynamic CH priority metrics for one candidate node."""

    graph.require_node(node)
    active_contracted = set() if contracted is None else contracted
    active_level = {candidate: 0 for candidate in graph.nodes} if level is None else level
    incoming = _active_incoming_edges(graph, node, active_contracted)
    outgoing = _active_outgoing_edges(graph, node, active_contracted)
    shortcut_count = len(_required_shortcuts(graph, node, active_contracted))
    return ContractionCandidate(
        node=node,
        shortcut_count=shortcut_count,
        edge_difference=shortcut_count - len(incoming) - len(outgoing),
        contracted_neighbors=_contracted_neighbor_count(graph, node, active_contracted),
        level=active_level.get(node, 0),
    )


def witness_contraction_order(graph: Graph, *, heuristic: str = "edge_difference") -> tuple[Node, ...]:
    """Build a dynamic contraction order using witness-based shortcut estimates."""

    graph.require_non_negative_weights()
    work = Graph(directed=True)
    for node in graph.nodes:
        work.add_node(node)
    for edge in graph.iter_edges():
        work.add_edge(edge.source, edge.target, edge.weight)

    contracted: set[Node] = set()
    levels = {node: 0 for node in graph.nodes}
    order: list[Node] = []

    def score(candidate: ContractionCandidate) -> tuple[int, int, int, int]:
        if heuristic == "edge_difference":
            value = candidate.edge_difference
        elif heuristic == "shortcut_cover":
            value = candidate.shortcut_count
        elif heuristic == "contracted_neighbor_count":
            value = candidate.edge_difference + candidate.contracted_neighbors
        elif heuristic == "level":
            value = candidate.edge_difference + candidate.level
        else:
            raise ValueError(f"unknown witness contraction heuristic: {heuristic}")
        return (value, candidate.shortcut_count, candidate.level, candidate.node)

    while len(order) < len(graph.nodes):
        remaining = sorted(graph.nodes - contracted)
        candidates = [
            contraction_candidate(work, node, contracted=contracted, level=levels)
            for node in remaining
        ]
        selected = min(candidates, key=score)
        shortcuts = _required_shortcuts(work, selected.node, contracted)
        for shortcut in shortcuts:
            work.add_edge(shortcut.source, shortcut.target, shortcut.weight)
            levels[shortcut.source] = max(levels[shortcut.source], levels[selected.node] + 1)
            levels[shortcut.target] = max(levels[shortcut.target], levels[selected.node] + 1)
        contracted.add(selected.node)
        order.append(selected.node)
    return tuple(order)


def _bounded_witness_distance(graph: Graph, source: Node, target: Node, bound: float) -> float:
    """Return a witness distance, stopping once labels exceed ``bound``."""

    distances = {node: float("inf") for node in graph.nodes}
    distances[source] = 0.0
    queue: list[tuple[float, Node]] = [(0.0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        if distance > bound:
            return float("inf")
        if node == target:
            return distance
        for edge in graph.neighbors(node):
            candidate = distance + edge.weight
            if candidate < distances[edge.target] and candidate <= bound:
                distances[edge.target] = candidate
                heapq.heappush(queue, (candidate, edge.target))
    return distances[target]


def build_ch_index(
    graph: Graph,
    order: list[Node] | tuple[Node, ...] | None = None,
    *,
    heuristic: str = "degree",
) -> CHIndex:
    """Build a small-graph contraction hierarchy.

    Args:
        graph: Directed or undirected graph with non-negative weights.
        order: Optional contraction order. If omitted, nodes are contracted by
            the selected heuristic.
        heuristic: Educational order heuristic used when ``order`` is omitted.
    """

    graph.require_non_negative_weights()
    if order is None:
        order = contraction_order(graph, heuristic=heuristic)
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
                witness = _bounded_witness_distance(
                    witness_graph,
                    in_edge.source,
                    out_edge.target,
                    shortcut_weight,
                )
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

    shortcut_lookup: dict[tuple[Node, Node], Shortcut] = {}
    for shortcut in shortcuts:
        current = shortcut_lookup.get((shortcut.source, shortcut.target))
        if current is None or shortcut.weight < current.weight:
            shortcut_lookup[(shortcut.source, shortcut.target)] = shortcut

    return CHIndex(
        upward=upward,
        downward=downward,
        rank=rank,
        shortcuts=tuple(shortcuts),
        shortcut_lookup=shortcut_lookup,
    )


def _search_upward(graph: Graph, source: Node) -> tuple[dict[Node, float], dict[Node, Node | None]]:
    distances = {node: float("inf") for node in graph.nodes}
    predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
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
                predecessors[edge.target] = node
                heapq.heappush(queue, (candidate, edge.target))
    return distances, predecessors


def _path_from_predecessors(
    predecessors: dict[Node, Node | None],
    source: Node,
    target: Node,
) -> list[Node]:
    path: list[Node] = []
    current: Node | None = target
    while current is not None:
        path.append(current)
        if current == source:
            break
        current = predecessors[current]
    if not path or path[-1] != source:
        return []
    path.reverse()
    return path


def _unpack_pair(source: Node, target: Node, shortcuts: dict[tuple[Node, Node], Shortcut]) -> list[Node]:
    shortcut = shortcuts.get((source, target))
    if shortcut is None:
        return [source, target]
    left = _unpack_pair(source, shortcut.via, shortcuts)
    right = _unpack_pair(shortcut.via, target, shortcuts)
    return left[:-1] + right


def _unpack_path(path: list[Node], shortcuts: dict[tuple[Node, Node], Shortcut]) -> list[Node]:
    if len(path) < 2:
        return path
    unpacked: list[Node] = [path[0]]
    for source, target in zip(path, path[1:], strict=False):
        unpacked.extend(_unpack_pair(source, target, shortcuts)[1:])
    return unpacked


def ch_query(index: CHIndex, source: Node, target: Node) -> float:
    """Return the shortest-path distance using the CH index."""

    index.upward.require_node(source)
    index.upward.require_node(target)
    forward, _ = _search_upward(index.upward, source)
    backward, _ = _search_upward(index.downward.reversed(), target)
    return min(forward[node] + backward[node] for node in index.upward.nodes)


def ch_query_path(index: CHIndex, source: Node, target: Node) -> tuple[float, list[Node]]:
    """Return the CH distance and an unpacked source-to-target path."""

    index.upward.require_node(source)
    index.upward.require_node(target)
    forward, forward_predecessors = _search_upward(index.upward, source)
    backward, backward_predecessors = _search_upward(index.downward.reversed(), target)
    meeting = min(index.upward.nodes, key=lambda node: forward[node] + backward[node])
    distance = forward[meeting] + backward[meeting]
    if distance == float("inf"):
        return float("inf"), []

    forward_path = _path_from_predecessors(forward_predecessors, source, meeting)
    reverse_tail = _path_from_predecessors(backward_predecessors, target, meeting)
    tail = list(reversed(reverse_tail))
    packed = forward_path + tail[1:]
    return distance, _unpack_path(packed, index.shortcut_lookup)
