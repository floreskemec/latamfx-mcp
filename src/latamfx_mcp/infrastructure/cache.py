"""A tiny async-safe TTL cache.

Upstream public APIs are rate-limited and their data only changes every few
minutes, so caching is both polite and faster. Kept dependency-free on purpose.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Caches the result of an async loader per key for ``ttl`` seconds."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = asyncio.Lock()

    async def get_or_load(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        now = time.monotonic()
        async with self._lock:
            hit = self._store.get(key)
            if hit is not None and now - hit[0] < self._ttl:
                return hit[1]
        # Load outside the lock so slow I/O does not serialize unrelated keys.
        value = await loader()
        async with self._lock:
            self._store[key] = (time.monotonic(), value)
        return value

    def clear(self) -> None:
        self._store.clear()
