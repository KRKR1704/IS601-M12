# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
from typing import Optional


class _InMemoryRedis:
    def __init__(self):
        self._store = {}
        self._locks = {}

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        self._store[key] = value
        if ex is not None:
            async def expire_key(k, delay):
                await asyncio.sleep(delay)
                try:
                    del self._store[k]
                except KeyError:
                    pass
            asyncio.create_task(expire_key(key, ex))

    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0


async def from_url(url: str):
    """Return an in-memory Redis-like client.

    The real `aioredis.from_url` is async and returns a client instance.
    This function mirrors that behavior so the application code can
    `await aioredis.from_url(...)` as usual.
    """
    return _InMemoryRedis()
