"""Bounded multi-source shortest-path primitive.

This is a practical primitive inspired by BMSSP. It computes shortest paths
from a set of sources but only explores labels strictly below a bound. It is
not the full recursive structure from the Duan et al. paper.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph, Node, Weight


@dataclass(frozen=True, slots=True)
class BoundedMultiSourceResult:
    """Result of bounded multi-source exploration."""

    bound: Weight
    distances: dict[Node, Weight]
    predecessors: dict[Node, Node | None]
    settled: frozenset[Node]
    frontier: frozenset[Node]


def _check_bounded_invariants(result: BoundedMultiSourceResult) -> None:
    """Validate runtime invariants for bounded exploration."""

    for node in result.settled:
        if result.distances[node] >= result.bound:
            raise AssertionError("settled nodes must have labels below the bound")
    for node in result.frontier:
        if result.distances[node] < result.bound:
            raise AssertionError("frontier nodes must have labels at or above the bound")
    if result.settled & result.frontier:
        raise AssertionError("settled and frontier sets must be disjoint")


def bounded_multi_source_sssp(
    graph: Graph,
    sources: set[Node] | frozenset[Node],
    *,
    bound: Weight,
    source_distances: dict[Node, Weight] | None = None,
    debug: bool = False,
    stats: OperationStats | None = None,
) -> BoundedMultiSourceResult:
    """Explore all paths from ``sources`` with distance below ``bound``.

    Args:
        graph: Weighted graph with non-negative weights.
        sources: One or more source nodes.
        bound: Strict absolute upper exploration bound. Labels ``>= bound`` are
            placed in the frontier and not settled.
        source_distances: Optional absolute distance for each source. When
            omitted, all sources start at zero.
        debug: Validate bounded-exploration invariants before returning.
        stats: Optional mutable operation counters.
    """

    counters = stats if stats is not None else OperationStats()
    if not sources:
        raise ValueError("sources must not be empty")
    if bound <= 0:
        raise ValueError("bound must be positive")
    graph.require_non_negative_weights()
    for source in sources:
        graph.require_node(source)

    distances: dict[Node, Weight] = {node: float("inf") for node in graph.nodes}
    predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
    queue: list[tuple[float, Node]] = []
    for source in sources:
        start_distance = 0.0 if source_distances is None else float(source_distances[source])
        distances[source] = start_distance
        heapq.heappush(queue, (start_distance, source))
        counters.queue_pushes += 1

    settled: set[Node] = set()
    frontier: set[Node] = set()

    while queue:
        distance, node = heapq.heappop(queue)
        counters.queue_pops += 1
        if distance != distances[node]:
            counters.stale_pops += 1
            continue
        if distance >= bound:
            frontier.add(node)
            continue
        settled.add(node)
        counters.settled_nodes += 1
        for edge in graph.neighbors(node):
            counters.relaxations += 1
            candidate = distance + edge.weight
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                predecessors[edge.target] = node
                if candidate < bound:
                    heapq.heappush(queue, (candidate, edge.target))
                    counters.queue_pushes += 1
                else:
                    frontier.add(edge.target)

    result = BoundedMultiSourceResult(
        bound=bound,
        distances=distances,
        predecessors=predecessors,
        settled=frozenset(settled),
        frontier=frozenset(frontier),
    )
    if debug:
        _check_bounded_invariants(result)
    return result
