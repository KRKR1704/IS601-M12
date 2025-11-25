# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
from fastapi.testclient import TestClient
from app.main import app


def test_logout_revokes_refresh_token():
    client = TestClient(app)

    reg_payload = {
        "first_name": "Black",
        "last_name": "List",
        "email": "blacklist@example.com",
        "username": "blacklist_user",
        "password": "StrongPass1!",
        "confirm_password": "StrongPass1!"
    }
    r = client.post("/auth/register", json=reg_payload)
    assert r.status_code == 201

    login_payload = {"username": "blacklist_user", "password": "StrongPass1!"}
    r = client.post("/auth/login", json=login_payload)
    assert r.status_code == 200
    body = r.json()
    refresh = body.get("refresh_token")
    assert refresh

    headers = {"Authorization": f"Bearer {refresh}"}
    r = client.post("/auth/logout", headers=headers)
    assert r.status_code == 204

    from app.auth.jwt import decode_token
    from app.schemas.token import TokenType
    import pytest

    with pytest.raises(Exception):
        asyncio.run(decode_token(refresh, TokenType.REFRESH))
