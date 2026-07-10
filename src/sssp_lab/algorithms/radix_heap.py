"""Monotone radix heap for non-negative integer keys.

The queue supports push and pop-min when inserted keys are never smaller than
previously popped keys. Dijkstra with non-negative integer weights satisfies
that condition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class RadixHeap(Generic[T]):
    """A monotone priority queue for integer keys."""

    max_bits: int = 64
    _last: int = 0
    _size: int = 0
    _buckets: list[list[tuple[int, T]]] = field(init=False)

    def __post_init__(self) -> None:
        if self.max_bits <= 0:
            raise ValueError("max_bits must be positive")
        self._buckets = [[] for _ in range(self.max_bits + 1)]

    def __len__(self) -> int:
        return self._size

    @staticmethod
    def _bucket_index(key: int, last: int) -> int:
        return (key ^ last).bit_length()

    def push(self, key: int, value: T) -> None:
        """Insert ``value`` with integer ``key``."""

        if not isinstance(key, int):
            raise TypeError("key must be an int")
        if key < self._last:
            raise ValueError("radix heap requires monotone non-decreasing keys")
        index = self._bucket_index(key, self._last)
        if index > self.max_bits:
            raise ValueError("key exceeds configured max_bits")
        self._buckets[index].append((key, value))
        self._size += 1

    def pop(self) -> tuple[int, T]:
        """Remove and return the smallest key-value pair."""

        if self._size == 0:
            raise IndexError("pop from empty radix heap")

        if not self._buckets[0]:
            index = next(i for i, bucket in enumerate(self._buckets) if bucket)
            self._last = min(key for key, _ in self._buckets[index])
            old_bucket = self._buckets[index]
            self._buckets[index] = []
            for key, value in old_bucket:
                new_index = self._bucket_index(key, self._last)
                self._buckets[new_index].append((key, value))

        self._size -= 1
        return self._buckets[0].pop()
