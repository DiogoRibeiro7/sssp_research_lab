"""Shared utilities for shortest-path algorithms."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping

from sssp_lab.graph import Graph, Node, Weight

INF = float("inf")


def initialise_single_source(graph: Graph, source: Node) -> tuple[dict[Node, Weight], dict[Node, Node | None]]:
    """Initialise distance and predecessor maps for SSSP algorithms."""

    graph.require_node(source)
    distances: dict[Node, Weight] = {node: INF for node in graph.nodes}
    predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
    distances[source] = 0.0
    return distances, predecessors


def assert_same_distances(
    actual: Mapping[Node, Weight],
    expected: Mapping[Node, Weight],
    *,
    tolerance: float = 1e-9,
) -> None:
    """Assert that two distance maps are equal up to a numerical tolerance."""

    if set(actual) != set(expected):
        raise AssertionError("distance maps have different node sets")
    for node in expected:
        a = actual[node]
        e = expected[node]
        if math.isinf(a) and math.isinf(e):
            continue
        if abs(a - e) > tolerance:
            raise AssertionError(f"distance mismatch at node {node}: {a} != {e}")


def make_random_graph(
    *,
    nodes: int,
    edges: int,
    directed: bool,
    min_weight: int = 1,
    max_weight: int = 10,
    seed: int = 0,
) -> Graph:
    """Generate a deterministic random graph for tests and benchmarks."""

    if nodes <= 0:
        raise ValueError("nodes must be positive")
    if edges < 0:
        raise ValueError("edges must be non-negative")
    if min_weight < 0 or max_weight < min_weight:
        raise ValueError("invalid weight range")

    rng = random.Random(seed)
    graph = Graph(directed=directed)
    for node in range(nodes):
        graph.add_node(node)

    attempts = 0
    inserted = 0
    seen: set[tuple[int, int]] = set()
    while inserted < edges and attempts < edges * 20 + 100:
        attempts += 1
        source = rng.randrange(nodes)
        target = rng.randrange(nodes)
        if source == target:
            continue
        key = (source, target) if directed else (min(source, target), max(source, target))
        if key in seen:
            continue
        seen.add(key)
        graph.add_edge(source, target, float(rng.randint(min_weight, max_weight)))
        inserted += 1
    return graph
