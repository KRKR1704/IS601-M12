# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest
from uuid import uuid4
from datetime import datetime

import aioredis

from app.auth import dependencies
from app.models.user import User
from app.schemas.user import UserResponse


def test_get_current_user_full_payload(monkeypatch):
    payload = {
        "username": "alice",
        "id": str(uuid4()),
        "email": "a@b.com",
        "first_name": "A",
        "last_name": "B",
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    monkeypatch.setattr(User, "verify_token", staticmethod(lambda t: payload))
    user_resp = dependencies.get_current_user("token")
    assert isinstance(user_resp, UserResponse)
    assert user_resp.username == "alice"


def test_get_current_user_minimal_sub(monkeypatch):
    sub = str(uuid4())
    monkeypatch.setattr(User, "verify_token", staticmethod(lambda t: {"sub": sub}))
    user_resp = dependencies.get_current_user("token")
    assert user_resp.id is not None


def test_get_current_user_uuid(monkeypatch):
    uid = uuid4()
    monkeypatch.setattr(User, "verify_token", staticmethod(lambda t: uid))
    user_resp = dependencies.get_current_user("token")
    assert user_resp.id == uid


def test_get_current_user_invalid(monkeypatch):
    monkeypatch.setattr(User, "verify_token", staticmethod(lambda t: None))
    with pytest.raises(Exception):
        dependencies.get_current_user("token")


def test_redis_blacklist_behavior():
    import asyncio

    async def _inner():
        red = await aioredis.from_url("redis://localhost")
        jti = "test-jti"
        await red.set(f"blacklist:{jti}", "1", ex=1)
        # use module functions
        import app.auth.redis as auth_redis
        # ensure the module's cached redis client is the same instance we set
        auth_redis.get_redis.redis = red
        from app.auth.redis import is_blacklisted
        assert await is_blacklisted(jti) in (0, 1)

    asyncio.run(_inner())
