from __future__ import annotations

import pytest

from sssp_lab.algorithms.dial import dial_circular_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.rust_accel import RustSsspWorkspace, rust_backend_available
from sssp_lab.graph import Graph
from sssp_lab.utils import (
    assert_same_distances,
    make_equal_weight_graph,
    make_erdos_renyi_graph,
    make_grid_graph,
    make_heavy_tailed_graph,
    make_layered_dag,
    make_random_graph,
    make_road_like_graph,
    make_wide_integer_weight_graph,
)

pytestmark = pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")


def disconnected_graph() -> Graph:
    graph = Graph.from_edges([(0, 1, 3), (1, 2, 4), (5, 6, 1)], directed=True)
    graph.add_node(99)
    return graph


def arbitrary_id_graph() -> Graph:
    graph = Graph.from_edges(
        [
            (100, 400, 2),
            (100, 700, 9),
            (400, 250, 1),
            (250, 700, 3),
            (700, 900, 1),
        ],
        directed=True,
    )
    graph.add_node(1200)
    return graph


def zero_weight_graph() -> Graph:
    return Graph.from_edges(
        [
            (0, 1, 0),
            (1, 2, 0),
            (0, 3, 4),
            (2, 3, 1),
            (3, 4, 0),
        ],
        directed=True,
    )


def float_weight_graph() -> Graph:
    return Graph.from_edges(
        [
            (0, 1, 1.5),
            (0, 2, 3.25),
            (1, 2, 0.25),
            (2, 3, 2.5),
            (1, 4, 10.0),
        ],
        directed=True,
    )


INTEGER_CASES = [
    ("disconnected", disconnected_graph(), (0, 5, 99)),
    ("arbitrary_ids", arbitrary_id_graph(), (100, 400, 1200)),
    ("zero_weights", zero_weight_graph(), (0, 1, 4)),
    ("sparse_random", make_random_graph(nodes=12, edges=24, directed=True, seed=11), (0, 5, 9)),
    (
        "dense_erdos_renyi",
        make_erdos_renyi_graph(nodes=10, probability=0.35, directed=True, seed=13),
        (0, 3, 7),
    ),
    ("grid", make_grid_graph(4, 3, directed=False, weight=2), (0, 5, 11)),
    ("road_like", make_road_like_graph(width=4, height=4, seed=17), (0, 6, 15)),
    ("heavy_tailed", make_heavy_tailed_graph(nodes=14, edges=30, directed=True, seed=19), (0, 4, 8)),
    ("layered_dag", make_layered_dag(layers=4, width=4, seed=23), (0, 5, 12)),
    (
        "wide_integer_weights",
        make_wide_integer_weight_graph(nodes=10, edges=22, directed=True, seed=29),
        (0, 2, 6),
    ),
    ("equal_weights", make_equal_weight_graph(nodes=10, edges=20, directed=True, seed=31), (0, 3, 8)),
]

DIJKSTRA_CASES = [
    *INTEGER_CASES,
    ("float_weights", float_weight_graph(), (0, 1, 4)),
]


@pytest.mark.parametrize(("name", "graph", "sources"), DIJKSTRA_CASES, ids=[case[0] for case in DIJKSTRA_CASES])
def test_rust_workspace_dijkstra_matches_python_corpus(
    name: str,
    graph: Graph,
    sources: tuple[int, ...],
) -> None:
    del name
    workspace = RustSsspWorkspace.from_graph(graph)

    results = workspace.dijkstra_many(sources)

    assert len(results) == len(sources)
    for source, result in zip(sources, results, strict=True):
        assert result.source == source
        assert_same_distances(result.distances, dijkstra(graph, source).distances)
        single_result = workspace.dijkstra(source)
        assert_same_distances(single_result.distances, result.distances)


@pytest.mark.parametrize(("name", "graph", "sources"), INTEGER_CASES, ids=[case[0] for case in INTEGER_CASES])
def test_rust_workspace_circular_dial_matches_python_corpus(
    name: str,
    graph: Graph,
    sources: tuple[int, ...],
) -> None:
    del name
    workspace = RustSsspWorkspace.from_graph(graph)

    results = workspace.dial_circular_many(sources)

    assert len(results) == len(sources)
    for source, result in zip(sources, results, strict=True):
        assert result.source == source
        assert_same_distances(result.distances, dial_circular_sssp(graph, source).distances)
        single_result = workspace.dial_circular(source)
        assert_same_distances(single_result.distances, result.distances)
