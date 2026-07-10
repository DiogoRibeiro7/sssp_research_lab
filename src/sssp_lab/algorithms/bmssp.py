"""Bounded multi-source shortest-path primitive.

This is a practical primitive inspired by BMSSP. It computes shortest paths
from a set of sources but only explores labels strictly below a bound. It is
not the full recursive structure from the Duan et al. paper.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import isfinite

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


@dataclass(frozen=True, slots=True)
class BMSSPLevel:
    """One leaf bounded subproblem produced by recursive BMSSP splitting."""

    depth: int
    bound: Weight
    sources: frozenset[Node]
    settled: frozenset[Node]
    frontier: frozenset[Node]


@dataclass(frozen=True, slots=True)
class RecursiveBMSSPResult:
    """Result of recursive bounded multi-source exploration."""

    bound: Weight
    distances: dict[Node, Weight]
    predecessors: dict[Node, Node | None]
    settled: frozenset[Node]
    frontier: frozenset[Node]
    levels: tuple[BMSSPLevel, ...]


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


def _check_recursive_invariants(result: RecursiveBMSSPResult) -> None:
    bounded = BoundedMultiSourceResult(
        bound=result.bound,
        distances=result.distances,
        predecessors=result.predecessors,
        settled=result.settled,
        frontier=result.frontier,
    )
    _check_bounded_invariants(bounded)
    if not result.levels:
        raise AssertionError("recursive BMSSP must record at least one level")


def _merge_result(
    global_distances: dict[Node, Weight],
    global_predecessors: dict[Node, Node | None],
    result: BoundedMultiSourceResult | RecursiveBMSSPResult,
) -> None:
    for node, distance in result.distances.items():
        if distance < global_distances[node]:
            global_distances[node] = distance
            global_predecessors[node] = result.predecessors[node]


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


def recursive_bmssp(
    graph: Graph,
    sources: set[Node] | frozenset[Node],
    *,
    bound: Weight,
    depth: int = 2,
    split_factor: int = 2,
    source_distances: dict[Node, Weight] | None = None,
    debug: bool = False,
    stats: OperationStats | None = None,
) -> RecursiveBMSSPResult:
    """Explore bounded multi-source labels through recursive bound splitting.

    The routine recursively splits the absolute distance interval between the
    current source labels and ``bound``. Each leaf is still solved by the
    correctness-tested bounded primitive, so this is a faithful recursive
    scaffold for experiments rather than the paper's asymptotic data structure.
    """

    counters = stats if stats is not None else OperationStats()
    if depth < 0:
        raise ValueError("depth must be non-negative")
    if split_factor <= 1:
        raise ValueError("split_factor must be greater than one")
    if not sources:
        raise ValueError("sources must not be empty")
    if bound <= 0:
        raise ValueError("bound must be positive")
    graph.require_non_negative_weights()
    for source in sources:
        graph.require_node(source)

    initial_distances = (
        {source: 0.0 for source in sources}
        if source_distances is None
        else {source: float(source_distances[source]) for source in sources}
    )
    levels: list[BMSSPLevel] = []

    def solve(
        active_sources: set[Node],
        active_distances: dict[Node, Weight],
        active_bound: Weight,
        active_depth: int,
        level_depth: int,
    ) -> RecursiveBMSSPResult:
        if active_depth == 0 or not isfinite(float(active_bound)):
            leaf = bounded_multi_source_sssp(
                graph,
                active_sources,
                bound=active_bound,
                source_distances=active_distances,
                debug=debug,
                stats=counters,
            )
            levels.append(
                BMSSPLevel(
                    depth=level_depth,
                    bound=active_bound,
                    sources=frozenset(active_sources),
                    settled=leaf.settled,
                    frontier=leaf.frontier,
                )
            )
            return RecursiveBMSSPResult(
                bound=active_bound,
                distances=leaf.distances,
                predecessors=leaf.predecessors,
                settled=leaf.settled,
                frontier=leaf.frontier,
                levels=tuple(levels),
            )

        lower = min(float(active_distances[source]) for source in active_sources)
        midpoint = lower + ((float(active_bound) - lower) / split_factor)
        if midpoint <= lower or midpoint >= active_bound:
            return solve(active_sources, active_distances, active_bound, 0, level_depth)

        first = solve(
            active_sources,
            active_distances,
            midpoint,
            active_depth - 1,
            level_depth + 1,
        )
        global_distances = {node: float("inf") for node in graph.nodes}
        global_predecessors: dict[Node, Node | None] = {node: None for node in graph.nodes}
        _merge_result(global_distances, global_predecessors, first)

        if first.frontier:
            frontier_distances = {
                node: first.distances[node]
                for node in first.frontier
                if first.distances[node] < float("inf")
            }
            second = solve(
                set(frontier_distances),
                frontier_distances,
                active_bound,
                active_depth - 1,
                level_depth + 1,
            )
            _merge_result(global_distances, global_predecessors, second)
            settled = first.settled | second.settled
            frontier = second.frontier
        else:
            settled = first.settled
            frontier = first.frontier

        return RecursiveBMSSPResult(
            bound=active_bound,
            distances=global_distances,
            predecessors=global_predecessors,
            settled=frozenset(settled),
            frontier=frozenset(frontier),
            levels=tuple(levels),
        )

    result = solve(set(sources), initial_distances, bound, depth, 0)
    if debug:
        _check_recursive_invariants(result)
    return result
