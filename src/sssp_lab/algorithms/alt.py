"""ALT shortest-path queries: A*, Landmarks, and Triangle inequality."""

from __future__ import annotations

import heapq
import random
import time
from dataclasses import dataclass

from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.graph import Graph, Node


@dataclass(frozen=True, slots=True)
class ALTIndex:
    """Landmark distances used by ALT.

    For directed graphs, distances from landmarks and to landmarks are both
    stored. The latter are computed by running Dijkstra on the reversed graph.
    """

    landmarks: tuple[Node, ...]
    from_landmark: dict[Node, dict[Node, float]]
    to_landmark: dict[Node, dict[Node, float]]


@dataclass(slots=True)
class ALTQueryStats:
    """Mutable diagnostics for one ALT query."""

    settled_nodes: int = 0
    heap_pops: int = 0
    heuristic_evaluations: int = 0
    seconds: float = 0.0


def random_landmarks(graph: Graph, *, count: int, seed: int = 0) -> tuple[Node, ...]:
    """Select landmarks uniformly at random with a deterministic seed."""

    if count <= 0:
        raise ValueError("count must be positive")
    nodes = sorted(graph.nodes)
    if count > len(nodes):
        raise ValueError("count must not exceed number of nodes")
    rng = random.Random(seed)
    return tuple(sorted(rng.sample(nodes, count)))


def high_degree_landmarks(graph: Graph, *, count: int) -> tuple[Node, ...]:
    """Select nodes with the highest outgoing degree."""

    if count <= 0:
        raise ValueError("count must be positive")
    return tuple(
        node
        for node, _ in sorted(
            ((node, len(graph.neighbors(node))) for node in graph.nodes),
            key=lambda item: (-item[1], item[0]),
        )[:count]
    )


def farthest_first_landmarks(graph: Graph, *, count: int, seed: Node | None = None) -> tuple[Node, ...]:
    """Select landmarks greedily by maximum distance from existing landmarks."""

    if count <= 0:
        raise ValueError("count must be positive")
    nodes = sorted(graph.nodes)
    if count > len(nodes):
        raise ValueError("count must not exceed number of nodes")
    first = nodes[0] if seed is None else seed
    graph.require_node(first)
    landmarks = [first]
    while len(landmarks) < count:
        distance_maps = [dijkstra(graph, landmark).distances for landmark in landmarks]
        best_node = max(
            (node for node in nodes if node not in landmarks),
            key=lambda node: (
                min(distance_map[node] for distance_map in distance_maps),
                -node,
            ),
        )
        landmarks.append(best_node)
    return tuple(landmarks)


def grid_corner_landmarks(*, width: int, height: int) -> tuple[Node, ...]:
    """Return corner node ids for a row-major rectangular grid graph."""

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    return (
        0,
        width - 1,
        (height - 1) * width,
        (height * width) - 1,
    )


def build_alt_index(graph: Graph, landmarks: list[Node] | tuple[Node, ...]) -> ALTIndex:
    """Precompute landmark distances for ALT."""

    if not landmarks:
        raise ValueError("at least one landmark is required")
    graph.require_non_negative_weights()
    reverse = graph.reversed()
    from_landmark: dict[Node, dict[Node, float]] = {}
    to_landmark: dict[Node, dict[Node, float]] = {}
    for landmark in landmarks:
        graph.require_node(landmark)
        from_landmark[landmark] = dict(dijkstra(graph, landmark).distances)
        to_landmark[landmark] = dict(dijkstra(reverse, landmark).distances)
    return ALTIndex(
        landmarks=tuple(landmarks),
        from_landmark=from_landmark,
        to_landmark=to_landmark,
    )


def _lower_bound(index: ALTIndex, node: Node, target: Node) -> float:
    lower = 0.0
    for landmark in index.landmarks:
        # Directed ALT uses both |d(L,t)-d(L,v)| style bounds and reverse bounds.
        from_l_node = index.from_landmark[landmark].get(node, float("inf"))
        from_l_target = index.from_landmark[landmark].get(target, float("inf"))
        to_l_node = index.to_landmark[landmark].get(node, float("inf"))
        to_l_target = index.to_landmark[landmark].get(target, float("inf"))

        if from_l_node < float("inf") and from_l_target < float("inf"):
            lower = max(lower, from_l_target - from_l_node)
        if to_l_node < float("inf") and to_l_target < float("inf"):
            lower = max(lower, to_l_node - to_l_target)
    return max(lower, 0.0)


def alt_query(
    graph: Graph,
    source: Node,
    target: Node,
    index: ALTIndex,
    *,
    stats: ALTQueryStats | None = None,
) -> tuple[float, list[Node]]:
    """Run one ALT point-to-point shortest-path query."""

    start = time.perf_counter()
    counters = stats if stats is not None else ALTQueryStats()
    graph.require_non_negative_weights()
    graph.require_node(source)
    graph.require_node(target)

    distances: dict[Node, float] = {node: float("inf") for node in graph.nodes}
    predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
    distances[source] = 0.0
    counters.heuristic_evaluations += 1
    queue: list[tuple[float, Node]] = [(_lower_bound(index, source, target), source)]
    settled: set[Node] = set()

    while queue:
        _, node = heapq.heappop(queue)
        counters.heap_pops += 1
        if node in settled:
            continue
        if node == target:
            break
        settled.add(node)
        counters.settled_nodes += 1
        for edge in graph.neighbors(node):
            candidate = distances[node] + edge.weight
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                predecessors[edge.target] = node
                counters.heuristic_evaluations += 1
                priority = candidate + _lower_bound(index, edge.target, target)
                heapq.heappush(queue, (priority, edge.target))

    if distances[target] == float("inf"):
        counters.seconds = time.perf_counter() - start
        return float("inf"), []

    path: list[Node] = []
    current: Node | None = target
    seen: set[Node] = set()
    while current is not None:
        if current in seen:
            raise RuntimeError("cycle detected in ALT predecessor chain")
        seen.add(current)
        path.append(current)
        current = predecessors[current]
    path.reverse()
    counters.seconds = time.perf_counter() - start
    return distances[target], path
