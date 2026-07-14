"""Bounded multi-source shortest-path primitive.

This is a practical primitive inspired by BMSSP. It computes shortest paths
from a set of sources but only explores labels strictly below a bound. It is
not the full recursive structure from the Duan et al. paper.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import ceil, floor, isfinite, log2

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


@dataclass(frozen=True, slots=True)
class BMSSPParameters:
    """Paper-shaped BMSSP parameters derived from graph size."""

    node_count: int
    k: int
    t: int
    max_level: int

    def source_limit(self, level: int) -> int:
        """Return the approximate level source-set limit ``2 ** (level * t)``."""

        if level < 0:
            raise ValueError("level must be non-negative")
        return int(2 ** (level * self.t))

    def child_limit(self, level: int) -> int:
        """Return the recursive child source limit for ``level``."""

        if level < 0:
            raise ValueError("level must be non-negative")
        if level == 0:
            return 1
        return self.source_limit(level - 1)

    def to_config(self, *, level: int | None = None) -> BMSSPConfig:
        """Create a correctness-first driver config for ``level``."""

        active_level = self.max_level if level is None else level
        if active_level < 0:
            raise ValueError("level must be non-negative")
        return BMSSPConfig(
            k=self.k,
            child_limit=self.child_limit(active_level),
            work_limit=self.source_limit(active_level),
        )


@dataclass(frozen=True, slots=True)
class BMSSPConfig:
    """Configuration for the correctness-first paper-shaped BMSSP driver."""

    k: int = 2
    child_limit: int = 2
    work_limit: int = 32

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError("k must be positive")
        if self.child_limit <= 0:
            raise ValueError("child_limit must be positive")
        if self.work_limit <= 0:
            raise ValueError("work_limit must be positive")

    @classmethod
    def from_graph(cls, graph: Graph, *, level: int | None = None) -> BMSSPConfig:
        """Derive a correctness-first driver config from graph size."""

        return derive_bmssp_parameters(graph).to_config(level=level)


@dataclass(frozen=True, slots=True)
class PaperBMSSPResult:
    """Result from the correctness-first paper-shaped BMSSP driver."""

    boundary: float
    complete_vertices: frozenset[Node]
    partial: bool
    levels: tuple[BMSSPLevel, ...]


@dataclass(frozen=True, slots=True)
class PivotResult:
    """Result of a correctness-first BMSSP pivot search."""

    pivots: frozenset[Node]
    reached: frozenset[Node]
    partial: bool


class BMSSPQueue:
    """Correctness-first queue for paper-shaped BMSSP recursion.

    The interface mirrors the paper operations that the full BMSSP driver will
    need: insert/update one key, batch-prepend a group of smaller labels, and
    pull the keys with the smallest labels. The implementation uses a heap plus
    an active-label map, so it is not the paper's asymptotic block-list data
    structure.
    """

    def __init__(self) -> None:
        self._labels: dict[Node, float] = {}
        self._heap: list[tuple[float, Node]] = []

    def __bool__(self) -> bool:
        return bool(self._labels)

    def __len__(self) -> int:
        return len(self._labels)

    def insert(self, node: Node, label: Weight) -> None:
        """Insert ``node`` with ``label``, keeping the smallest label per node."""

        value = _validate_queue_label(label)
        current = self._labels.get(node)
        if current is not None and current <= value:
            return
        self._labels[node] = value
        heapq.heappush(self._heap, (value, node))

    def batch_prepend(self, labels: dict[Node, Weight]) -> None:
        """Insert labels that should precede the queue's current minimum."""

        updates: dict[Node, float] = {}
        for node, label in labels.items():
            value = _validate_queue_label(label)
            current = self._labels.get(node)
            if current is None or value < current:
                updates[node] = value

        if not updates:
            return

        current_min = self._peek_min()
        if current_min < float("inf") and any(value > current_min for value in updates.values()):
            raise ValueError("batch-prepended labels must not exceed the current queue minimum")

        for node, value in updates.items():
            self._labels[node] = value
            heapq.heappush(self._heap, (value, node))

    def pull(self, limit: int) -> tuple[frozenset[Node], float]:
        """Remove up to ``limit`` keys with the smallest labels.

        Returns:
            The pulled node set and the smallest remaining label, or infinity
            when the queue is empty.
        """

        if limit <= 0:
            raise ValueError("limit must be positive")

        pulled: set[Node] = set()
        while len(pulled) < limit:
            item = self._pop_active()
            if item is None:
                break
            _, node = item
            pulled.add(node)
        return frozenset(pulled), self._peek_min()

    def _peek_min(self) -> float:
        while self._heap:
            label, node = self._heap[0]
            if self._labels.get(node) == label:
                return label
            heapq.heappop(self._heap)
        return float("inf")

    def _pop_active(self) -> tuple[float, Node] | None:
        while self._heap:
            label, node = heapq.heappop(self._heap)
            if self._labels.get(node) != label:
                continue
            del self._labels[node]
            return label, node
        return None


def _validate_queue_label(label: Weight) -> float:
    if not isinstance(label, (int, float)):
        raise TypeError("label must be numeric")
    value = float(label)
    if not isfinite(value):
        raise ValueError("label must be finite")
    return value


def derive_bmssp_parameters(graph_or_node_count: Graph | int) -> BMSSPParameters:
    """Derive clamped paper-shaped BMSSP parameters from graph size."""

    if isinstance(graph_or_node_count, Graph):
        node_count = len(graph_or_node_count.nodes)
    elif isinstance(graph_or_node_count, int) and not isinstance(graph_or_node_count, bool):
        node_count = graph_or_node_count
    else:
        raise TypeError("graph_or_node_count must be a Graph or positive integer")
    if node_count <= 0:
        raise ValueError("node count must be positive")

    log_n = log2(max(node_count, 2))
    k = max(1, floor((log_n ** (1 / 3)) + 1e-12))
    t = max(1, floor((log_n ** (2 / 3)) + 1e-12))
    max_level = max(1, ceil(log_n / t))
    return BMSSPParameters(node_count=node_count, k=k, t=t, max_level=max_level)


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


def _require_source_labels(
    sources: set[Node] | frozenset[Node],
    labels: dict[Node, Weight],
    *,
    label_name: str,
) -> None:
    missing = sorted(source for source in sources if source not in labels)
    if missing:
        raise ValueError(f"{label_name} must include every source; missing {missing!r}")


def find_pivots(
    graph: Graph,
    sources: set[Node] | frozenset[Node],
    *,
    bound: Weight,
    k: int,
    labels: dict[Node, Weight],
    predecessors: dict[Node, Node | None],
    stats: OperationStats | None = None,
) -> PivotResult:
    """Run a correctness-first BMSSP pivot search.

    This helper follows the paper-shaped pivot routine from the implementation
    notes: perform ``k`` bounded relaxation rounds from ``sources``, stop early
    if the reached set grows too large, and otherwise choose source roots whose
    predecessor subtrees have size at least ``k``. It is not the paper's
    optimized implementation.
    """

    counters = stats if stats is not None else OperationStats()
    if not sources:
        raise ValueError("sources must not be empty")
    if bound <= 0:
        raise ValueError("bound must be positive")
    if k <= 0:
        raise ValueError("k must be positive")
    graph.require_non_negative_weights()
    if set(labels) != set(graph.nodes):
        raise ValueError("labels must contain exactly the graph nodes")
    if set(predecessors) != set(graph.nodes):
        raise ValueError("predecessors must contain exactly the graph nodes")
    for source in sources:
        graph.require_node(source)
        if labels[source] == float("inf"):
            raise ValueError("source labels must be finite")

    reached: set[Node] = set(sources)
    frontier: set[Node] = set(sources)
    for _ in range(k):
        next_frontier: set[Node] = set()
        for node in frontier:
            for edge in graph.neighbors(node):
                counters.relaxations += 1
                candidate = float(labels[node]) + edge.weight
                if candidate < labels[edge.target] and candidate < bound:
                    labels[edge.target] = candidate
                    predecessors[edge.target] = node
                    next_frontier.add(edge.target)
                    reached.add(edge.target)
        if len(reached) > k * len(sources):
            return PivotResult(
                pivots=frozenset(sources),
                reached=frozenset(reached),
                partial=True,
            )
        frontier = next_frontier
        if not frontier:
            break

    subtree_sizes = _predecessor_subtree_sizes(
        roots=frozenset(sources),
        reached=frozenset(reached),
        predecessors=predecessors,
    )
    pivots = frozenset(root for root, size in subtree_sizes.items() if size >= k)
    return PivotResult(pivots=pivots, reached=frozenset(reached), partial=False)


def _predecessor_subtree_sizes(
    *,
    roots: frozenset[Node],
    reached: frozenset[Node],
    predecessors: dict[Node, Node | None],
) -> dict[Node, int]:
    children: dict[Node, list[Node]] = {node: [] for node in reached}
    for node in reached:
        predecessor = predecessors[node]
        if predecessor in reached:
            children.setdefault(predecessor, []).append(node)

    subtree_sizes: dict[Node, int] = {}
    for root in roots:
        stack = [root]
        seen: set[Node] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(children.get(node, ()))
        subtree_sizes[root] = len(seen)
    return subtree_sizes


def bmssp_base_case(
    graph: Graph,
    source: Node,
    *,
    bound: Weight,
    k: int,
    labels: dict[Node, Weight],
    predecessors: dict[Node, Node | None],
    complete: set[Node] | None = None,
    stats: OperationStats | None = None,
) -> tuple[float, frozenset[Node]]:
    """Solve a level-zero paper-shaped BMSSP subproblem.

    The helper performs a bounded Dijkstra-style expansion from one source,
    mutating shared ``labels`` and ``predecessors`` maps. It stops after at most
    ``k + 1`` settled vertices or when the next queue label reaches ``bound``.
    The returned boundary is ``bound`` for a complete base case and the largest
    settled label for a partial base case.
    """

    counters = stats if stats is not None else OperationStats()
    if bound <= 0:
        raise ValueError("bound must be positive")
    if k <= 0:
        raise ValueError("k must be positive")
    graph.require_non_negative_weights()
    graph.require_node(source)
    if set(labels) != set(graph.nodes):
        raise ValueError("labels must contain exactly the graph nodes")
    if set(predecessors) != set(graph.nodes):
        raise ValueError("predecessors must contain exactly the graph nodes")
    if labels[source] == float("inf"):
        raise ValueError("source label must be finite")

    active_complete = set() if complete is None else complete
    queue: list[tuple[float, Node]] = [(float(labels[source]), source)]
    counters.queue_pushes += 1
    settled: set[Node] = set()
    next_boundary = float(bound)

    while queue and len(settled) < k + 1:
        distance, node = heapq.heappop(queue)
        counters.queue_pops += 1
        if distance != labels[node]:
            counters.stale_pops += 1
            continue
        if distance >= bound:
            next_boundary = min(next_boundary, distance)
            break
        if node in settled:
            counters.stale_pops += 1
            continue

        active_complete.add(node)
        settled.add(node)
        counters.settled_nodes += 1
        for edge in graph.neighbors(node):
            counters.relaxations += 1
            candidate = distance + edge.weight
            if candidate < labels[edge.target]:
                labels[edge.target] = candidate
                predecessors[edge.target] = node
                if candidate < bound:
                    heapq.heappush(queue, (candidate, edge.target))
                    counters.queue_pushes += 1
                else:
                    next_boundary = min(next_boundary, candidate)

    if len(settled) <= k:
        return next_boundary, frozenset(settled)
    return max(float(labels[node]) for node in settled), frozenset(settled)


def paper_bmssp(
    graph: Graph,
    sources: set[Node] | frozenset[Node],
    *,
    bound: Weight,
    level: int,
    labels: dict[Node, Weight],
    predecessors: dict[Node, Node | None],
    config: BMSSPConfig | None = None,
    complete: set[Node] | None = None,
    debug: bool = False,
    stats: OperationStats | None = None,
) -> PaperBMSSPResult:
    """Run a correctness-first, paper-shaped recursive BMSSP subproblem.

    This driver composes :func:`find_pivots`, :class:`BMSSPQueue`, and
    :func:`bmssp_base_case` over shared label state. It is intentionally
    conservative: all reached vertices are considered as candidate child
    sources so the helper remains a correctness scaffold rather than relying on
    the paper's still-unimplemented pruning data structure.
    """

    active_config = config if config is not None else BMSSPConfig()
    counters = stats if stats is not None else OperationStats()
    active_complete = set() if complete is None else complete
    _validate_paper_bmssp_inputs(
        graph,
        sources,
        bound=bound,
        level=level,
        labels=labels,
        predecessors=predecessors,
    )

    levels: list[BMSSPLevel] = []

    def solve(
        active_sources: frozenset[Node],
        active_bound: float,
        active_level: int,
        depth: int,
    ) -> PaperBMSSPResult:
        if active_level == 0:
            base_complete_here: set[Node] = set()
            boundary = active_bound
            for source in sorted(active_sources):
                source_boundary, settled = bmssp_base_case(
                    graph,
                    source,
                    bound=active_bound,
                    k=active_config.k,
                    labels=labels,
                    predecessors=predecessors,
                    complete=active_complete,
                    stats=counters,
                )
                boundary = min(boundary, source_boundary)
                base_complete_here.update(settled)
            level_record = BMSSPLevel(
                depth=depth,
                bound=active_bound,
                sources=active_sources,
                settled=frozenset(base_complete_here),
                frontier=frozenset(
                    node for node in graph.nodes if labels[node] >= boundary and labels[node] < active_bound
                ),
            )
            levels.append(level_record)
            return PaperBMSSPResult(
                boundary=boundary,
                complete_vertices=frozenset(base_complete_here),
                partial=boundary < active_bound,
                levels=tuple(levels),
            )

        pivot_result = find_pivots(
            graph,
            active_sources,
            bound=active_bound,
            k=active_config.k,
            labels=labels,
            predecessors=predecessors,
            stats=counters,
        )
        queue = BMSSPQueue()
        for node in pivot_result.pivots | pivot_result.reached:
            if labels[node] < active_bound:
                queue.insert(node, labels[node])

        complete_here: set[Node] = set()
        boundary = active_bound
        while queue and len(complete_here) < active_config.work_limit:
            child_sources, child_bound = queue.pull(active_config.child_limit)
            if not child_sources:
                break
            if child_bound == float("inf"):
                child_bound = active_bound
            if any(labels[source] >= child_bound for source in child_sources):
                child_bound = active_bound
            child = solve(
                child_sources,
                min(child_bound, active_bound),
                active_level - 1,
                depth + 1,
            )
            complete_here.update(child.complete_vertices)
            boundary = min(boundary, child.boundary)

            prepend_labels: dict[Node, Weight] = {}
            for node in child.complete_vertices:
                for edge in graph.neighbors(node):
                    counters.relaxations += 1
                    candidate = labels[node] + edge.weight
                    if candidate < labels[edge.target] and candidate < active_bound:
                        labels[edge.target] = candidate
                        predecessors[edge.target] = node
                        prepend_labels[edge.target] = candidate
            _insert_relaxed_labels(queue, prepend_labels)
            for node, label in labels.items():
                if node not in active_complete and label < active_bound:
                    queue.insert(node, label)

        if not queue:
            boundary = active_bound
        partial = boundary < active_bound or bool(queue)
        level_record = BMSSPLevel(
            depth=depth,
            bound=active_bound,
            sources=active_sources,
            settled=frozenset(complete_here),
            frontier=frozenset(
                node for node in graph.nodes if labels[node] >= boundary and labels[node] < active_bound
            ),
        )
        levels.append(level_record)
        if debug:
            _check_paper_bmssp_result(
                graph,
                labels,
                predecessors,
                complete_here,
                boundary=boundary,
                bound=active_bound,
            )
        return PaperBMSSPResult(
            boundary=boundary,
            complete_vertices=frozenset(complete_here),
            partial=partial,
            levels=tuple(levels),
        )

    return solve(frozenset(sources), float(bound), level, 0)


def _validate_paper_bmssp_inputs(
    graph: Graph,
    sources: set[Node] | frozenset[Node],
    *,
    bound: Weight,
    level: int,
    labels: dict[Node, Weight],
    predecessors: dict[Node, Node | None],
) -> None:
    if not sources:
        raise ValueError("sources must not be empty")
    if bound <= 0:
        raise ValueError("bound must be positive")
    if level < 0:
        raise ValueError("level must be non-negative")
    graph.require_non_negative_weights()
    if set(labels) != set(graph.nodes):
        raise ValueError("labels must contain exactly the graph nodes")
    if set(predecessors) != set(graph.nodes):
        raise ValueError("predecessors must contain exactly the graph nodes")
    for source in sources:
        graph.require_node(source)
        if labels[source] == float("inf"):
            raise ValueError("source labels must be finite")


def _insert_relaxed_labels(queue: BMSSPQueue, labels: dict[Node, Weight]) -> None:
    try:
        queue.batch_prepend(labels)
    except ValueError:
        for node, label in labels.items():
            queue.insert(node, label)


def _check_paper_bmssp_result(
    graph: Graph,
    labels: dict[Node, Weight],
    predecessors: dict[Node, Node | None],
    complete_vertices: set[Node],
    *,
    boundary: float,
    bound: float,
) -> None:
    if boundary > bound:
        raise AssertionError("BMSSP boundary must not exceed the input bound")
    if set(labels) != set(graph.nodes):
        raise AssertionError("labels must contain exactly the graph nodes")
    if set(predecessors) != set(graph.nodes):
        raise AssertionError("predecessors must contain exactly the graph nodes")
    for node in complete_vertices:
        if labels[node] >= bound:
            raise AssertionError("complete BMSSP vertices must have labels below the input bound")
        _check_predecessor_chain(graph, labels, predecessors, node)


def _check_predecessor_chain(
    graph: Graph,
    labels: dict[Node, Weight],
    predecessors: dict[Node, Node | None],
    node: Node,
) -> None:
    seen: set[Node] = set()
    current = node
    while predecessors[current] is not None:
        if current in seen:
            raise AssertionError("BMSSP predecessor chain must be acyclic")
        seen.add(current)
        predecessor = predecessors[current]
        if predecessor not in labels:
            raise AssertionError("BMSSP predecessor must be present in labels")
        edge_weights = _edge_weights_between(graph, predecessor, current)
        if not edge_weights:
            raise AssertionError("BMSSP predecessor must correspond to an edge")
        if all(
            abs((float(labels[predecessor]) + edge_weight) - float(labels[current])) > 1e-9
            for edge_weight in edge_weights
        ):
            raise AssertionError("BMSSP predecessor edge must explain the label")
        current = predecessor


def _edge_weights_between(graph: Graph, source: Node, target: Node) -> tuple[float, ...]:
    return tuple(edge.weight for edge in graph.neighbors(source) if edge.target == target)


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
    if source_distances is not None:
        _require_source_labels(sources, source_distances, label_name="source_distances")

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
    if source_distances is not None:
        _require_source_labels(sources, source_distances, label_name="source_distances")

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
