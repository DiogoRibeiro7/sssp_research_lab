from __future__ import annotations

import pytest

from sssp_lab.algorithms.dial import dial_circular_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.rust_accel import (
    RustBackendUnavailable,
    dial_circular_rust,
    dijkstra_rust,
    graph_to_csr,
    rust_backend_available,
)
from sssp_lab.graph import Graph
from sssp_lab.utils import assert_same_distances


def test_graph_to_csr_preserves_arbitrary_node_ids() -> None:
    graph = Graph.from_edges([(10, 20, 2), (10, 30, 5), (20, 30, 1)], directed=True)

    csr = graph_to_csr(graph)

    assert csr.nodes == (10, 20, 30)
    assert csr.offsets == [0, 2, 3, 3]
    assert csr.targets == [1, 2, 2]
    assert csr.weights == [2.0, 5.0, 1.0]


def test_rust_backend_unavailable_contract() -> None:
    if rust_backend_available():
        pytest.skip("Rust backend is installed")

    graph = Graph.from_edges([(0, 1, 1)], directed=True)

    with pytest.raises(RustBackendUnavailable):
        dijkstra_rust(graph, 0)


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_dijkstra_matches_python_reference() -> None:
    graph = Graph.from_edges(
        [(10, 20, 2), (10, 30, 5), (20, 30, 1), (30, 40, 3)],
        directed=True,
    )

    result = dijkstra_rust(graph, 10)

    assert_same_distances(result.distances, dijkstra(graph, 10).distances)
    assert result.path_to(40) == [10, 20, 30, 40]


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_circular_dial_matches_python_reference() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 3)],
        directed=True,
    )

    result = dial_circular_rust(graph, 0)

    assert_same_distances(result.distances, dial_circular_sssp(graph, 0).distances)
