from __future__ import annotations

import pytest

from sssp_lab.algorithms.bellman_ford import NegativeCycleError, bellman_ford
from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dial import dial_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap
from sssp_lab.algorithms.stepping_variants import policy_delta_stepping
from sssp_lab.graph import Graph
from sssp_lab.utils import assert_same_distances, make_random_graph


def test_dijkstra_path_reconstruction() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 3)],
        directed=True,
    )
    result = dijkstra(graph, 0)
    assert result.distances[3] == 6
    assert result.path_to(3) == [0, 1, 2, 3]


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_non_negative_algorithms_match_dijkstra(seed: int) -> None:
    graph = make_random_graph(
        nodes=30,
        edges=120,
        directed=True,
        min_weight=1,
        max_weight=10,
        seed=seed,
    )
    reference = dijkstra(graph, 0)
    for result in [
        dial_sssp(graph, 0),
        dijkstra_radix_heap(graph, 0),
        delta_stepping(graph, 0, delta=3.0),
        policy_delta_stepping(graph, 0),
    ]:
        assert_same_distances(result.distances, reference.distances)


def test_bellman_ford_handles_negative_edges() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, -2), (0, 2, 5), (2, 3, 1)],
        directed=True,
    )
    result = bellman_ford(graph, 0)
    assert result.distances[3] == 0


def test_bellman_ford_detects_negative_cycle() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, -3), (2, 1, 1)],
        directed=True,
    )
    with pytest.raises(NegativeCycleError):
        bellman_ford(graph, 0)
