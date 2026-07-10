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


@dataclass(frozen=True, slots=True)
class ThorupComponent:
    """One connected component at a hierarchy scale."""

    component_id: int
    level: int
    scale: int
    nodes: frozenset[Node]
    parent: int | None = None


@dataclass(frozen=True, slots=True)
class ThorupComponentHierarchy:
    """Thresholded component hierarchy for undirected integer graphs."""

    levels: tuple[tuple[ThorupComponent, ...], ...]
    node_to_component: tuple[dict[Node, int], ...]

    def component_path(self, node: Node) -> tuple[int, ...]:
        """Return component ids containing ``node`` from low to high scales."""

        path: list[int] = []
        for level_map in self.node_to_component:
            if node not in level_map:
                raise ValueError(f"node {node!r} is not present in hierarchy")
            path.append(level_map[node])
        return tuple(path)


class _DisjointSet:
    def __init__(self, nodes: frozenset[Node]) -> None:
        self._parent = {node: node for node in nodes}

    def find(self, node: Node) -> Node:
        parent = self._parent[node]
        if parent != node:
            self._parent[node] = self.find(parent)
        return self._parent[node]

    def union(self, left: Node, right: Node) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if right_root < left_root:
            left_root, right_root = right_root, left_root
        self._parent[right_root] = left_root


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


def _default_component_scales(graph: Graph) -> tuple[int, ...]:
    max_weight = graph.max_edge_weight()
    if max_weight <= 0:
        return (1,)
    scales: list[int] = []
    scale = 1
    while scale < max_weight:
        scales.append(scale)
        scale *= 2
    scales.append(scale)
    return tuple(scales)


def _components_at_scale(graph: Graph, *, scale: int, level: int) -> tuple[ThorupComponent, ...]:
    disjoint_set = _DisjointSet(graph.nodes)
    for edge in graph.iter_edges():
        if edge.weight <= scale:
            disjoint_set.union(edge.source, edge.target)

    groups: dict[Node, set[Node]] = {}
    for node in graph.nodes:
        groups.setdefault(disjoint_set.find(node), set()).add(node)
    return tuple(
        ThorupComponent(
            component_id=(level << 32) + index,
            level=level,
            scale=scale,
            nodes=frozenset(nodes),
        )
        for index, (_, nodes) in enumerate(
            sorted(groups.items(), key=lambda item: min(item[1]))
        )
    )


def build_component_hierarchy(
    graph: Graph,
    *,
    scales: tuple[int, ...] | None = None,
) -> ThorupComponentHierarchy:
    """Build thresholded connected components over increasing edge scales."""

    validate_thorup_target_graph(graph)
    selected_scales = _default_component_scales(graph) if scales is None else scales
    if not selected_scales:
        raise ValueError("scales must not be empty")
    if any(scale <= 0 for scale in selected_scales):
        raise ValueError("scales must be positive")
    if tuple(sorted(selected_scales)) != tuple(selected_scales):
        raise ValueError("scales must be sorted in nondecreasing order")

    raw_levels = [
        _components_at_scale(graph, scale=scale, level=level)
        for level, scale in enumerate(selected_scales)
    ]
    node_to_component = tuple(
        {
            node: component.component_id
            for component in components
            for node in component.nodes
        }
        for components in raw_levels
    )
    levels: list[tuple[ThorupComponent, ...]] = []
    for level, components in enumerate(raw_levels):
        if level + 1 == len(raw_levels):
            levels.append(components)
            continue
        parent_map = node_to_component[level + 1]
        levels.append(
            tuple(
                ThorupComponent(
                    component_id=component.component_id,
                    level=component.level,
                    scale=component.scale,
                    nodes=component.nodes,
                    parent=parent_map[min(component.nodes)],
                )
                for component in components
            )
        )
    return ThorupComponentHierarchy(
        levels=tuple(levels),
        node_to_component=node_to_component,
    )


def thorup_integer_baseline(graph: Graph, source: Node) -> PathResult:
    """Run the integer SSSP baseline used by the Thorup lab.

    The function requires an undirected graph with positive integer weights and
    uses radix-heap Dijkstra as a correctness baseline. It does not implement
    Thorup's component hierarchy or word-RAM priority structure.
    """

    validate_thorup_target_graph(graph)
    return dijkstra_radix_heap(graph, source)
