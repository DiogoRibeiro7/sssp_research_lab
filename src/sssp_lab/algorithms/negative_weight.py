"""Negative-weight shortest-path baselines.

The near-linear negative-weight SSSP paper is a research-frontier algorithm.
This module provides correct baselines and Johnson-style reweighting utilities
that can be used while implementing the full paper.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from sssp_lab.algorithms.bellman_ford import bellman_ford
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Edge, Graph, Node, PathResult


@dataclass(frozen=True, slots=True)
class PotentialResult:
    """Johnson potential values."""

    potentials: dict[Node, float]
    reweighted_graph: Graph


@dataclass(frozen=True, slots=True)
class SignDecomposition:
    """Toy decomposition separating negative and non-negative edges."""

    negative_edges: tuple[Edge, ...]
    non_negative_edges: tuple[Edge, ...]


@dataclass(frozen=True, slots=True)
class ScaleLayer:
    """Toy edge layer grouped by absolute weight scale."""

    scale: int
    edges: tuple[Edge, ...]


@dataclass(frozen=True, slots=True)
class NegativeDecompositionRound:
    """One cumulative scale round in the negative-weight experiment."""

    scale: int
    edges: tuple[Edge, ...]
    sampled_vertices: frozenset[Node]
    reachable: frozenset[Node]


@dataclass(frozen=True, slots=True)
class NegativeDecompositionExperiment:
    """Diagnostics and exact result for a simplified decomposition experiment."""

    result: PathResult
    sign_decomposition: SignDecomposition
    rounds: tuple[NegativeDecompositionRound, ...]


def decompose_by_edge_sign(graph: Graph) -> SignDecomposition:
    """Split edges by sign for deterministic negative-weight experiments."""

    negative: list[Edge] = []
    non_negative: list[Edge] = []
    for edge in graph.iter_edges():
        if edge.weight < 0:
            negative.append(edge)
        else:
            non_negative.append(edge)
    return SignDecomposition(negative_edges=tuple(negative), non_negative_edges=tuple(non_negative))


def scale_layers(graph: Graph, *, scale: int) -> tuple[ScaleLayer, ...]:
    """Group edges by ``floor(abs(weight) / scale)`` for toy scale handling."""

    if scale <= 0:
        raise ValueError("scale must be positive")
    groups: dict[int, list[Edge]] = {}
    for edge in graph.iter_edges():
        groups.setdefault(int(abs(edge.weight)) // scale, []).append(edge)
    return tuple(ScaleLayer(scale=key, edges=tuple(edges)) for key, edges in sorted(groups.items()))


def seeded_vertex_sample(graph: Graph, *, probability: float, seed: int) -> frozenset[Node]:
    """Sample vertices with a fixed seed for reproducible randomized experiments."""

    if not 0 <= probability <= 1:
        raise ValueError("probability must be in [0, 1]")
    rng = random.Random(seed)
    return frozenset(node for node in sorted(graph.nodes) if rng.random() <= probability)


def check_against_bellman_ford(graph: Graph, source: Node, result: PathResult) -> None:
    """Raise if ``result`` disagrees with Bellman-Ford distances."""

    reference = bellman_ford(graph, source)
    if dict(result.distances) != dict(reference.distances):
        raise AssertionError("shortest-path distances differ from Bellman-Ford")


def _graph_from_edges_with_nodes(nodes: frozenset[Node], edges: tuple[Edge, ...]) -> Graph:
    graph = Graph(directed=True)
    for node in nodes:
        graph.add_node(node)
    for edge in edges:
        graph.add_edge(edge.source, edge.target, edge.weight)
    return graph


def _source_reachable_nodes(graph: Graph, source: Node) -> frozenset[Node]:
    graph.require_node(source)
    reachable: set[Node] = {source}
    queue: deque[Node] = deque([source])
    while queue:
        node = queue.popleft()
        for edge in graph.neighbors(node):
            if edge.target not in reachable:
                reachable.add(edge.target)
                queue.append(edge.target)
    return frozenset(reachable)


def _reachable_subgraph(graph: Graph, source: Node) -> Graph:
    reachable = _source_reachable_nodes(graph, source)
    edges = tuple(
        edge
        for edge in graph.iter_edges()
        if edge.source in reachable and edge.target in reachable
    )
    return _graph_from_edges_with_nodes(reachable, edges)


def johnson_potentials(graph: Graph, *, stats: OperationStats | None = None) -> PotentialResult:
    """Compute Johnson potentials and a non-negative reweighted graph.

    A synthetic super-source is connected to every node with a zero-weight edge.
    Bellman-Ford distances from the super-source become the potentials.
    """

    super_source = max(graph.nodes, default=-1) + 1
    augmented = Graph(directed=True)
    for node in graph.nodes:
        augmented.add_node(node)
        augmented.add_edge(super_source, node, 0.0)
    augmented.add_node(super_source)
    for edge in graph.iter_edges():
        augmented.add_edge(edge.source, edge.target, edge.weight)

    bf = bellman_ford(augmented, super_source, stats=stats)
    potentials = {node: bf.distances[node] for node in graph.nodes}

    reweighted = Graph(directed=True)
    for node in graph.nodes:
        reweighted.add_node(node)
    for edge in graph.iter_edges():
        new_weight = edge.weight + potentials[edge.source] - potentials[edge.target]
        # Numerical noise can create tiny negatives near zero.
        if -1e-12 < new_weight < 0:
            new_weight = 0.0
        reweighted.add_edge(edge.source, edge.target, new_weight)
    return PotentialResult(potentials=potentials, reweighted_graph=reweighted)


def johnson_sssp(
    graph: Graph,
    source: Node,
    *,
    stats: OperationStats | None = None,
) -> PathResult:
    """Compute SSSP with Johnson reweighting and Dijkstra.

    This handles negative edges if there is no reachable negative cycle. It is
    not near-linear in the same sense as Bernstein-Nanongkai-Wulff-Nilsen.
    """

    graph.require_node(source)
    reachable_graph = _reachable_subgraph(graph, source)
    potential_result = johnson_potentials(reachable_graph, stats=stats)
    weighted = dijkstra(potential_result.reweighted_graph, source, stats=stats)
    distances: dict[Node, float] = {node: float("inf") for node in graph.nodes}
    predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
    for node, distance in weighted.distances.items():
        if distance == float("inf"):
            distances[node] = float("inf")
        else:
            distances[node] = (
                distance
                - potential_result.potentials[source]
                + potential_result.potentials[node]
            )
        predecessors[node] = weighted.predecessors[node]
    return PathResult(source=source, distances=distances, predecessors=predecessors)


def negative_weight_reference_sssp(
    graph: Graph,
    source: Node,
    *,
    stats: OperationStats | None = None,
) -> PathResult:
    """Correct reference for graphs with negative weights."""

    return bellman_ford(graph, source, stats=stats)


def negative_decomposition_experiment(
    graph: Graph,
    source: Node,
    *,
    scale: int,
    sample_probability: float = 0.5,
    seed: int = 0,
    stats: OperationStats | None = None,
) -> NegativeDecompositionExperiment:
    """Run a deterministic layered decomposition experiment for negative SSSP.

    The rounds expose how cumulative absolute-weight layers grow reachability.
    The returned shortest-path result is still computed exactly through Johnson
    reweighting and checked against Bellman-Ford.
    """

    if scale <= 0:
        raise ValueError("scale must be positive")
    graph.require_node(source)
    sign_decomposition = decompose_by_edge_sign(graph)
    layers = scale_layers(graph, scale=scale)
    rounds: list[NegativeDecompositionRound] = []
    cumulative_edges: list[Edge] = []
    for layer in layers:
        cumulative_edges.extend(layer.edges)
        subgraph = _graph_from_edges_with_nodes(graph.nodes, tuple(cumulative_edges))
        partial = negative_weight_reference_sssp(subgraph, source, stats=stats)
        rounds.append(
            NegativeDecompositionRound(
                scale=layer.scale,
                edges=layer.edges,
                sampled_vertices=seeded_vertex_sample(
                    subgraph,
                    probability=sample_probability,
                    seed=seed + layer.scale,
                ),
                reachable=frozenset(
                    node for node, distance in partial.distances.items() if distance < float("inf")
                ),
            )
        )

    result = johnson_sssp(graph, source, stats=stats)
    check_against_bellman_ford(graph, source, result)
    return NegativeDecompositionExperiment(
        result=result,
        sign_decomposition=sign_decomposition,
        rounds=tuple(rounds),
    )
