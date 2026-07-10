"""Negative-weight shortest-path baselines.

The near-linear negative-weight SSSP paper is a research-frontier algorithm.
This module provides correct baselines and Johnson-style reweighting utilities
that can be used while implementing the full paper.
"""

from __future__ import annotations

from dataclasses import dataclass

from sssp_lab.algorithms.bellman_ford import bellman_ford
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.graph import Graph, Node, PathResult


@dataclass(frozen=True, slots=True)
class PotentialResult:
    """Johnson potential values."""

    potentials: dict[Node, float]
    reweighted_graph: Graph


def johnson_potentials(graph: Graph) -> PotentialResult:
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

    bf = bellman_ford(augmented, super_source)
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


def johnson_sssp(graph: Graph, source: Node) -> PathResult:
    """Compute SSSP with Johnson reweighting and Dijkstra.

    This handles negative edges if there is no reachable negative cycle. It is
    not near-linear in the same sense as Bernstein-Nanongkai-Wulff-Nilsen.
    """

    graph.require_node(source)
    potential_result = johnson_potentials(graph)
    weighted = dijkstra(potential_result.reweighted_graph, source)
    distances: dict[Node, float] = {}
    for node, distance in weighted.distances.items():
        if distance == float("inf"):
            distances[node] = float("inf")
        else:
            distances[node] = (
                distance
                - potential_result.potentials[source]
                + potential_result.potentials[node]
            )
    return PathResult(source=source, distances=distances, predecessors=weighted.predecessors)


def negative_weight_reference_sssp(graph: Graph, source: Node) -> PathResult:
    """Correct reference for graphs with negative weights."""

    return bellman_ford(graph, source)
