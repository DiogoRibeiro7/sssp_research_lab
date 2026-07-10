"""Integer undirected SSSP lab inspired by Thorup's result.

Thorup's full linear-time algorithm uses component hierarchies and word-RAM
integer tricks. This module does not claim to reproduce that proof-level
algorithm. It provides implementable pieces that are useful when developing one:
integer bucket validation, component bucketing, and a radix-heap baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap
from sssp_lab.graph import Graph, Node, PathResult


@dataclass(frozen=True, slots=True)
class ComponentBucket:
    """A bucket of nodes grouped by distance scale."""

    scale: int
    nodes: frozenset[Node]


def build_distance_scale_buckets(result: PathResult, *, scale: int) -> tuple[ComponentBucket, ...]:
    """Group nodes by ``floor(distance / scale)``.

    This helper is useful for experimenting with component hierarchies. It is
    deliberately separated from the actual SSSP computation.
    """

    if scale <= 0:
        raise ValueError("scale must be positive")
    groups: dict[int, set[Node]] = {}
    for node, distance in result.distances.items():
        if distance == float("inf"):
            continue
        groups.setdefault(int(distance) // scale, set()).add(node)
    return tuple(ComponentBucket(scale=k, nodes=frozenset(v)) for k, v in sorted(groups.items()))


def validate_thorup_target_graph(graph: Graph) -> None:
    """Validate the graph assumptions for Thorup's target setting."""

    if graph.directed:
        raise ValueError("Thorup's target setting is undirected")
    graph.require_non_negative_weights()
    graph.require_integer_weights()
    for edge in graph.iter_edges():
        if edge.weight <= 0:
            raise ValueError("Thorup's target setting requires positive weights")


def thorup_integer_baseline(graph: Graph, source: Node) -> PathResult:
    """Run the integer SSSP baseline used by the Thorup lab.

    The function requires an undirected graph with positive integer weights and
    uses radix-heap Dijkstra as a correctness baseline. It does not implement
    Thorup's component hierarchy or word-RAM priority structure.
    """

    validate_thorup_target_graph(graph)
    return dijkstra_radix_heap(graph, source)
