from __future__ import annotations

import pytest

from sssp_lab.algorithms.bellman_ford import NegativeCycleError, bellman_ford
from sssp_lab.algorithms.delta_stepping import delta_stepping
from sssp_lab.algorithms.dial import dial_circular_sssp, dial_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.dijkstra_radix import dijkstra_radix_heap
from sssp_lab.algorithms.radix_heap import RadixHeap
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.algorithms.stepping_variants import (
    adaptive_bucket_delta,
    degree_adjusted_delta,
    mean_weight_delta,
    median_weight_delta,
    percentile_weight_delta,
    policy_delta_stepping,
    stepping_engine,
)
from sssp_lab.graph import Graph
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
        dial_circular_sssp(graph, 0),
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


@pytest.mark.parametrize(
    "graph",
    [
        Graph.from_edges([(0, 1, 0), (1, 2, 2), (0, 2, 5)], directed=True),
        Graph.from_edges([(0, 1, 3), (0, 1, 1), (1, 2, 4)], directed=True),
        Graph.from_edges([(0, 1, 2)], directed=True),
        Graph.from_edges([], directed=True),
    ],
)
def test_core_edge_cases_match_reference(graph: Graph) -> None:
    if not graph.nodes:
        graph.add_node(0)
    graph.add_node(99)

    reference = dijkstra(graph, 0)
    assert reference.distances[99] == float("inf")
    for result in [
        dial_sssp(graph, 0),
        dial_circular_sssp(graph, 0),
        dijkstra_radix_heap(graph, 0),
        delta_stepping(graph, 0, delta=1.0),
    ]:
        assert_same_distances(result.distances, reference.distances)


def test_core_algorithms_populate_stats() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 2), (0, 2, 5)], directed=True)
    stats = OperationStats()

    result = dijkstra(graph, 0, stats=stats)

    assert result.distances[2] == 3
    assert stats.relaxations > 0
    assert stats.queue_pushes > 0
    assert stats.queue_pops > 0
    assert stats.settled_nodes == 3


@pytest.mark.parametrize(
    "runner",
    [
        dijkstra,
        dial_sssp,
        dial_circular_sssp,
        dijkstra_radix_heap,
        lambda graph, source: delta_stepping(graph, source, delta=1.0),
    ],
)
def test_non_negative_algorithms_reject_negative_weights(runner: object) -> None:
    graph = Graph.from_edges([(0, 1, -1)], directed=True)

    with pytest.raises(ValueError):
        runner(graph, 0)  # type: ignore[operator]


@pytest.mark.parametrize("runner", [dial_sssp, dial_circular_sssp, dijkstra_radix_heap])
def test_integer_algorithms_reject_non_integer_weights(runner: object) -> None:
    graph = Graph.from_edges([(0, 1, 1.5)], directed=True)

    with pytest.raises(ValueError):
        runner(graph, 0)  # type: ignore[operator]


def test_radix_heap_monotone_keys_and_duplicates() -> None:
    heap: RadixHeap[str] = RadixHeap(max_bits=16)
    heap.push(0, "a")
    heap.push(3, "b")
    heap.push(3, "c")
    heap.push(10, "d")

    assert heap.pop() == (0, "a")
    assert heap.pop()[0] == 3
    assert heap.pop()[0] == 3
    assert heap.pop() == (10, "d")


def test_radix_heap_rejects_invalid_operations() -> None:
    heap: RadixHeap[int] = RadixHeap(max_bits=8)

    with pytest.raises(IndexError):
        heap.pop()

    heap.push(5, 1)
    assert heap.pop() == (5, 1)
    with pytest.raises(ValueError):
        heap.push(4, 2)


def test_radix_heap_handles_large_integer_keys() -> None:
    heap: RadixHeap[str] = RadixHeap(max_bits=64)
    large = 2**40

    heap.push(large, "large")

    assert heap.pop() == (large, "large")


def test_circular_dial_matches_reference_on_wide_integer_weights() -> None:
    graph = make_random_graph(
        nodes=25,
        edges=100,
        directed=True,
        min_weight=1,
        max_weight=1000,
        seed=44,
    )

    result = dial_circular_sssp(graph, 0)

    assert_same_distances(result.distances, dijkstra(graph, 0).distances)


@pytest.mark.parametrize("delta", [0.5, 1.0, 2.0, 5.0])
def test_delta_stepping_matches_dijkstra_over_delta_values(delta: float) -> None:
    graph = Graph.from_edges(
        [(0, 1, 0.5), (0, 2, 4.0), (1, 2, 1.5), (2, 3, 2.0), (1, 3, 6.0)],
        directed=True,
    )
    stats = OperationStats()

    result = delta_stepping(graph, 0, delta=delta, stats=stats)

    assert_same_distances(result.distances, dijkstra(graph, 0).distances)
    assert stats.bucket_phases > 0
    assert stats.light_relaxations + stats.heavy_relaxations == stats.relaxations


@pytest.mark.parametrize(
    "policy",
    [
        median_weight_delta,
        mean_weight_delta,
        percentile_weight_delta(75),
        degree_adjusted_delta,
        adaptive_bucket_delta,
    ],
)
def test_stepping_policies_match_dijkstra(policy: object) -> None:
    graph = make_random_graph(
        nodes=20,
        edges=80,
        directed=True,
        min_weight=1,
        max_weight=25,
        seed=33,
    )

    result = policy_delta_stepping(graph, 0, delta_policy=policy)  # type: ignore[arg-type]

    assert_same_distances(result.distances, dijkstra(graph, 0).distances)


def test_generic_stepping_engine_accepts_partition_policy() -> None:
    graph = Graph.from_edges([(0, 1, 1), (1, 2, 5), (0, 2, 10)], directed=True)

    result = stepping_engine(
        graph,
        0,
        delta=2.0,
        edge_partition_policy=lambda weight, delta: weight < delta,
    )

    assert_same_distances(result.distances, dijkstra(graph, 0).distances)


def test_graph_generators_support_property_style_checks() -> None:
    graph_cases = [
        make_erdos_renyi_graph(nodes=12, probability=0.2, directed=True, seed=1),
        make_erdos_renyi_graph(nodes=12, probability=0.2, directed=False, seed=2),
        make_grid_graph(4, 4, directed=False),
        make_layered_dag(layers=4, width=3, seed=3),
        make_road_like_graph(width=4, height=4, seed=4),
        make_heavy_tailed_graph(nodes=12, edges=30, directed=True, seed=5),
        make_equal_weight_graph(nodes=12, edges=30, directed=True, seed=6),
        make_wide_integer_weight_graph(nodes=12, edges=30, directed=True, seed=7),
    ]

    for index, graph in enumerate(graph_cases):
        reference = dijkstra(graph, 0)
        result = delta_stepping(graph, 0, delta=3.0)
        try:
            assert_same_distances(result.distances, reference.distances)
        except AssertionError as exc:
            raise AssertionError(f"graph generator case {index} failed") from exc


def test_negative_dag_generator_has_no_negative_cycle() -> None:
    graph = make_negative_dag(nodes=12, edges=30, seed=8)

    result = bellman_ford(graph, 0)

    assert result.source == 0
