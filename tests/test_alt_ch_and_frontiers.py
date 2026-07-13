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
from sssp_lab.algorithms.bellman_ford import NegativeCycleError, bellman_ford
from sssp_lab.algorithms.bmssp import (
    BMSSPConfig,
    BMSSPQueue,
    bmssp_base_case,
    bounded_multi_source_sssp,
    find_pivots,
    paper_bmssp,
    recursive_bmssp,
)
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
from sssp_lab.algorithms.frontier_sssp import (
    bounded_exploration_round,
    build_incomplete_vertex_index,
    frontier_partition_sssp,
)
from sssp_lab.algorithms.negative_weight import (
    check_against_bellman_ford,
    decompose_by_edge_sign,
    johnson_sssp,
    negative_decomposition_experiment,
    negative_weight_reference_sssp,
    scale_layers,
    seeded_vertex_sample,
)
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.algorithms.thorup_like import (
    build_component_hierarchy,
    build_distance_scale_buckets,
    thorup_integer_baseline,
)
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


def test_alt_query_rejects_index_from_different_graph() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1.0), (1, 2, 1.0), (0, 2, 100.0)],
        directed=True,
    )
    stale_index_graph = Graph.from_edges([(0, 1, 0.0), (0, 2, 100.0)], directed=True)
    index = build_alt_index(stale_index_graph, landmarks=[0])

    try:
        alt_query(graph, 0, 2, index)
    except ValueError as exc:
        assert str(exc) == "ALT index was built for a different graph"
    else:
        raise AssertionError("stale ALT index was accepted")


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


def test_ch_query_populates_stats() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10), (1, 3, 5)],
        directed=False,
    )
    index = build_ch_index(graph, order=[0, 1, 2, 3])
    stats = OperationStats()

    distance = ch_query(index, 0, 3, stats=stats)

    assert distance == dijkstra(graph, 0).distances[3]
    assert stats.relaxations > 0
    assert stats.queue_pushes > 0
    assert stats.queue_pops > 0
    assert stats.settled_nodes > 0


def test_ch_query_path_unpacks_shortcuts() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10)],
        directed=False,
    )
    index = build_ch_index(graph, order=[1, 2, 0, 3])
    stats = OperationStats()

    distance, path = ch_query_path(index, 0, 3, stats=stats)

    assert distance == dijkstra(graph, 0).distances[3]
    assert path[0] == 0
    assert path[-1] == 3
    assert len(path) >= 2
    assert stats.relaxations > 0


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


def test_bmssp_queue_insert_pull_and_duplicate_keys() -> None:
    queue = BMSSPQueue()

    assert not queue
    assert queue.pull(2) == (frozenset(), float("inf"))

    queue.insert(3, 5.0)
    queue.insert(1, 2.0)
    queue.insert(2, 4.0)
    queue.insert(3, 1.0)
    queue.insert(2, 9.0)

    assert len(queue) == 3
    pulled, next_bound = queue.pull(2)
    assert pulled == frozenset({1, 3})
    assert next_bound == 4.0

    pulled, next_bound = queue.pull(5)
    assert pulled == frozenset({2})
    assert next_bound == float("inf")
    assert not queue


def test_bmssp_queue_batch_prepend_keeps_smallest_labels() -> None:
    queue = BMSSPQueue()
    queue.insert(10, 10.0)
    queue.insert(11, 12.0)

    queue.batch_prepend({1: 3.0, 2: 4.0, 10: 2.0})

    pulled, next_bound = queue.pull(3)
    assert pulled == frozenset({1, 2, 10})
    assert next_bound == 12.0


def test_bmssp_queue_validates_operations() -> None:
    queue = BMSSPQueue()

    try:
        queue.pull(0)
    except ValueError as exc:
        assert str(exc) == "limit must be positive"
    else:
        raise AssertionError("non-positive pull limit was accepted")

    try:
        queue.insert(1, float("inf"))
    except ValueError as exc:
        assert str(exc) == "label must be finite"
    else:
        raise AssertionError("infinite queue label was accepted")

    queue.insert(1, 1.0)
    try:
        queue.batch_prepend({2: 2.0})
    except ValueError as exc:
        assert str(exc) == "batch-prepended labels must not exceed the current queue minimum"
    else:
        raise AssertionError("out-of-order batch prepend was accepted")


def test_find_pivots_selects_large_predecessor_subtrees() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 1)], directed=True)
    graph.add_node(3)
    labels = {node: float("inf") for node in graph.nodes}
    predecessors = {node: None for node in graph.nodes}
    labels[0] = 0.0
    labels[3] = 0.0
    stats = OperationStats()

    result = find_pivots(
        graph,
        {0, 3},
        bound=10,
        k=2,
        labels=labels,
        predecessors=predecessors,
        stats=stats,
    )

    assert result.pivots == frozenset({0})
    assert result.reached == frozenset({0, 1, 2, 3})
    assert not result.partial
    assert labels[2] == 2.0
    assert predecessors[2] == 1
    assert stats.relaxations == 2


def test_find_pivots_returns_partial_when_reached_set_grows_too_large() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (0, 2, 1), (0, 3, 1)],
        directed=True,
    )
    labels = {node: float("inf") for node in graph.nodes}
    predecessors = {node: None for node in graph.nodes}
    labels[0] = 0.0

    result = find_pivots(
        graph,
        {0},
        bound=10,
        k=2,
        labels=labels,
        predecessors=predecessors,
    )

    assert result.partial
    assert result.pivots == frozenset({0})
    assert result.reached == frozenset({0, 1, 2, 3})


def test_find_pivots_respects_bound_and_validates_inputs() -> None:
    graph = Graph.from_edges([(0, 1, 5)], directed=True)
    labels = {0: 0.0, 1: float("inf")}
    predecessors = {0: None, 1: None}

    result = find_pivots(
        graph,
        {0},
        bound=5,
        k=1,
        labels=labels,
        predecessors=predecessors,
    )
    assert result.reached == frozenset({0})
    assert labels[1] == float("inf")

    for runner in [
        lambda: find_pivots(graph, set(), bound=5, k=1, labels=labels, predecessors=predecessors),
        lambda: find_pivots(graph, {0}, bound=0, k=1, labels=labels, predecessors=predecessors),
        lambda: find_pivots(graph, {0}, bound=5, k=0, labels=labels, predecessors=predecessors),
        lambda: find_pivots(graph, {0}, bound=5, k=1, labels={0: 0.0}, predecessors=predecessors),
        lambda: find_pivots(graph, {1}, bound=5, k=1, labels=labels, predecessors=predecessors),
    ]:
        try:
            runner()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid find_pivots input was accepted")


def test_bmssp_base_case_completes_when_settled_count_stays_within_k() -> None:
    graph = Graph.from_edges([(0, 1, 2), (1, 2, 2)], directed=True)
    labels = {node: float("inf") for node in graph.nodes}
    predecessors = {node: None for node in graph.nodes}
    complete: set[int] = set()
    labels[0] = 0.0
    stats = OperationStats()

    boundary, settled = bmssp_base_case(
        graph,
        0,
        bound=5,
        k=3,
        labels=labels,
        predecessors=predecessors,
        complete=complete,
        stats=stats,
    )

    assert boundary == 5
    assert settled == frozenset({0, 1, 2})
    assert complete == {0, 1, 2}
    assert labels[2] == 4.0
    assert predecessors[2] == 1
    assert stats.settled_nodes == 3


def test_bmssp_base_case_returns_partial_boundary_after_k_plus_one_vertices() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 1), (2, 3, 1)], directed=True)
    labels = {node: float("inf") for node in graph.nodes}
    predecessors = {node: None for node in graph.nodes}
    labels[0] = 0.0

    boundary, settled = bmssp_base_case(
        graph,
        0,
        bound=10,
        k=2,
        labels=labels,
        predecessors=predecessors,
    )

    assert boundary == 2.0
    assert settled == frozenset({0, 1, 2})
    assert labels[3] == 3.0
    assert predecessors[3] == 2


def test_bmssp_base_case_respects_bound_and_validates_inputs() -> None:
    graph = Graph.from_edges([(0, 1, 5)], directed=True)
    labels = {0: 0.0, 1: float("inf")}
    predecessors = {0: None, 1: None}

    boundary, settled = bmssp_base_case(
        graph,
        0,
        bound=5,
        k=2,
        labels=labels,
        predecessors=predecessors,
    )
    assert boundary == 5
    assert settled == frozenset({0})
    assert labels[1] == 5.0
    assert predecessors[1] == 0

    for runner in [
        lambda: bmssp_base_case(
            graph,
            0,
            bound=0,
            k=1,
            labels={0: 0.0, 1: float("inf")},
            predecessors={0: None, 1: None},
        ),
        lambda: bmssp_base_case(
            graph,
            0,
            bound=5,
            k=0,
            labels={0: 0.0, 1: float("inf")},
            predecessors={0: None, 1: None},
        ),
        lambda: bmssp_base_case(
            graph,
            0,
            bound=5,
            k=1,
            labels={0: 0.0},
            predecessors={0: None, 1: None},
        ),
        lambda: bmssp_base_case(
            graph,
            0,
            bound=5,
            k=1,
            labels={0: 0.0, 1: float("inf")},
            predecessors={0: None},
        ),
        lambda: bmssp_base_case(
            graph,
            1,
            bound=5,
            k=1,
            labels={0: 0.0, 1: float("inf")},
            predecessors={0: None, 1: None},
        ),
    ]:
        try:
            runner()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid bmssp_base_case input was accepted")


def test_paper_bmssp_matches_bounded_multi_source_on_small_graph() -> None:
    graph = Graph.from_edges(
        [
            (0, 1, 1),
            (1, 2, 1),
            (3, 4, 2),
            (4, 2, 1),
        ],
        directed=True,
    )
    labels = {node: float("inf") for node in graph.nodes}
    predecessors = {node: None for node in graph.nodes}
    labels[0] = 0.0
    labels[3] = 0.0
    complete: set[int] = set()
    stats = OperationStats()

    result = paper_bmssp(
        graph,
        {0, 3},
        bound=10,
        level=2,
        labels=labels,
        predecessors=predecessors,
        config=BMSSPConfig(k=3, child_limit=2, work_limit=20),
        complete=complete,
        debug=True,
        stats=stats,
    )
    expected = bounded_multi_source_sssp(graph, {0, 3}, bound=10)

    assert_same_distances(labels, expected.distances)
    assert result.boundary == 10
    assert not result.partial
    assert result.complete_vertices == frozenset(graph.nodes)
    assert complete == set(graph.nodes)
    assert result.levels
    assert stats.relaxations > 0


def test_paper_bmssp_reports_partial_when_work_limit_is_reached() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 1), (3, 4, 1), (4, 5, 1)],
        directed=True,
    )
    labels = {node: float("inf") for node in graph.nodes}
    predecessors = {node: None for node in graph.nodes}
    labels[0] = 0.0
    labels[3] = 0.0

    result = paper_bmssp(
        graph,
        {0, 3},
        bound=10,
        level=1,
        labels=labels,
        predecessors=predecessors,
        config=BMSSPConfig(k=2, child_limit=1, work_limit=1),
    )

    assert result.partial
    assert result.boundary <= 10
    assert result.complete_vertices


def test_paper_bmssp_validates_inputs() -> None:
    graph = Graph.from_edges([(0, 1, 1)], directed=True)
    labels = {0: 0.0, 1: float("inf")}
    predecessors = {0: None, 1: None}

    for runner in [
        lambda: BMSSPConfig(k=0),
        lambda: BMSSPConfig(child_limit=0),
        lambda: BMSSPConfig(work_limit=0),
        lambda: paper_bmssp(
            graph,
            set(),
            bound=5,
            level=1,
            labels=labels,
            predecessors=predecessors,
        ),
        lambda: paper_bmssp(
            graph,
            {0},
            bound=0,
            level=1,
            labels=labels,
            predecessors=predecessors,
        ),
        lambda: paper_bmssp(
            graph,
            {0},
            bound=5,
            level=-1,
            labels=labels,
            predecessors=predecessors,
        ),
        lambda: paper_bmssp(
            graph,
            {0},
            bound=5,
            level=1,
            labels={0: 0.0},
            predecessors=predecessors,
        ),
        lambda: paper_bmssp(
            graph,
            {1},
            bound=5,
            level=1,
            labels=labels,
            predecessors=predecessors,
        ),
    ]:
        try:
            runner()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid paper_bmssp input was accepted")


def test_paper_bmssp_matches_bounded_multi_source_on_random_graphs() -> None:
    for seed in range(100):
        graph = make_random_graph(
            nodes=12,
            edges=35,
            directed=True,
            min_weight=1,
            max_weight=9,
            seed=seed,
        )
        labels = {node: float("inf") for node in graph.nodes}
        predecessors = {node: None for node in graph.nodes}
        labels[0] = 0.0

        result = paper_bmssp(
            graph,
            {0},
            bound=float("inf"),
            level=3,
            labels=labels,
            predecessors=predecessors,
            config=BMSSPConfig(k=4, child_limit=3, work_limit=64),
            debug=True,
        )
        expected = bounded_multi_source_sssp(graph, {0}, bound=float("inf"))

        assert_same_distances(labels, expected.distances)
        assert not result.partial
        assert result.boundary == float("inf")


def test_paper_bmssp_matches_bounded_multi_source_on_layered_tie_graphs() -> None:
    cases = [
        Graph.from_edges(
            [
                (0, 1, 1.0),
                (0, 2, 1.0),
                (0, 3, 1.01),
                (1, 4, 1.0),
                (2, 4, 1.0),
                (1, 5, 1.02),
                (2, 5, 1.01),
                (3, 5, 0.99),
                (4, 6, 1.0),
                (5, 6, 1.0),
                (6, 7, 0.5),
            ],
            directed=True,
        ),
        Graph.from_edges(
            [
                (0, 1, 1.0),
                (0, 2, 1.0),
                (0, 3, 1.0),
                (1, 4, 1.0),
                (1, 5, 1.0),
                (1, 6, 1.0),
                (2, 4, 1.0),
                (2, 5, 1.0),
                (2, 6, 1.0),
                (3, 4, 1.0),
                (3, 5, 1.0),
                (3, 6, 1.0),
                (4, 7, 1.0),
                (5, 7, 1.0),
                (6, 7, 1.0),
                (4, 8, 1.0),
                (5, 8, 1.0),
                (6, 8, 1.0),
            ],
            directed=True,
        ),
    ]

    for graph in cases:
        labels = {node: float("inf") for node in graph.nodes}
        predecessors = {node: None for node in graph.nodes}
        labels[0] = 0.0

        result = paper_bmssp(
            graph,
            {0},
            bound=float("inf"),
            level=3,
            labels=labels,
            predecessors=predecessors,
            config=BMSSPConfig(k=2, child_limit=2, work_limit=32),
            debug=True,
        )
        expected = bounded_multi_source_sssp(graph, {0}, bound=float("inf"))

        assert_same_distances(labels, expected.distances)
        assert not result.partial
        assert result.boundary == float("inf")


def test_paper_bmssp_preserves_inf_for_disconnected_vertices() -> None:
    graph = Graph.from_edges(
        [
            (0, 1, 2.0),
            (1, 2, 3.0),
            (3, 4, 1.0),
            (4, 5, 1.0),
        ],
        directed=True,
    )
    graph.add_node(6)
    labels = {node: float("inf") for node in graph.nodes}
    predecessors = {node: None for node in graph.nodes}
    labels[0] = 0.0

    result = paper_bmssp(
        graph,
        {0},
        bound=float("inf"),
        level=3,
        labels=labels,
        predecessors=predecessors,
        config=BMSSPConfig(k=2, child_limit=2, work_limit=16),
        debug=True,
    )
    expected = bounded_multi_source_sssp(graph, {0}, bound=float("inf"))

    assert_same_distances(labels, expected.distances)
    assert result.complete_vertices == frozenset({0, 1, 2})
    assert labels[3] == float("inf")
    assert labels[4] == float("inf")
    assert labels[5] == float("inf")
    assert labels[6] == float("inf")
    assert predecessors[3] is None
    assert predecessors[6] is None
    assert not result.partial


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


def test_bounded_source_label_maps_report_missing_sources() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 1)], directed=True)

    for runner in [
        lambda: bounded_multi_source_sssp(graph, {0, 1}, bound=3, source_distances={0: 0.0}),
        lambda: recursive_bmssp(graph, {0, 1}, bound=3, source_distances={0: 0.0}),
        lambda: bounded_exploration_round(graph, {1}, bound=3, global_distances={0: 0.0}),
    ]:
        try:
            runner()
        except ValueError as exc:
            assert "must include every source" in str(exc)
            assert "1" in str(exc)
        else:
            raise AssertionError("missing source label was accepted")


def test_incomplete_vertex_index_tracks_boundary_labels() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 1)],
        directed=True,
    )
    distances = {0: 0.0, 1: 2.0, 2: float("inf"), 3: float("inf")}

    index = build_incomplete_vertex_index(graph, distances)

    assert index.complete == frozenset({0, 1})
    assert index.incomplete == frozenset({2, 3})
    assert {(edge.source, edge.target) for edge in index.boundary_edges} == {(0, 2), (1, 2)}
    assert index.boundary_labels == {2: 3.0}
    assert index.frontier_sources() == frozenset({2})


def test_incomplete_vertex_index_can_use_settled_set() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 1)], directed=True)
    distances = {0: 0.0, 1: 1.0, 2: 2.0}

    index = build_incomplete_vertex_index(graph, distances, settled={0})

    assert index.complete == frozenset({0})
    assert index.incomplete == frozenset({1, 2})
    assert index.boundary_labels == {1: 1.0}


def test_frontier_partition_matches_dijkstra() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (1, 2, 2), (0, 3, 10), (2, 3, 1)],
        directed=True,
    )
    result, frontier_stats = frontier_partition_sssp(graph, 0, initial_bound=2, growth=2, debug=True)
    assert frontier_stats.rounds >= 1
    assert len(frontier_stats.incomplete_counts) == frontier_stats.rounds
    assert len(frontier_stats.boundary_edge_counts) == frontier_stats.rounds
    assert_same_distances(result.distances, dijkstra(graph, 0).distances)


def test_frontier_partition_populates_operation_stats() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (1, 2, 2), (0, 3, 10), (2, 3, 1)],
        directed=True,
    )
    stats = OperationStats()

    result, frontier_stats = frontier_partition_sssp(
        graph,
        0,
        initial_bound=2,
        growth=2,
        debug=True,
        stats=stats,
    )

    assert_same_distances(result.distances, dijkstra(graph, 0).distances)
    assert frontier_stats.rounds >= 1
    assert stats.relaxations > 0
    assert stats.queue_pushes > 0
    assert stats.queue_pops > 0
    assert stats.settled_nodes > 0


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
    stats = OperationStats()
    result = thorup_integer_baseline(graph, 0, stats=stats)
    buckets = build_distance_scale_buckets(result, scale=2)
    assert result.distances[3] == 6
    assert buckets
    assert stats.relaxations > 0
    assert stats.queue_pushes > 0
    assert stats.queue_pops > 0
    assert stats.settled_nodes == 4


def test_thorup_component_hierarchy_tracks_scale_components() -> None:
    graph = Graph.from_edges(
        [(0, 1, 1), (1, 2, 4), (2, 3, 8), (4, 5, 2)],
        directed=False,
    )

    hierarchy = build_component_hierarchy(graph, scales=(1, 4, 8))

    assert [len(level) for level in hierarchy.levels] == [5, 3, 2]
    assert hierarchy.component_path(0)[0] == hierarchy.component_path(1)[0]
    assert hierarchy.component_path(0)[1] == hierarchy.component_path(2)[1]
    assert hierarchy.component_path(0)[2] == hierarchy.component_path(3)[2]
    assert hierarchy.component_path(4)[2] == hierarchy.component_path(5)[2]
    assert hierarchy.component_path(0)[2] != hierarchy.component_path(4)[2]
    assert all(component.parent is not None for component in hierarchy.levels[0])
    assert all(component.parent is None for component in hierarchy.levels[-1])


def test_thorup_component_hierarchy_uses_default_powers_of_two() -> None:
    graph = Graph.from_edges([(0, 1, 3), (1, 2, 9)], directed=False)

    hierarchy = build_component_hierarchy(graph)

    assert [level[0].scale for level in hierarchy.levels] == [1, 2, 4, 8, 16]
    assert hierarchy.component_path(0)[-1] == hierarchy.component_path(2)[-1]


def test_thorup_component_hierarchy_validates_scales() -> None:
    graph = Graph.from_edges([(0, 1, 1)], directed=False)

    for scales in [(), (0,), (2, 1)]:
        try:
            build_component_hierarchy(graph, scales=scales)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid component hierarchy scale was accepted")


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


def test_negative_decomposition_experiment_matches_bellman_ford() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (1, 2, -1), (0, 2, 5), (2, 3, 2), (1, 3, 4)],
        directed=True,
    )

    experiment = negative_decomposition_experiment(
        graph,
        0,
        scale=2,
        sample_probability=0.5,
        seed=11,
    )

    assert_same_distances(experiment.result.distances, bellman_ford(graph, 0).distances)
    assert len(experiment.sign_decomposition.negative_edges) == 1
    assert experiment.rounds
    assert experiment.rounds[-1].reachable == frozenset({0, 1, 2, 3})
    assert negative_decomposition_experiment(
        graph,
        0,
        scale=2,
        sample_probability=0.5,
        seed=11,
    ).rounds == experiment.rounds


def test_negative_decomposition_experiment_validates_options() -> None:
    graph = Graph.from_edges([(0, 1, -1)], directed=True)

    try:
        negative_decomposition_experiment(graph, 0, scale=0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid decomposition scale was accepted")


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


def test_johnson_sssp_ignores_unreachable_negative_cycle() -> None:
    graph = Graph.from_edges(
        [
            (0, 1, 2.0),
            (2, 3, -1.0),
            (3, 2, -1.0),
        ],
        directed=True,
    )
    for node in range(4):
        graph.add_node(node)

    result = johnson_sssp(graph, 0)

    assert_same_distances(result.distances, bellman_ford(graph, 0).distances)
