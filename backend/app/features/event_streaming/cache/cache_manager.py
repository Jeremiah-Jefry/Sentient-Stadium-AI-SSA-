"""Multi-layer cache abstraction for event streaming data."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_L1_MAX_SIZE = 1000
DEFAULT_L1_TTL_SECONDS = 60
DEFAULT_L2_TTL_SECONDS = 300


@dataclass(slots=True)
class CacheEntry:
    """A single cache entry with value, expiry, and access tracking."""

    key: str
    value: object
    created_at: float
    ttl_seconds: float
    access_count: int = 0
    last_accessed: float = 0.0

    @property
    def is_expired(self) -> bool:
        return time.monotonic() - self.created_at > self.ttl_seconds


class CacheManager:
    """Two-layer in-memory cache with L1 (hot) and L2 (warm) tiers.

    L1: Small, fast, short TTL for frequently accessed data.
    L2: Larger, longer TTL for less frequent but still needed data.
    Both layers use LRU eviction when capacity is reached.
    """

    def __init__(
        self,
        l1_max_size: int = DEFAULT_L1_MAX_SIZE,
        l1_ttl: float = DEFAULT_L1_TTL_SECONDS,
        l2_max_size: int = DEFAULT_L1_MAX_SIZE * 5,
        l2_ttl: float = DEFAULT_L2_TTL_SECONDS,
    ) -> None:
        self._l1: OrderedDict[str, CacheEntry] = OrderedDict()
        self._l2: OrderedDict[str, CacheEntry] = OrderedDict()
        self._l1_max = l1_max_size
        self._l1_ttl = l1_ttl
        self._l2_max = l2_max_size
        self._l2_ttl = l2_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> object | None:
        """Retrieve a value from cache (checks L1 then L2)."""
        entry = self._l1.get(key)
        if entry is not None and not entry.is_expired:
            self._l1.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = time.monotonic()
            self._hits += 1
            return entry.value

        if entry is not None:
            del self._l1[key]

        entry = self._l2.get(key)
        if entry is not None and not entry.is_expired:
            self._l2.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = time.monotonic()
            self._promote_to_l1(key, entry)
            self._hits += 1
            return entry.value

        if entry is not None:
            del self._l2[key]

        self._misses += 1
        return None

    def set(self, key: str, value: object, ttl: float | None = None, l1_only: bool = False) -> None:
        """Store a value in the cache."""
        now = time.monotonic()
        entry = CacheEntry(
            key=key, value=value,
            created_at=now, ttl_seconds=ttl or self._l1_ttl,
            last_accessed=now,
        )

        self._l1[key] = entry
        self._l1.move_to_end(key)

        if len(self._l1) > self._l1_max:
            self._evict_l1()

        if not l1_only:
            l2_entry = CacheEntry(
                key=key, value=value,
                created_at=now, ttl_seconds=self._l2_ttl,
                last_accessed=now,
            )
            self._l2[key] = l2_entry
            self._l2.move_to_end(key)
            if len(self._l2) > self._l2_max:
                self._evict_l2()

    def delete(self, key: str) -> bool:
        """Remove a key from both cache layers."""
        removed = False
        if key in self._l1:
            del self._l1[key]
            removed = True
        if key in self._l2:
            del self._l2[key]
            removed = True
        return removed

    def clear(self, layer: str | None = None) -> None:
        """Clear one or both cache layers."""
        if layer == "l1" or layer is None:
            self._l1.clear()
        if layer == "l2" or layer is None:
            self._l2.clear()

    def _promote_to_l1(self, key: str, entry: CacheEntry) -> None:
        """Promote a frequently accessed L2 entry to L1."""
        l1_entry = CacheEntry(
            key=key, value=entry.value,
            created_at=time.monotonic(), ttl_seconds=self._l1_ttl,
            access_count=entry.access_count,
        )
        self._l1[key] = l1_entry
        self._l1.move_to_end(key)
        if len(self._l1) > self._l1_max:
            self._evict_l1()

    def _evict_l1(self) -> None:
        """Evict least recently used entry from L1."""
        if self._l1:
            self._l1.popitem(last=False)

    def _evict_l2(self) -> None:
        """Evict least recently used entry from L2."""
        if self._l2:
            self._l2.popitem(last=False)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "l1_size": len(self._l1),
            "l2_size": len(self._l2),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
        }
