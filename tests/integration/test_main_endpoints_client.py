# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.user import UserLogin
from app.models.user import User
from datetime import datetime
from uuid import uuid4


def test_health_endpoint_client():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_timezone_branch(monkeypatch, db_session):
    def fake_auth(db, username, password):
        dummy = User(first_name="A", last_name="B", email="a@b.com", username=username, password="x")
        dummy.id = uuid4()
        dummy.is_active = True
        dummy.is_verified = False
        return {
            "access_token": "t1",
            "refresh_token": "t2",
            "user": dummy,
            "expires_at": datetime.utcnow(),  # naive
        }

    monkeypatch.setattr(User, "authenticate", classmethod(lambda cls, db, u, p: fake_auth(db, u, p)))

    client = TestClient(app)
    payload = {"username": "u123", "password": "ValidPass1!"}
    r = client.post("/auth/login", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
