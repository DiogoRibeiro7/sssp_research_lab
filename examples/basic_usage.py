"""Basic use of SSSP Research Lab."""

from __future__ import annotations

from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.graph import Graph
from sssp_lab.utils import assert_same_distances


def main() -> None:
    graph = Graph.from_edges(
        [
            (0, 1, 2.0),
            (0, 2, 5.0),
            (1, 2, 1.0),
            (2, 3, 3.0),
        ],
        directed=True,
    )

    reference = dijkstra(graph, 0)
    stepped = delta_stepping(graph, 0, delta=2.0)
    assert_same_distances(stepped.distances, reference.distances)
    print(reference.distances)


if __name__ == "__main__":
    main()
