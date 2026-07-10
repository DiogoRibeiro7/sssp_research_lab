"""Experimental stepping variants.

This module is intentionally conservative. It exposes useful policy hooks for
experiments without pretending to reproduce every algorithmic detail from the
stepping-algorithm literature.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sssp_lab.algorithms.delta_stepping import _bucket_index
from sssp_lab.algorithms.stats import OperationStats
from sssp_lab.graph import Graph, Node, PathResult
from sssp_lab.utils import initialise_single_source

DeltaPolicy = Callable[[Graph], float]
EdgePartitionPolicy = Callable[[float, float], bool]


@dataclass(frozen=True, slots=True)
class SteppingRun:
    """Path result and instrumentation for one stepping-policy run."""

    result: PathResult
    delta: float
    policy_name: str
    stats: OperationStats


def median_weight_delta(graph: Graph) -> float:
    """Return a robust default Δ based on the median edge weight."""

    weights = sorted(edge.weight for edge in graph.iter_edges() if edge.weight >= 0)
    if not weights:
        return 1.0
    return max(weights[len(weights) // 2], 1e-12)


def mean_weight_delta(graph: Graph) -> float:
    """Return Δ as the mean non-negative edge weight."""

    weights = [edge.weight for edge in graph.iter_edges() if edge.weight >= 0]
    if not weights:
        return 1.0
    return max(sum(weights) / len(weights), 1e-12)


def trimmed_mean_weight_delta(trim_fraction: float) -> DeltaPolicy:
    """Create a Δ policy from a trimmed mean of non-negative edge weights."""

    if not 0 <= trim_fraction < 0.5:
        raise ValueError("trim_fraction must be in [0, 0.5)")

    def policy(graph: Graph) -> float:
        weights = sorted(edge.weight for edge in graph.iter_edges() if edge.weight >= 0)
        if not weights:
            return 1.0
        trim_count = int(len(weights) * trim_fraction)
        if trim_count:
            weights = weights[trim_count:-trim_count]
        return max(sum(weights) / len(weights), 1e-12)

    return policy


def percentile_weight_delta(percentile: float) -> DeltaPolicy:
    """Create a Δ policy from a percentile of non-negative edge weights."""

    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be in [0, 100]")

    def policy(graph: Graph) -> float:
        weights = sorted(edge.weight for edge in graph.iter_edges() if edge.weight >= 0)
        if not weights:
            return 1.0
        index = round((percentile / 100) * (len(weights) - 1))
        return max(weights[index], 1e-12)

    return policy


def degree_adjusted_delta(graph: Graph) -> float:
    """Return Δ using average edge weight divided by maximum out-degree."""

    weights = [edge.weight for edge in graph.iter_edges() if edge.weight >= 0]
    if not weights:
        return 1.0
    max_degree = max((len(graph.neighbors(node)) for node in graph.nodes), default=1)
    return max(sum(weights) / len(weights) / max(max_degree, 1), 1e-12)


def max_degree_delta(graph: Graph) -> float:
    """Backward-compatible alias for :func:`degree_adjusted_delta`."""

    return degree_adjusted_delta(graph)


def adaptive_bucket_delta(graph: Graph) -> float:
    """Return a conservative Δ adjusted by average bucket occupancy pressure.

    This is an engineering heuristic: dense graphs use a smaller Δ to reduce
    bucket churn, while sparse graphs stay near the median weight.
    """

    base = median_weight_delta(graph)
    if not graph.nodes:
        return base
    density = graph.edge_count / max(len(graph.nodes), 1)
    return max(base / max(density, 1.0), 1e-12)


def light_edge_partition(weight: float, delta: float) -> bool:
    """Default edge partition: light edges have weight at most Δ."""

    return weight <= delta


def stepping_engine(
    graph: Graph,
    source: Node,
    *,
    delta: float,
    edge_partition_policy: EdgePartitionPolicy = light_edge_partition,
    stats: OperationStats | None = None,
) -> PathResult:
    """Run a generic sequential stepping engine.

    The engine separates the bucket-width policy from the light/heavy edge
    partition rule. It is intended for correctness-first experiments, not as a
    claim about any particular paper's formal algorithm.
    """

    if delta <= 0:
        raise ValueError("delta must be positive")
    graph.require_non_negative_weights()
    counters = stats if stats is not None else OperationStats()
    distances, predecessors = initialise_single_source(graph, source)
    buckets: dict[int, set[Node]] = {0: {source}}
    counters.bucket_insertions += 1
    counters.max_bucket_size = 1

    def relax(node: Node, candidate: float, predecessor: Node | None) -> None:
        if candidate < distances[node]:
            old_distance = distances[node]
            if old_distance != float("inf"):
                old_index = _bucket_index(old_distance, delta)
                if old_index in buckets:
                    buckets[old_index].discard(node)
                counters.bucket_reinserts += 1
            distances[node] = candidate
            predecessors[node] = predecessor
            new_index = _bucket_index(candidate, delta)
            buckets.setdefault(new_index, set()).add(node)
            counters.bucket_insertions += 1
            counters.max_bucket_size = max(counters.max_bucket_size, len(buckets[new_index]))

    while buckets:
        current_index = min(buckets)
        current_bucket = buckets[current_index]
        if not current_bucket:
            del buckets[current_index]
            continue
        counters.bucket_phases += 1
        settled_in_bucket: set[Node] = set()

        while current_bucket:
            active = set(current_bucket)
            current_bucket.clear()
            settled_in_bucket.update(active)
            for node in active:
                for edge in graph.neighbors(node):
                    if edge_partition_policy(edge.weight, delta):
                        counters.relaxations += 1
                        counters.light_relaxations += 1
                        relax(edge.target, distances[node] + edge.weight, node)
        del buckets[current_index]

        for node in settled_in_bucket:
            for edge in graph.neighbors(node):
                if not edge_partition_policy(edge.weight, delta):
                    counters.relaxations += 1
                    counters.heavy_relaxations += 1
                    relax(edge.target, distances[node] + edge.weight, node)
        counters.settled_nodes += len(settled_in_bucket)

    return PathResult(source=source, distances=distances, predecessors=predecessors)


def policy_delta_stepping(
    graph: Graph,
    source: Node,
    *,
    delta_policy: DeltaPolicy = median_weight_delta,
    stats: OperationStats | None = None,
) -> PathResult:
    """Run Δ-stepping using a user-supplied Δ policy."""

    delta = delta_policy(graph)
    return stepping_engine(graph, source, delta=delta, stats=stats)


def run_stepping_policy(
    graph: Graph,
    source: Node,
    *,
    policy_name: str,
    delta_policy: DeltaPolicy,
) -> SteppingRun:
    """Run one named Δ policy and return result, Δ value, and counters."""

    stats = OperationStats()
    delta = delta_policy(graph)
    result = stepping_engine(graph, source, delta=delta, stats=stats)
    return SteppingRun(result=result, delta=delta, policy_name=policy_name, stats=stats)
