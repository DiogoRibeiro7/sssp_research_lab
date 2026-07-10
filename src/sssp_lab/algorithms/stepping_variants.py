"""Experimental stepping variants.

This module is intentionally conservative. It exposes useful policy hooks for
experiments without pretending to reproduce every algorithmic detail from the
stepping-algorithm literature.
"""

from __future__ import annotations

from collections.abc import Callable

from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.graph import Graph, Node, PathResult

DeltaPolicy = Callable[[Graph], float]


def median_weight_delta(graph: Graph) -> float:
    """Return a robust default Δ based on the median edge weight."""

    weights = sorted(edge.weight for edge in graph.iter_edges() if edge.weight >= 0)
    if not weights:
        return 1.0
    return max(weights[len(weights) // 2], 1e-12)


def max_degree_delta(graph: Graph) -> float:
    """Return a simple Δ policy using average edge weight and maximum degree."""

    weights = [edge.weight for edge in graph.iter_edges() if edge.weight >= 0]
    if not weights:
        return 1.0
    max_degree = max((len(graph.neighbors(node)) for node in graph.nodes), default=1)
    return max(sum(weights) / len(weights) / max(max_degree, 1), 1e-12)


def policy_delta_stepping(
    graph: Graph,
    source: Node,
    *,
    delta_policy: DeltaPolicy = median_weight_delta,
) -> PathResult:
    """Run Δ-stepping using a user-supplied Δ policy."""

    delta = delta_policy(graph)
    return delta_stepping(graph, source, delta=delta)
