"""Optional Rust acceleration wrappers for shortest-path kernels."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import ModuleType

from sssp_lab.graph import Graph, Node, PathResult

try:
    _sssp_accel: ModuleType | None = import_module("sssp_lab._sssp_accel")
except ImportError:  # pragma: no cover - depends on optional local build
    _sssp_accel = None


class RustBackendUnavailable(RuntimeError):
    """Raised when an optional Rust acceleration function is requested but absent."""


@dataclass(frozen=True, slots=True)
class CSRGraph:
    """Compressed sparse row arrays and node-id mappings."""

    nodes: tuple[Node, ...]
    offsets: list[int]
    targets: list[int]
    weights: list[float]


def rust_backend_available() -> bool:
    """Return whether the optional Rust extension is importable."""

    return _sssp_accel is not None


def _backend() -> ModuleType:
    if _sssp_accel is None:
        raise RustBackendUnavailable(
            "Rust backend is not installed; run `maturin develop` in rust/sssp_accel"
        )
    return _sssp_accel


def graph_to_csr(graph: Graph) -> CSRGraph:
    """Convert a graph with arbitrary integer node ids to CSR arrays."""

    nodes = tuple(sorted(graph.nodes))
    index = {node: position for position, node in enumerate(nodes)}
    offsets: list[int] = [0]
    targets: list[int] = []
    weights: list[float] = []
    for node in nodes:
        for edge in graph.neighbors(node):
            targets.append(index[edge.target])
            weights.append(edge.weight)
        offsets.append(len(targets))
    return CSRGraph(nodes=nodes, offsets=offsets, targets=targets, weights=weights)


def _predecessor_map(nodes: tuple[Node, ...], raw_predecessors: list[int | None]) -> dict[Node, Node | None]:
    return {
        node: None if predecessor is None else nodes[predecessor]
        for node, predecessor in zip(nodes, raw_predecessors, strict=True)
    }


def _distance_map(nodes: tuple[Node, ...], raw_distances: list[float]) -> dict[Node, float]:
    return dict(zip(nodes, raw_distances, strict=True))


def dijkstra_rust(graph: Graph, source: Node) -> PathResult:
    """Compute non-negative SSSP through the optional Rust Dijkstra kernel."""

    backend = _backend()
    graph.require_non_negative_weights()
    graph.require_node(source)
    csr = graph_to_csr(graph)
    source_index = csr.nodes.index(source)
    raw_distances, raw_predecessors = backend.dijkstra_csr(
        len(csr.nodes),
        csr.offsets,
        csr.targets,
        csr.weights,
        source_index,
    )
    return PathResult(
        source=source,
        distances=_distance_map(csr.nodes, raw_distances),
        predecessors=_predecessor_map(csr.nodes, raw_predecessors),
    )


def dial_circular_rust(graph: Graph, source: Node) -> PathResult:
    """Compute integer SSSP through the optional Rust circular-Dial kernel."""

    backend = _backend()
    graph.require_non_negative_weights()
    graph.require_integer_weights()
    graph.require_node(source)
    csr = graph_to_csr(graph)
    source_index = csr.nodes.index(source)
    integer_weights = [int(weight) for weight in csr.weights]
    raw_distances, raw_predecessors = backend.dial_circular_csr(
        len(csr.nodes),
        csr.offsets,
        csr.targets,
        integer_weights,
        source_index,
    )
    return PathResult(
        source=source,
        distances=_distance_map(csr.nodes, raw_distances),
        predecessors=_predecessor_map(csr.nodes, raw_predecessors),
    )


__all__ = [
    "CSRGraph",
    "RustBackendUnavailable",
    "dial_circular_rust",
    "dijkstra_rust",
    "graph_to_csr",
    "rust_backend_available",
]
