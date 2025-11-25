# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth import jwt as jwt_module
from app.auth.jwt import create_token, decode_token, TokenType
from jose import jwt as jose_jwt
from app.core.config import settings
from datetime import datetime, timezone
import secrets


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_get_calculation_invalid_uuid_returns_400(test_user):
    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)

    r = client.get("/calculations/not-a-uuid", headers=_auth_header(token))
    assert r.status_code == 400
    assert "Invalid calculation id format" in r.text or "Invalid calculation id format." in r.text


def test_get_calculation_not_found_returns_404(test_user):
    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)
    random_id = str(uuid.uuid4())

    r = client.get(f"/calculations/{random_id}", headers=_auth_header(token))
    assert r.status_code == 404
    assert "Calculation not found" in r.text


def test_update_calculation_invalid_uuid_returns_400(test_user):
    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)

    r = client.put("/calculations/not-a-uuid", headers=_auth_header(token), json={})
    assert r.status_code == 400


def test_update_calculation_not_found_returns_404(test_user):
    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)
    random_id = str(uuid.uuid4())

    r = client.put(f"/calculations/{random_id}", headers=_auth_header(token), json={})
    assert r.status_code == 404


def test_delete_calculation_invalid_uuid_returns_400(test_user):
    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)

    r = client.delete("/calculations/not-a-uuid", headers=_auth_header(token))
    assert r.status_code == 400


def test_delete_calculation_not_found_returns_404(test_user):
    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)
    random_id = str(uuid.uuid4())

    r = client.delete(f"/calculations/{random_id}", headers=_auth_header(token))
    assert r.status_code == 404


def test_decode_token_wrong_type_raises_http_exception():
    fake_user_id = str(uuid.uuid4())
    payload = {
        "sub": fake_user_id,
        "type": TokenType.REFRESH.value,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_hex(8)
    }
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(Exception) as excinfo:
        asyncio.run(decode_token(token, TokenType.ACCESS))
    assert "Invalid token type" in str(excinfo.value)


def test_decode_token_revoked_token_raises(monkeypatch):
    fake_user_id = str(uuid.uuid4())
    token = create_token(fake_user_id, TokenType.ACCESS)

    async def _blacklisted(jti):
        return True

    monkeypatch.setattr(jwt_module, "is_blacklisted", _blacklisted)

    with pytest.raises(Exception) as excinfo:
        asyncio.run(decode_token(token, TokenType.ACCESS))
    assert "Token has been revoked" in str(excinfo.value)


def test_decode_token_expired_raises():
    # create an already-expired token
    fake_user_id = str(uuid.uuid4())
    token = create_token(fake_user_id, TokenType.ACCESS, expires_delta=timedelta(seconds=-10))

    with pytest.raises(Exception) as excinfo:
        asyncio.run(decode_token(token, TokenType.ACCESS))
    assert "Token has expired" in str(excinfo.value)


def test_decode_token_invalid_token_raises():
    with pytest.raises(Exception) as excinfo:
        asyncio.run(decode_token("this-is-not-a-token", TokenType.ACCESS))
    assert "Could not validate credentials" in str(excinfo.value)
