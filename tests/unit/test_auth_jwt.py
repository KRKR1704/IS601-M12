# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest
from datetime import timedelta, datetime, timezone
from uuid import uuid4

from app.auth.redis import get_redis

from app.auth import jwt as auth_jwt
from app.schemas.token import TokenType
from app.core.config import settings
from jose import jwt as jose_jwt


def test_create_and_decode_token_success():
    import asyncio
    user_id = str(uuid4())
    token = auth_jwt.create_token(user_id, TokenType.ACCESS)
    payload = asyncio.run(auth_jwt.decode_token(token, TokenType.ACCESS))
    assert payload["sub"] == user_id


def test_password_hash_and_verify():
    pw = "TestPass123!"
    hashed = auth_jwt.get_password_hash(pw)
    assert auth_jwt.verify_password(pw, hashed)


def test_decode_invalid_type_raises():
    import asyncio
    user_id = str(uuid4())
    token = auth_jwt.create_token(user_id, TokenType.ACCESS)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.decode_token(token, TokenType.REFRESH))
    # Depending on JWT secret behavior the decode may fail with a signature error
    # or raise the explicit Invalid token type. Accept either outcome.
    msg = str(excinfo.value)
    assert "Invalid token type" in msg or "Could not validate credentials" in msg


def test_decode_expired_raises():
    import asyncio
    user_id = str(uuid4())
    token = auth_jwt.create_token(user_id, TokenType.ACCESS, expires_delta=timedelta(seconds=-1))
    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.decode_token(token, TokenType.ACCESS))
    assert "Token has expired" in str(excinfo.value)


def test_decode_revoked_raises():
    import asyncio
    user_id = str(uuid4())
    token = auth_jwt.create_token(user_id, TokenType.ACCESS)
    # Extract payload to get jti
    payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti = payload["jti"]
    # Add to blacklist using the app's cached redis client so decode_token sees it
    red = asyncio.run(get_redis())
    asyncio.run(red.set(f"blacklist:{jti}", "1", ex=60))

    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.decode_token(token, TokenType.ACCESS))
    assert "Token has been revoked" in str(excinfo.value)


def test_decode_invalid_token_raises():
    import asyncio
    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.decode_token("not-a-token", TokenType.ACCESS))
    assert "Could not validate credentials" in str(excinfo.value)


def test_get_current_user_not_found(db_session):
    import asyncio
    # Token for a user id that does not exist
    token = auth_jwt.create_token(str(uuid4()), TokenType.ACCESS)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.get_current_user(token=token, db=db_session))
    # Should raise an HTTPException (401/404) - accept either
    from fastapi import HTTPException
    assert isinstance(excinfo.value, HTTPException)
    assert excinfo.value.status_code in (401, 404)
