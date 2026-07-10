from __future__ import annotations

from collections.abc import Callable

import pytest

from sssp_lab.algorithms.bellman_ford import bellman_ford
from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dial import dial_circular_sssp, dial_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap
from sssp_lab.algorithms.negative_weight import johnson_sssp
from sssp_lab.algorithms.stepping_variants import policy_delta_stepping
from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import (
    assert_same_distances,
    make_equal_weight_graph,
    make_erdos_renyi_graph,
    make_grid_graph,
    make_heavy_tailed_graph,
    make_layered_dag,
    make_negative_dag,
    make_random_graph,
    make_road_like_graph,
    make_wide_integer_weight_graph,
)

SsspRunner = Callable[[Graph, Node], PathResult]


def assert_shortest_path_invariants(graph: Graph, result: PathResult) -> None:
    """Check distance labels and predecessor edges for a shortest-path result."""

    assert set(result.distances) == graph.nodes
    assert result.distances[result.source] == 0
    edges_by_pair: dict[tuple[Node, Node], float] = {}
    for edge in graph.iter_edges():
        pair = (edge.source, edge.target)
        current = edges_by_pair.get(pair)
        if current is None or edge.weight < current:
            edges_by_pair[pair] = edge.weight

    for edge in graph.iter_edges():
        source_distance = result.distances[edge.source]
        target_distance = result.distances[edge.target]
        if source_distance == float("inf"):
            continue
        assert source_distance + edge.weight >= target_distance

    for node, distance in result.distances.items():
        predecessor = result.predecessors[node]
        if node == result.source or distance == float("inf"):
            assert predecessor is None
            continue
        assert predecessor is not None
        assert result.distances[predecessor] + edges_by_pair[(predecessor, node)] == distance


def selected_sources(graph: Graph) -> tuple[Node, ...]:
    nodes = tuple(sorted(graph.nodes))
    return tuple(dict.fromkeys((nodes[0], nodes[len(nodes) // 2], nodes[-1])))


NON_NEGATIVE_CASES = [
    ("random", make_random_graph(nodes=14, edges=42, directed=True, seed=101)),
    (
        "erdos_renyi",
        make_erdos_renyi_graph(nodes=12, probability=0.25, directed=True, seed=102),
    ),
    ("grid", make_grid_graph(4, 4, directed=False, weight=2)),
    ("road_like", make_road_like_graph(width=4, height=4, seed=103)),
    ("heavy_tailed", make_heavy_tailed_graph(nodes=14, edges=36, directed=True, seed=104)),
    ("layered_dag", make_layered_dag(layers=4, width=4, seed=105)),
    ("equal_weight", make_equal_weight_graph(nodes=14, edges=36, directed=True, seed=106)),
    ("wide_integer", make_wide_integer_weight_graph(nodes=12, edges=32, directed=True, seed=107)),
]

NON_NEGATIVE_RUNNERS: tuple[tuple[str, SsspRunner], ...] = (
    ("dial", dial_sssp),
    ("dial_circular", dial_circular_sssp),
    ("radix_heap", dijkstra_radix_heap),
    ("delta", lambda graph, source: delta_stepping(graph, source, delta=3.0)),
    ("policy_delta", policy_delta_stepping),
)


@pytest.mark.parametrize(
    ("name", "graph"),
    NON_NEGATIVE_CASES,
    ids=[case[0] for case in NON_NEGATIVE_CASES],
)
def test_non_negative_algorithms_satisfy_randomized_invariants(name: str, graph: Graph) -> None:
    del name
    for source in selected_sources(graph):
        reference = dijkstra(graph, source)
        assert_shortest_path_invariants(graph, reference)

        for _runner_name, runner in NON_NEGATIVE_RUNNERS:
            result = runner(graph, source)
            assert_same_distances(result.distances, reference.distances)
            assert_shortest_path_invariants(graph, result)


@pytest.mark.parametrize("seed", [201, 202, 203, 204, 205])
def test_negative_dag_algorithms_satisfy_randomized_invariants(seed: int) -> None:
    graph = make_negative_dag(nodes=12, edges=30, seed=seed)

    for source in selected_sources(graph):
        reference = bellman_ford(graph, source)
        result = johnson_sssp(graph, source)

        assert_same_distances(result.distances, reference.distances)
        assert_shortest_path_invariants(graph, reference)
        assert_shortest_path_invariants(graph, result)
