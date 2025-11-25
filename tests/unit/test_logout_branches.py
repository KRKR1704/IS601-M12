# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app


client = TestClient(app)


def _auth_header():
    return {"Authorization": "Bearer faketoken"}


def test_invalid_token_both_attempts_fail(monkeypatch):
    async def raise_http(*args, **kwargs):
        raise HTTPException(status_code=400)

    monkeypatch.setattr("app.main.decode_token", raise_http)

    resp = client.post("/auth/logout", headers=_auth_header())
    assert resp.status_code == 400


def test_missing_jti_or_exp(monkeypatch):
    async def ret_empty(*args, **kwargs):
        return {}

    monkeypatch.setattr("app.main.decode_token", ret_empty)

    resp = client.post("/auth/logout", headers=_auth_header())
    assert resp.status_code == 400
    assert resp.json().get("detail") == "Invalid token payload"


def test_exp_not_numeric_results_in_add_without_expiry(monkeypatch):
    calls = []

    async def ret_payload(*args, **kwargs):
        return {"jti": "my-jti", "exp": "not-a-number"}

    async def fake_add(jti, ttl):
        calls.append((jti, ttl))

    monkeypatch.setattr("app.main.decode_token", ret_payload)
    monkeypatch.setattr("app.main.add_to_blacklist", fake_add)

    resp = client.post("/auth/logout", headers=_auth_header())
    assert resp.status_code == 204
    assert calls == [("my-jti", 0)]


def test_exp_in_past_adds_without_expiry(monkeypatch):
    calls = []
    past = int(datetime.now(timezone.utc).timestamp()) - 10

    async def ret_payload(*args, **kwargs):
        return {"jti": "past-jti", "exp": past}

    async def fake_add(jti, ttl):
        calls.append((jti, ttl))

    monkeypatch.setattr("app.main.decode_token", ret_payload)
    monkeypatch.setattr("app.main.add_to_blacklist", fake_add)

    resp = client.post("/auth/logout", headers=_auth_header())
    assert resp.status_code == 204
    assert calls == [("past-jti", 0)]


def test_exp_in_future_adds_with_ttl(monkeypatch):
    calls = []
    future = int(datetime.now(timezone.utc).timestamp()) + 3600

    async def ret_payload(*args, **kwargs):
        return {"jti": "future-jti", "exp": future}

    async def fake_add(jti, ttl):
        calls.append((jti, ttl))

    monkeypatch.setattr("app.main.decode_token", ret_payload)
    monkeypatch.setattr("app.main.add_to_blacklist", fake_add)

    resp = client.post("/auth/logout", headers=_auth_header())
    assert resp.status_code == 204
    assert len(calls) == 1
    assert calls[0][0] == "future-jti"
    # TTL should be positive
    assert isinstance(calls[0][1], int) and calls[0][1] > 0
