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


def make_erdos_renyi_graph(
    *,
    nodes: int,
    probability: float,
    directed: bool,
    min_weight: int = 1,
    max_weight: int = 10,
    seed: int = 0,
) -> Graph:
    """Generate a deterministic weighted Erdos-Renyi graph."""

    if nodes <= 0:
        raise ValueError("nodes must be positive")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be in [0, 1]")
    rng = random.Random(seed)
    graph = Graph(directed=directed)
    for node in range(nodes):
        graph.add_node(node)
    for source in range(nodes):
        targets = range(nodes) if directed else range(source + 1, nodes)
        for target in targets:
            if source == target:
                continue
            if rng.random() <= probability:
                graph.add_edge(source, target, float(rng.randint(min_weight, max_weight)))
    return graph


def make_grid_graph(width: int, height: int, *, directed: bool = False, weight: int = 1) -> Graph:
    """Generate a row-major rectangular grid graph."""

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    graph = Graph(directed=directed)
    for node in range(width * height):
        graph.add_node(node)
    for row in range(height):
        for col in range(width):
            node = row * width + col
            if col + 1 < width:
                graph.add_edge(node, node + 1, float(weight))
            if row + 1 < height:
                graph.add_edge(node, node + width, float(weight))
    return graph


def make_layered_dag(
    *,
    layers: int,
    width: int,
    edge_probability: float = 0.5,
    min_weight: int = 1,
    max_weight: int = 10,
    seed: int = 0,
) -> Graph:
    """Generate a weighted layered DAG with edges only to the next layer."""

    if layers <= 0 or width <= 0:
        raise ValueError("layers and width must be positive")
    rng = random.Random(seed)
    graph = Graph(directed=True)
    for node in range(layers * width):
        graph.add_node(node)
    for layer in range(layers - 1):
        for source_col in range(width):
            source = layer * width + source_col
            for target_col in range(width):
                if rng.random() <= edge_probability:
                    target = (layer + 1) * width + target_col
                    graph.add_edge(source, target, float(rng.randint(min_weight, max_weight)))
    return graph


def make_road_like_graph(*, width: int, height: int, seed: int = 0) -> Graph:
    """Generate a sparse grid with a few deterministic long links."""

    rng = random.Random(seed)
    graph = make_grid_graph(width, height, directed=False, weight=1)
    nodes = sorted(graph.nodes)
    for _ in range(max(1, len(nodes) // 10)):
        source = rng.choice(nodes)
        target = rng.choice(nodes)
        if source != target:
            graph.add_edge(source, target, float(rng.randint(2, 8)))
    return graph


def make_heavy_tailed_graph(
    *,
    nodes: int,
    edges: int,
    directed: bool,
    seed: int = 0,
) -> Graph:
    """Generate a graph with preferential attachment-like endpoint reuse."""

    if nodes <= 0:
        raise ValueError("nodes must be positive")
    rng = random.Random(seed)
    graph = Graph(directed=directed)
    for node in range(nodes):
        graph.add_node(node)
    choices = list(range(nodes))
    inserted = 0
    while inserted < edges:
        source = rng.choice(choices)
        target = rng.randrange(nodes)
        if source == target:
            continue
        graph.add_edge(source, target, float(rng.randint(1, 20)))
        choices.extend([source, target])
        inserted += 1
    return graph


def make_equal_weight_graph(*, nodes: int, edges: int, directed: bool, seed: int = 0) -> Graph:
    """Generate a deterministic graph where every edge has weight one."""

    return make_random_graph(
        nodes=nodes,
        edges=edges,
        directed=directed,
        min_weight=1,
        max_weight=1,
        seed=seed,
    )


def make_wide_integer_weight_graph(
    *,
    nodes: int,
    edges: int,
    directed: bool,
    seed: int = 0,
) -> Graph:
    """Generate a deterministic graph with a wide integer weight range."""

    return make_random_graph(
        nodes=nodes,
        edges=edges,
        directed=directed,
        min_weight=1,
        max_weight=10_000,
        seed=seed,
    )


def make_negative_dag(*, nodes: int, edges: int, seed: int = 0) -> Graph:
    """Generate a DAG with negative edges and therefore no directed cycles."""

    if nodes <= 0:
        raise ValueError("nodes must be positive")
    rng = random.Random(seed)
    graph = Graph(directed=True)
    for node in range(nodes):
        graph.add_node(node)
    inserted = 0
    attempts = 0
    while inserted < edges and attempts < edges * 20 + 100:
        attempts += 1
        source = rng.randrange(nodes)
        target = rng.randrange(nodes)
        if source >= target:
            continue
        graph.add_edge(source, target, float(rng.randint(-5, 10)))
        inserted += 1
    return graph
