"""Graph primitives used by the shortest-path algorithms.

The implementation deliberately keeps the graph type small. It is easier to
verify shortest-path algorithms when the data model has few moving parts.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

Node = int
Weight = float


@dataclass(frozen=True, slots=True)
class Edge:
    """A weighted edge.

    Attributes:
        source: Source node id.
        target: Target node id.
        weight: Edge weight.
    """

    source: Node
    target: Node
    weight: Weight

    def __post_init__(self) -> None:
        if not isinstance(self.source, int):
            raise TypeError("source must be an int")
        if not isinstance(self.target, int):
            raise TypeError("target must be an int")
        if not isinstance(self.weight, (int, float)):
            raise TypeError("weight must be numeric")
        if not isfinite(float(self.weight)):
            raise ValueError("weight must be finite")


@dataclass(frozen=True, slots=True)
class PathResult:
    """Result returned by shortest-path algorithms.

    Attributes:
        source: Source node used by the algorithm.
        distances: Map from node to shortest distance estimate.
        predecessors: Map from node to predecessor in the shortest-path tree.
    """

    source: Node
    distances: Mapping[Node, Weight]
    predecessors: Mapping[Node, Node | None]

    def path_to(self, target: Node) -> list[Node]:
        """Reconstruct one shortest path from the source to ``target``.

        Args:
            target: Node whose path should be reconstructed.

        Returns:
            A list of node ids. If the target is unreachable, an empty list is
            returned.
        """

        if target not in self.distances or self.distances[target] == float("inf"):
            return []

        path: list[Node] = []
        current: Node | None = target
        seen: set[Node] = set()
        while current is not None:
            if current in seen:
                raise RuntimeError("cycle detected in predecessor chain")
            seen.add(current)
            path.append(current)
            current = self.predecessors.get(current)
        path.reverse()
        return path


class Graph:
    """Weighted graph with integer node ids.

    Args:
        directed: If ``False``, every inserted edge is mirrored.
    """

    def __init__(self, *, directed: bool = True) -> None:
        if not isinstance(directed, bool):
            raise TypeError("directed must be a bool")
        self.directed = directed
        self._adj: dict[Node, list[Edge]] = {}
        self._nodes: set[Node] = set()

    @classmethod
    def from_edges(
        cls,
        edges: Iterable[tuple[Node, Node, Weight] | Edge],
        *,
        directed: bool = True,
    ) -> Graph:
        """Create a graph from weighted edges."""

        graph = cls(directed=directed)
        for raw_edge in edges:
            if isinstance(raw_edge, Edge):
                graph.add_edge(raw_edge.source, raw_edge.target, raw_edge.weight)
            else:
                source, target, weight = raw_edge
                graph.add_edge(source, target, weight)
        return graph

    def add_node(self, node: Node) -> None:
        """Add a node if it does not already exist."""

        if not isinstance(node, int):
            raise TypeError("node must be an int")
        self._nodes.add(node)
        self._adj.setdefault(node, [])

    def add_edge(self, source: Node, target: Node, weight: Weight) -> None:
        """Add a weighted edge to the graph."""

        edge = Edge(source, target, float(weight))
        self.add_node(source)
        self.add_node(target)
        self._adj[source].append(edge)
        if not self.directed:
            self._adj[target].append(Edge(target, source, float(weight)))

    @property
    def nodes(self) -> frozenset[Node]:
        """Nodes present in the graph."""

        return frozenset(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of stored directed edges."""

        return sum(len(edges) for edges in self._adj.values())

    def neighbors(self, node: Node) -> Sequence[Edge]:
        """Return outgoing edges from ``node``."""

        return tuple(self._adj.get(node, ()))

    def iter_edges(self) -> Iterator[Edge]:
        """Iterate over stored directed edges."""

        for edges in self._adj.values():
            yield from edges

    def reversed(self) -> Graph:
        """Return the graph with all directed edges reversed."""

        reverse = Graph(directed=True)
        for node in self.nodes:
            reverse.add_node(node)
        for edge in self.iter_edges():
            reverse.add_edge(edge.target, edge.source, edge.weight)
        return reverse

    def require_node(self, source: Node) -> None:
        """Raise if ``source`` is not present in the graph."""

        if source not in self._nodes:
            raise ValueError(f"source node {source!r} is not present in graph")

    def require_non_negative_weights(self) -> None:
        """Raise if any edge weight is negative."""

        for edge in self.iter_edges():
            if edge.weight < 0:
                raise ValueError("algorithm requires non-negative edge weights")

    def require_integer_weights(self) -> None:
        """Raise if any edge weight is not an integer value."""

        for edge in self.iter_edges():
            if int(edge.weight) != edge.weight:
                raise ValueError("algorithm requires integer-valued weights")

    def max_edge_weight(self) -> int:
        """Return the maximum edge weight as an integer."""

        self.require_integer_weights()
        weights = [int(edge.weight) for edge in self.iter_edges()]
        return max(weights, default=0)
