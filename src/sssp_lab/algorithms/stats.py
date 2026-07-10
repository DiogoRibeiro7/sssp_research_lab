"""Operation counters shared by shortest-path experiments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OperationStats:
    """Mutable counters populated by algorithms when supplied by the caller."""

    relaxations: int = 0
    queue_pushes: int = 0
    queue_pops: int = 0
    stale_pops: int = 0
    settled_nodes: int = 0
    bucket_insertions: int = 0
    bucket_phases: int = 0
    light_relaxations: int = 0
    heavy_relaxations: int = 0
    bucket_reinserts: int = 0
    max_bucket_size: int = 0
    heuristic_evaluations: int = 0

    def as_dict(self) -> dict[str, int]:
        """Return counters in a serialization-friendly form."""

        return {
            "relaxations": self.relaxations,
            "queue_pushes": self.queue_pushes,
            "queue_pops": self.queue_pops,
            "stale_pops": self.stale_pops,
            "settled_nodes": self.settled_nodes,
            "bucket_insertions": self.bucket_insertions,
            "bucket_phases": self.bucket_phases,
            "light_relaxations": self.light_relaxations,
            "heavy_relaxations": self.heavy_relaxations,
            "bucket_reinserts": self.bucket_reinserts,
            "max_bucket_size": self.max_bucket_size,
            "heuristic_evaluations": self.heuristic_evaluations,
        }
