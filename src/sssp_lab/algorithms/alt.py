"""ALT shortest-path queries: A*, Landmarks, and Triangle inequality."""

from __future__ import annotations

import heapq
import random
import time
from collections.abc import Mapping
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


def _validate_landmark_count(graph: Graph, count: int) -> list[Node]:
    if count <= 0:
        raise ValueError("count must be positive")
    nodes = sorted(graph.nodes)
    if count > len(nodes):
        raise ValueError("count must not exceed number of nodes")
    return nodes


def random_landmarks(graph: Graph, *, count: int, seed: int = 0) -> tuple[Node, ...]:
    """Select landmarks uniformly at random with a deterministic seed."""

    nodes = _validate_landmark_count(graph, count)
    rng = random.Random(seed)
    return tuple(sorted(rng.sample(nodes, count)))


def high_degree_landmarks(graph: Graph, *, count: int) -> tuple[Node, ...]:
    """Select nodes with the highest outgoing degree."""

    _validate_landmark_count(graph, count)
    return tuple(
        node
        for node, _ in sorted(
            ((node, len(graph.neighbors(node))) for node in graph.nodes),
            key=lambda item: (-item[1], item[0]),
        )[:count]
    )


def farthest_first_landmarks(graph: Graph, *, count: int, seed: Node | None = None) -> tuple[Node, ...]:
    """Select landmarks greedily by maximum distance from existing landmarks."""

    nodes = _validate_landmark_count(graph, count)
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


def avoid_landmarks(
    graph: Graph,
    *,
    count: int,
    seed: Node | None = None,
    sample_limit: int = 64,
) -> tuple[Node, ...]:
    """Select landmarks by targeting weak current ALT lower bounds.

    This deterministic approximation of the ALT "avoid" idea repeatedly samples
    source-target pairs, finds a pair where the current landmarks leave a large
    distance gap, and adds a node on that shortest path that is far from the
    existing landmarks.
    """

    nodes = _validate_landmark_count(graph, count)
    if sample_limit <= 0:
        raise ValueError("sample_limit must be positive")
    first = nodes[0] if seed is None else seed
    graph.require_node(first)
    landmarks = [first]

    while len(landmarks) < count:
        index = build_alt_index(graph, landmarks)
        pair_count = min(sample_limit, max(1, len(nodes) * (len(nodes) - 1)))
        sampled_pairs = (
            (nodes[i % len(nodes)], nodes[-(i % len(nodes)) - 1])
            for i in range(pair_count)
        )
        best_score: tuple[float, float, int, int] | None = None
        best_path: list[Node] = []
        for source, target in sampled_pairs:
            if source == target:
                continue
            result = dijkstra(graph, source)
            distance = result.distances[target]
            if distance == float("inf"):
                continue
            lower_bound = _lower_bound(index, source, target)
            gap = distance - lower_bound
            path = result.path_to(target)
            score = (gap, distance, -source, -target)
            if path and (best_score is None or score > best_score):
                best_score = score
                best_path = path

        if not best_path:
            return farthest_first_landmarks(graph, count=count, seed=first)

        candidates = [node for node in best_path if node not in landmarks]
        if not candidates:
            candidates = [node for node in nodes if node not in landmarks]
        distance_maps = [dijkstra(graph, landmark).distances for landmark in landmarks]
        landmarks.append(
            max(
                candidates,
                key=lambda node: (
                    min(distance_map[node] for distance_map in distance_maps),
                    -node,
                ),
            )
        )
    return tuple(landmarks)


def coordinate_corner_landmarks(
    graph: Graph,
    coordinates: Mapping[Node, tuple[float, float]],
    *,
    count: int = 4,
) -> tuple[Node, ...]:
    """Select nodes nearest the bounding-box corners of supplied coordinates."""

    nodes = _validate_landmark_count(graph, count)
    missing = [node for node in nodes if node not in coordinates]
    if missing:
        raise ValueError("coordinates must include every graph node")
    xs = [coordinates[node][0] for node in nodes]
    ys = [coordinates[node][1] for node in nodes]
    corners = (
        (min(xs), min(ys)),
        (max(xs), min(ys)),
        (min(xs), max(ys)),
        (max(xs), max(ys)),
    )
    landmarks: list[Node] = []
    for corner_x, corner_y in corners:
        closest = min(
            (node for node in nodes if node not in landmarks),
            key=lambda node: (
                (coordinates[node][0] - corner_x) ** 2 + (coordinates[node][1] - corner_y) ** 2,
                node,
            ),
            default=None,
        )
        if closest is not None:
            landmarks.append(closest)
        if len(landmarks) == count:
            return tuple(landmarks)

    while len(landmarks) < count:
        landmarks.append(
            max(
                (node for node in nodes if node not in landmarks),
                key=lambda node: (
                    min(
                        (coordinates[node][0] - coordinates[landmark][0]) ** 2
                        + (coordinates[node][1] - coordinates[landmark][1]) ** 2
                        for landmark in landmarks
                    ),
                    -node,
                ),
            )
        )
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
