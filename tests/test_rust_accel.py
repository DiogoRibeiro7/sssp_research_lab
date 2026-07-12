from __future__ import annotations

import pytest

from sssp_lab.algorithms.dial import dial_circular_sssp
from sssp_lab.algorithms.dijkstra_binary_heap import dijkstra
from sssp_lab.algorithms.rust_accel import (
    RustBackendUnavailable,
    RustSsspWorkspace,
    dial_circular_rust,
    dial_circular_rust_csr,
    dial_circular_rust_csr_many,
    dijkstra_rust,
    dijkstra_rust_csr,
    dijkstra_rust_csr_many,
    graph_to_csr,
    rust_backend_available,
)
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph
from sssp_lab.utils import assert_same_distances


def test_graph_to_csr_preserves_arbitrary_node_ids() -> None:
    graph = Graph.from_edges([(10, 20, 2), (10, 30, 5), (20, 30, 1)], directed=True)

    csr = graph_to_csr(graph)

    assert csr.nodes == (10, 20, 30)
    assert csr.node_to_index == {10: 0, 20: 1, 30: 2}
    assert csr.offsets == [0, 2, 3, 3]
    assert csr.targets == [1, 2, 2]
    assert csr.weights == [2.0, 5.0, 1.0]
    assert csr.source_index(20) == 1


def test_csr_rejects_missing_source() -> None:
    graph = Graph.from_edges([(10, 20, 2)], directed=True)
    csr = graph_to_csr(graph)

    with pytest.raises(ValueError):
        csr.source_index(99)


def test_workspace_prepares_reusable_csr_arrays() -> None:
    graph = Graph.from_edges([(10, 20, 2), (10, 30, 5), (20, 30, 1)], directed=True)

    workspace = RustSsspWorkspace.from_graph(graph)

    assert workspace.csr.nodes == (10, 20, 30)
    assert workspace.csr.offsets == [0, 2, 3, 3]
    assert workspace.csr.targets == [1, 2, 2]
    assert workspace.csr.weights == [2.0, 5.0, 1.0]
    assert workspace.integer_weights == [2, 5, 1]


def test_workspace_keeps_float_graphs_for_dijkstra_only() -> None:
    graph = Graph.from_edges([(0, 1, 1.5)], directed=True)

    workspace = RustSsspWorkspace.from_graph(graph)

    assert workspace.integer_weights is None
    with pytest.raises(ValueError):
        workspace.dial_circular(0)


def test_rust_backend_unavailable_contract() -> None:
    if rust_backend_available():
        pytest.skip("Rust backend is installed")

    graph = Graph.from_edges([(0, 1, 1)], directed=True)

    with pytest.raises(RustBackendUnavailable):
        dijkstra_rust(graph, 0, stats=OperationStats())
    with pytest.raises(RustBackendUnavailable):
        RustSsspWorkspace.from_graph(graph).dijkstra(0, stats=OperationStats())


def test_rust_csr_stats_validate_source_before_backend() -> None:
    graph = Graph.from_edges([(0, 1, 1)], directed=True)
    csr = graph_to_csr(graph)
    stats = OperationStats()

    with pytest.raises(ValueError):
        dijkstra_rust_csr(csr, 99, stats=stats)

    assert stats.as_dict() == OperationStats().as_dict()


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
def test_rust_dijkstra_accepts_prebuilt_csr() -> None:
    graph = Graph.from_edges(
        [(10, 20, 2), (10, 30, 5), (20, 30, 1), (30, 40, 3)],
        directed=True,
    )
    csr = graph_to_csr(graph)

    result = dijkstra_rust_csr(csr, 10)

    assert_same_distances(result.distances, dijkstra(graph, 10).distances)


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_dijkstra_populates_structural_stats() -> None:
    graph = Graph.from_edges(
        [(10, 20, 2), (10, 30, 5), (20, 30, 1), (30, 40, 3)],
        directed=True,
    )
    stats = OperationStats()

    result = dijkstra_rust(graph, 10, stats=stats)

    assert_same_distances(result.distances, dijkstra(graph, 10).distances)
    assert stats.settled_nodes == 4
    assert stats.relaxations == 4
    assert stats.queue_pushes == 4
    assert stats.queue_pops == 4


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_dijkstra_accepts_batched_sources() -> None:
    graph = Graph.from_edges(
        [(10, 20, 2), (10, 30, 5), (20, 30, 1), (30, 40, 3)],
        directed=True,
    )
    csr = graph_to_csr(graph)

    results = dijkstra_rust_csr_many(csr, (10, 20))

    assert len(results) == 2
    assert_same_distances(results[0].distances, dijkstra(graph, 10).distances)
    assert_same_distances(results[1].distances, dijkstra(graph, 20).distances)


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_workspace_runs_dijkstra_sources() -> None:
    graph = Graph.from_edges(
        [(10, 20, 2), (10, 30, 5), (20, 30, 1), (30, 40, 3)],
        directed=True,
    )
    workspace = RustSsspWorkspace.from_graph(graph)

    result = workspace.dijkstra(10)
    results = workspace.dijkstra_many((10, 20))

    assert_same_distances(result.distances, dijkstra(graph, 10).distances)
    assert len(results) == 2
    assert_same_distances(results[0].distances, dijkstra(graph, 10).distances)
    assert_same_distances(results[1].distances, dijkstra(graph, 20).distances)


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_circular_dial_matches_python_reference() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 3)],
        directed=True,
    )

    result = dial_circular_rust(graph, 0)

    assert_same_distances(result.distances, dial_circular_sssp(graph, 0).distances)


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_circular_dial_accepts_prebuilt_csr() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 3)],
        directed=True,
    )
    csr = graph_to_csr(graph)

    result = dial_circular_rust_csr(csr, 0)

    assert_same_distances(result.distances, dial_circular_sssp(graph, 0).distances)


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_circular_dial_populates_structural_stats() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 3)],
        directed=True,
    )
    stats = OperationStats()

    result = dial_circular_rust(graph, 0, stats=stats)

    assert_same_distances(result.distances, dial_circular_sssp(graph, 0).distances)
    assert stats.settled_nodes == 4
    assert stats.relaxations == 4
    assert stats.bucket_insertions == 4
    assert stats.max_bucket_size == 4


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_rust_circular_dial_accepts_batched_sources() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 3)],
        directed=True,
    )
    csr = graph_to_csr(graph)

    results = dial_circular_rust_csr_many(csr, (0, 1))

    assert len(results) == 2
    assert_same_distances(results[0].distances, dial_circular_sssp(graph, 0).distances)
    assert_same_distances(results[1].distances, dial_circular_sssp(graph, 1).distances)


@pytest.mark.skipif(not rust_backend_available(), reason="Rust backend is not installed")
def test_workspace_runs_circular_dial_sources() -> None:
    graph = Graph.from_edges(
        [(0, 1, 2), (0, 2, 5), (1, 2, 1), (2, 3, 3)],
        directed=True,
    )
    workspace = RustSsspWorkspace.from_graph(graph)

    result = workspace.dial_circular(0)
    results = workspace.dial_circular_many((0, 1))

    assert_same_distances(result.distances, dial_circular_sssp(graph, 0).distances)
    assert len(results) == 2
    assert_same_distances(results[0].distances, dial_circular_sssp(graph, 0).distances)
    assert_same_distances(results[1].distances, dial_circular_sssp(graph, 1).distances)
