# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
from uuid import uuid4

from app.auth import redis as auth_redis


def test_add_to_blacklist_and_check():
    jti = str(uuid4())
    asyncio.run(auth_redis.add_to_blacklist(jti, exp=1))
    assert asyncio.run(auth_redis.is_blacklisted(jti)) == 1
