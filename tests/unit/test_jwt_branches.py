# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
import pytest
from datetime import timedelta
from uuid import uuid4

from jose import jwt as jose_jwt

from app.auth import jwt as auth_jwt
from app.schemas.token import TokenType


def test_decode_invalid_type_explicit():
    user_id = str(uuid4())
    token = auth_jwt.create_token(user_id, TokenType.ACCESS)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.decode_token(token, TokenType.REFRESH))
    assert "Invalid token type" in str(excinfo.value) or "Could not validate credentials" in str(excinfo.value)


def test_decode_expired_explicit():
    user_id = str(uuid4())
    token = auth_jwt.create_token(user_id, TokenType.ACCESS, expires_delta=timedelta(seconds=-10))
    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.decode_token(token, TokenType.ACCESS))
    assert "Token has expired" in str(excinfo.value) or "Could not validate" in str(excinfo.value)


def test_decode_revoked_via_monkeypatch(monkeypatch):
    user_id = str(uuid4())
    token = auth_jwt.create_token(user_id, TokenType.ACCESS)

    async def fake_is_blacklisted(jti):
        return True

    monkeypatch.setattr(auth_jwt, "is_blacklisted", fake_is_blacklisted)

    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.decode_token(token, TokenType.ACCESS))
    assert "Token has been revoked" in str(excinfo.value)


def test_create_token_exception_path(monkeypatch):
    def fake_encode(payload, secret, algorithm=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(auth_jwt.jwt, "encode", fake_encode)
    with pytest.raises(Exception) as excinfo:
        auth_jwt.create_token(str(uuid4()), TokenType.ACCESS)
    assert "Could not create token" in str(excinfo.value)
