"""Frontier-partition SSSP experiment.

This module explores the design idea that shortest paths can be found by
expanding bounded frontiers rather than by globally sorting all active labels.
It is inspired by recent directed-SSSP papers, but it is not a theorem-level
implementation of those papers.
"""

from __future__ import annotations

from dataclasses import dataclass

from sssp_lab.algorithms.bmssp import BoundedMultiSourceResult, bounded_multi_source_sssp
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Edge, Graph, Node, PathResult


@dataclass(frozen=True, slots=True)
class FrontierStats:
    """Diagnostics for frontier-partition SSSP."""

    rounds: int
    settled_counts: tuple[int, ...]
    frontier_counts: tuple[int, ...]
    incomplete_counts: tuple[int, ...] = ()
    boundary_edge_counts: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class FrontierRound:
    """One bounded exploration round in the frontier experiment."""

    bound: float
    sources: frozenset[Node]
    settled: frozenset[Node]
    frontier: frozenset[Node]


@dataclass(frozen=True, slots=True)
class IncompleteVertexIndex:
    """Snapshot of unresolved vertices and edges crossing into them."""

    complete: frozenset[Node]
    incomplete: frozenset[Node]
    boundary_edges: tuple[Edge, ...]
    boundary_labels: dict[Node, float]

    def frontier_sources(self) -> frozenset[Node]:
        """Return incomplete nodes that have finite labels from boundary edges."""

        return frozenset(self.boundary_labels)


def construct_frontier(result: BoundedMultiSourceResult) -> frozenset[Node]:
    """Return the next frontier from one bounded exploration result."""

    return result.frontier


def incomplete_vertices(graph: Graph, distances: dict[Node, float]) -> frozenset[Node]:
    """Return vertices whose labels are still infinite."""

    return frozenset(node for node in graph.nodes if distances[node] == float("inf"))


def build_incomplete_vertex_index(
    graph: Graph,
    distances: dict[Node, float],
    *,
    settled: set[Node] | frozenset[Node] | None = None,
) -> IncompleteVertexIndex:
    """Build an index over incomplete vertices and their boundary labels."""

    if set(distances) != set(graph.nodes):
        raise ValueError("distances must contain exactly the graph nodes")
    complete = (
        frozenset(node for node, distance in distances.items() if distance < float("inf"))
        if settled is None
        else frozenset(settled)
    )
    incomplete = frozenset(graph.nodes - complete)
    boundary_edges: list[Edge] = []
    boundary_labels: dict[Node, float] = {}
    for edge in graph.iter_edges():
        if edge.source not in complete or edge.target not in incomplete:
            continue
        source_distance = distances[edge.source]
        if source_distance == float("inf"):
            continue
        candidate = source_distance + edge.weight
        boundary_edges.append(edge)
        if candidate < boundary_labels.get(edge.target, float("inf")):
            boundary_labels[edge.target] = candidate
    return IncompleteVertexIndex(
        complete=complete,
        incomplete=incomplete,
        boundary_edges=tuple(boundary_edges),
        boundary_labels=boundary_labels,
    )


def check_frontier_invariants(
    *,
    sources: set[Node],
    distances: dict[Node, float],
    bound: float,
    growth: float,
) -> None:
    """Validate basic invariants for one frontier expansion round."""

    if bound <= 0:
        raise AssertionError("frontier bound must be positive")
    if growth <= 1:
        raise AssertionError("frontier growth must increase the bound")
    for source in sources:
        if distances[source] == float("inf"):
            raise AssertionError("frontier sources must have finite absolute labels")


def bounded_exploration_round(
    graph: Graph,
    sources: set[Node],
    *,
    bound: float,
    global_distances: dict[Node, float],
    debug: bool = False,
    stats: OperationStats | None = None,
) -> BoundedMultiSourceResult:
    """Run one bounded exploration round from absolute source labels."""

    missing = sorted(source for source in sources if source not in global_distances)
    if missing:
        raise ValueError(f"global_distances must include every source; missing {missing!r}")
    return bounded_multi_source_sssp(
        graph,
        sources,
        bound=bound,
        source_distances={node: global_distances[node] for node in sources},
        debug=debug,
        stats=stats,
    )


def frontier_partition_sssp(
    graph: Graph,
    source: Node,
    *,
    initial_bound: float = 1.0,
    growth: float = 2.0,
    debug: bool = False,
    stats: OperationStats | None = None,
) -> tuple[PathResult, FrontierStats]:
    """Compute SSSP by increasing bounded multi-source exploration windows.

    The function is useful for experiments on ordering pressure. It should be
    compared against Dijkstra in all benchmarks.
    """

    if initial_bound <= 0:
        raise ValueError("initial_bound must be positive")
    if growth <= 1:
        raise ValueError("growth must be greater than one")
    graph.require_node(source)
    graph.require_non_negative_weights()

    current_sources: set[Node] = {source}
    bound = float(initial_bound)
    global_distances: dict[Node, float] = {node: float("inf") for node in graph.nodes}
    global_predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
    global_distances[source] = 0.0
    settled_total: set[Node] = set()
    settled_counts: list[int] = []
    frontier_counts: list[int] = []
    incomplete_counts: list[int] = []
    boundary_edge_counts: list[int] = []
    rounds = 0

    while len(settled_total) < len(graph.nodes) and current_sources:
        rounds += 1
        if debug:
            check_frontier_invariants(
                sources=current_sources,
                distances=global_distances,
                bound=bound,
                growth=growth,
            )
        result = bounded_exploration_round(
            graph,
            current_sources,
            bound=bound,
            global_distances=global_distances,
            debug=debug,
            stats=stats,
        )
        for node, distance in result.distances.items():
            if distance < global_distances[node]:
                global_distances[node] = distance
                global_predecessors[node] = result.predecessors[node]
        settled_total.update(result.settled)
        settled_counts.append(len(result.settled))
        frontier_counts.append(len(result.frontier))
        incomplete_index = build_incomplete_vertex_index(
            graph,
            global_distances,
            settled=settled_total,
        )
        incomplete_counts.append(len(incomplete_index.incomplete))
        boundary_edge_counts.append(len(incomplete_index.boundary_edges))
        current_sources = set(construct_frontier(result))
        bound *= growth

        if rounds > max(len(graph.nodes) * 4, 16):
            # Defensive guard. Falling back to Dijkstra would hide the failure,
            # so we expose the issue to the caller.
            raise RuntimeError("frontier expansion did not converge")

    return (
        PathResult(source=source, distances=global_distances, predecessors=global_predecessors),
        FrontierStats(
            rounds=rounds,
            settled_counts=tuple(settled_counts),
            frontier_counts=tuple(frontier_counts),
            incomplete_counts=tuple(incomplete_counts),
            boundary_edge_counts=tuple(boundary_edge_counts),
        ),
    )
