# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
import pytest

from app.auth import redis as auth_redis


def test_get_redis_and_blacklist_behavior():
    if hasattr(auth_redis.get_redis, "redis"):
        delattr(auth_redis.get_redis, "redis")
    red = asyncio.run(auth_redis.get_redis())
    asyncio.run(red.set("blacklist:foo", "1", ex=1))
    assert asyncio.run(red.exists("blacklist:foo")) == 1
