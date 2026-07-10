from __future__ import annotations

from sssp_lab.algorithms.alt import (
    ALTQueryStats,
    alt_query,
    avoid_landmarks,
    build_alt_index,
    coordinate_corner_landmarks,
    farthest_first_landmarks,
    grid_corner_landmarks,
    high_degree_landmarks,
    random_landmarks,
)
from sssp_lab.algorithms.bellman_ford import NegativeCycleError
from sssp_lab.algorithms.bmssp import bounded_multi_source_sssp, recursive_bmssp
from sssp_lab.algorithms.contraction_hierarchies import (
    build_ch_index,
    ch_query,
    ch_query_path,
    contraction_candidate,
    contraction_order,
    witness_contraction_order,
)
from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.frontier_sssp import frontier_partition_sssp
from sssp_lab.algorithms.negative_weight import (
    check_against_bellman_ford,
    decompose_by_edge_sign,
    johnson_sssp,
    negative_weight_reference_sssp,
    scale_layers,
    seeded_vertex_sample,
)
from sssp_lab.algorithms.stats import OperationStats
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


def _grid_graph(width: int, height: int, *, directed: bool) -> Graph:
    edges: list[tuple[int, int, float]] = []
    for row in range(height):
        for col in range(width):
            node = row * width + col
            if col + 1 < width:
                edges.append((node, node + 1, 1.0))
            if row + 1 < height:
                edges.append((node, node + width, 1.0))
    return Graph.from_edges(edges, directed=directed)


def test_alt_landmark_strategies() -> None:
    graph = _grid_graph(4, 4, directed=False)
    coordinates = {node: (float(node % 4), float(node // 4)) for node in graph.nodes}

    assert len(random_landmarks(graph, count=3, seed=1)) == 3
    assert high_degree_landmarks(graph, count=2)
    assert len(farthest_first_landmarks(graph, count=3)) == 3
    assert len(avoid_landmarks(graph, count=3, seed=0, sample_limit=10)) == 3
    assert coordinate_corner_landmarks(graph, coordinates) == (0, 3, 12, 15)
    assert grid_corner_landmarks(width=4, height=4) == (0, 3, 12, 15)


def test_alt_landmark_strategy_validation() -> None:
    graph = _grid_graph(2, 2, directed=False)

    for selector in [
        random_landmarks,
        high_degree_landmarks,
        farthest_first_landmarks,
        avoid_landmarks,
    ]:
        try:
            selector(graph, count=5)
        except ValueError:
            pass
        else:
            raise AssertionError("selector accepted too many landmarks")

    try:
        avoid_landmarks(graph, count=2, sample_limit=0)
    except ValueError:
        pass
    else:
        raise AssertionError("avoid selector accepted an empty sample")

    try:
        coordinate_corner_landmarks(graph, {0: (0.0, 0.0)}, count=2)
    except ValueError:
        pass
    else:
        raise AssertionError("coordinate selector accepted incomplete coordinates")


def test_alt_query_stats_on_directed_and_undirected_graphs() -> None:
    for directed in [True, False]:
        graph = _grid_graph(4, 4, directed=directed)
        index = build_alt_index(graph, grid_corner_landmarks(width=4, height=4))
        stats = ALTQueryStats()

        distance, path = alt_query(graph, 0, 15, index, stats=stats)

        assert distance == dijkstra(graph, 0).distances[15]
        assert path[0] == 0
        assert path[-1] == 15
        assert stats.heap_pops > 0
        assert stats.heuristic_evaluations > 0


def test_alt_settles_fewer_nodes_than_full_dijkstra_on_grid() -> None:
    graph = _grid_graph(5, 5, directed=False)
    index = build_alt_index(graph, grid_corner_landmarks(width=5, height=5))
    alt_stats = ALTQueryStats()

    distance, _ = alt_query(graph, 0, 24, index, stats=alt_stats)

    assert distance == dijkstra(graph, 0).distances[24]
    assert alt_stats.settled_nodes < len(graph.nodes)


def test_ch_query_matches_dijkstra_on_undirected_graph() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10), (1, 3, 5)],
        directed=False,
    )
    index = build_ch_index(graph, order=[0, 1, 2, 3])
    assert ch_query(index, 0, 3) == dijkstra(graph, 0).distances[3]


def test_ch_query_path_unpacks_shortcuts() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10)],
        directed=False,
    )
    index = build_ch_index(graph, order=[1, 2, 0, 3])

    distance, path = ch_query_path(index, 0, 3)

    assert distance == dijkstra(graph, 0).distances[3]
    assert path[0] == 0
    assert path[-1] == 3
    assert len(path) >= 2


def test_ch_order_heuristics_cover_small_graph() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 1), (0, 2, 3)], directed=False)

    for heuristic in ["degree", "edge_difference", "contracted_neighbor_count", "shortcut_cover", "level"]:
        order = contraction_order(graph, heuristic=heuristic)
        assert set(order) == graph.nodes


def test_ch_witness_order_heuristics_cover_small_graph() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10), (1, 3, 5)],
        directed=False,
    )

    for heuristic in [
        "edge_difference",
        "contracted_neighbor_count",
        "shortcut_cover",
        "level",
    ]:
        order = witness_contraction_order(graph, heuristic=heuristic)
        assert set(order) == graph.nodes


def test_ch_witness_order_builds_correct_index() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10), (1, 3, 5)],
        directed=False,
    )

    index = build_ch_index(graph, heuristic="witness_edge_difference")

    assert ch_query(index, 0, 3) == dijkstra(graph, 0).distances[3]
    assert set(index.rank) == graph.nodes


def test_ch_contraction_candidate_reports_shortcut_metrics() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 1)], directed=True)

    candidate = contraction_candidate(graph, 1)

    assert candidate.node == 1
    assert candidate.shortcut_count == 1
    assert candidate.edge_difference == -1


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


def test_recursive_bmssp_matches_bounded_primitive() -> None:
    graph = Graph.from_edges(
        [
            (0, 1, 1),
            (1, 2, 1),
            (2, 3, 1),
            (0, 4, 2),
            (4, 3, 2),
            (3, 5, 1),
        ],
        directed=True,
    )

    recursive = recursive_bmssp(graph, {0}, bound=4, depth=3, debug=True)
    bounded = bounded_multi_source_sssp(graph, {0}, bound=4, debug=True)

    assert_same_distances(recursive.distances, bounded.distances)
    assert recursive.settled == bounded.settled
    assert recursive.frontier == bounded.frontier
    assert len(recursive.levels) > 1


def test_recursive_bmssp_respects_absolute_source_offsets() -> None:
    graph = Graph.from_edges([(0, 1, 2), (1, 2, 2), (0, 2, 10)], directed=True)

    result = recursive_bmssp(
        graph,
        {1},
        bound=5,
        depth=2,
        source_distances={1: 1},
        debug=True,
    )

    assert result.distances[1] == 1
    assert result.distances[2] == 3
    assert 2 in result.settled


def test_recursive_bmssp_validates_options() -> None:
    graph = Graph.from_edges([(0, 1, 1)], directed=True)

    for kwargs in [{"depth": -1}, {"split_factor": 1}]:
        try:
            recursive_bmssp(graph, {0}, bound=2, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid recursive BMSSP option was accepted")

    try:
        recursive_bmssp(graph, {0}, bound=0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid recursive BMSSP bound was accepted")


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


def test_negative_weight_algorithms_populate_stats() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, -2), (0, 2, 5), (2, 3, 1)],
        directed=True,
    )
    johnson_stats = OperationStats()
    reference_stats = OperationStats()

    result = johnson_sssp(graph, 0, stats=johnson_stats)
    reference = negative_weight_reference_sssp(graph, 0, stats=reference_stats)

    assert_same_distances(result.distances, reference.distances)
    assert johnson_stats.relaxations > 0
    assert johnson_stats.queue_pushes > 0
    assert johnson_stats.queue_pops > 0
    assert johnson_stats.settled_nodes >= len(graph.nodes)
    assert reference_stats.relaxations > 0
    assert reference_stats.settled_nodes == len(graph.nodes)


def test_negative_weight_helpers_are_deterministic() -> None:
    graph = Graph.from_edges(
        [(0, 1, -2), (1, 2, 3), (0, 2, 5), (2, 3, -1)],
        directed=True,
    )

    decomposition = decompose_by_edge_sign(graph)
    layers = scale_layers(graph, scale=2)

    assert len(decomposition.negative_edges) == 2
    assert layers
    assert seeded_vertex_sample(graph, probability=0.5, seed=9) == seeded_vertex_sample(
        graph,
        probability=0.5,
        seed=9,
    )


def test_johnson_sssp_randomized_cases_match_bellman_ford() -> None:
    cases = [
        Graph.from_edges([(0, 1, 2), (1, 2, -1), (0, 2, 5)], directed=True),
        Graph.from_edges([(0, 1, -1), (0, 2, 4), (1, 2, 2), (2, 3, 1)], directed=True),
    ]

    for graph in cases:
        result = johnson_sssp(graph, 0)
        check_against_bellman_ford(graph, 0, result)


def test_johnson_sssp_detects_negative_cycle() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, -3), (2, 1, 1)], directed=True)

    try:
        johnson_sssp(graph, 0)
    except NegativeCycleError:
        pass
    else:
        raise AssertionError("negative cycle was not detected")
