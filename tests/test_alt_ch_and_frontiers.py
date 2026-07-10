from __future__ import annotations

from sssp_lab.algorithms.alt import alt_query, build_alt_index
from sssp_lab.algorithms.bmssp import bounded_multi_source_sssp
from sssp_lab.algorithms.contraction_hierarchies import build_ch_index, ch_query
from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.frontier_sssp import frontier_partition_sssp
from sssp_lab.algorithms.negative_weight import johnson_sssp
from sssp_lab.algorithms.thorup_like import build_distance_scale_buckets, thorup_integer_baseline
from sssp_lab.graph import Graph
from sssp_lab.utils import assert_same_distances, make_random_graph


def test_alt_query_matches_dijkstra() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (1, 2, 2), (0, 3, 3), (3, 2, 2), (2, 4, 1)],
        directed=True,
    )
    index = build_alt_index(graph, landmarks=[0, 4])
    distance, path = alt_query(graph, 0, 4, index)
    assert distance == dijkstra(graph, 0).distances[4]
    assert path[0] == 0
    assert path[-1] == 4


def test_ch_query_matches_dijkstra_on_undirected_graph() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10), (1, 3, 5)],
        directed=False,
    )
    index = build_ch_index(graph, order=[0, 1, 2, 3])
    assert ch_query(index, 0, 3) == dijkstra(graph, 0).distances[3]


def test_bounded_multi_source_sssp_exposes_frontier() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (1, 2, 2), (2, 3, 2)],
        directed=True,
    )
    result = bounded_multi_source_sssp(graph, {0}, bound=3)
    assert 0 in result.settled
    assert 1 in result.settled
    assert 2 in result.frontier


def test_bounded_multi_source_debug_invariants() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 1), (0, 2, 5)], directed=True)

    result = bounded_multi_source_sssp(graph, {0}, bound=2, debug=True)

    assert result.settled == frozenset({0, 1})
    assert 2 in result.frontier


def test_bounded_multi_source_matches_dijkstra_on_random_graphs() -> None:
    for seed in range(100):
        graph = make_random_graph(
            nodes=12,
            edges=35,
            directed=True,
            min_weight=1,
            max_weight=9,
            seed=seed,
        )
        result = bounded_multi_source_sssp(graph, {0}, bound=float("inf"), debug=True)
        assert_same_distances(result.distances, dijkstra(graph, 0).distances)


def test_bounded_multi_source_layered_and_close_labels() -> None:
    graph = Graph.from_edges(
        [
            (0, 1, 1.0),
            (0, 2, 1.01),
            (1, 3, 1.0),
            (2, 3, 0.98),
            (3, 4, 1.0),
            (2, 5, 3.0),
        ],
        directed=True,
    )

    result = bounded_multi_source_sssp(graph, {0}, bound=float("inf"), debug=True)

    assert_same_distances(result.distances, dijkstra(graph, 0).distances)


def test_frontier_partition_matches_dijkstra() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (1, 2, 2), (0, 3, 10), (2, 3, 1)],
        directed=True,
    )
    result, stats = frontier_partition_sssp(graph, 0, initial_bound=2, growth=2, debug=True)
    assert stats.rounds >= 1
    assert_same_distances(result.distances, dijkstra(graph, 0).distances)


def test_frontier_partition_matches_comparison_algorithms() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 4), (0, 3, 2), (3, 2, 1), (2, 4, 3)],
        directed=True,
    )

    result, _ = frontier_partition_sssp(graph, 0, initial_bound=1.5, growth=2.0, debug=True)

    assert_same_distances(result.distances, dijkstra(graph, 0).distances)
    assert_same_distances(result.distances, delta_stepping(graph, 0, delta=2).distances)


def test_frontier_partition_uses_absolute_source_offsets() -> None:
    graph = Graph.from_edges(
        [
            (0, 1, 2),
            (1, 2, 2),
            (0, 2, 10),
            (2, 3, 1),
        ],
        directed=True,
    )

    result, _ = frontier_partition_sssp(graph, 0, initial_bound=3, growth=2, debug=True)

    assert result.distances[3] == 5


def test_thorup_like_baseline_and_buckets() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 2), (2, 3, 3)],
        directed=False,
    )
    result = thorup_integer_baseline(graph, 0)
    buckets = build_distance_scale_buckets(result, scale=2)
    assert result.distances[3] == 6
    assert buckets


def test_thorup_like_rejects_out_of_scope_graphs() -> None:
    directed = Graph.from_edges([(0, 1, 1)], directed=True)
    non_integer = Graph.from_edges([(0, 1, 1.5)], directed=False)
    zero_weight = Graph.from_edges([(0, 1, 0)], directed=False)

    for graph in [directed, non_integer, zero_weight]:
        try:
            thorup_integer_baseline(graph, 0)
        except ValueError:
            pass
        else:
            raise AssertionError("out-of-scope graph was accepted")


def test_thorup_like_matches_references_on_undirected_families() -> None:
    cases = [
        Graph.from_edges([(0, 1, 2), (1, 2, 3), (2, 3, 4)], directed=False),
        Graph.from_edges([(0, 1, 1), (1, 2, 1), (2, 0, 1)], directed=False),
        Graph.from_edges([(0, 1, 7), (2, 3, 5)], directed=False),
        make_random_graph(
            nodes=15,
            edges=25,
            directed=False,
            min_weight=1,
            max_weight=20,
            seed=55,
        ),
    ]

    for graph in cases:
        result = thorup_integer_baseline(graph, 0)
        assert_same_distances(result.distances, dijkstra(graph, 0).distances)


def test_johnson_sssp_matches_bellman_ford_case() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, -2), (0, 2, 5), (2, 3, 1)],
        directed=True,
    )
    result = johnson_sssp(graph, 0)
    assert result.distances[3] == 0
