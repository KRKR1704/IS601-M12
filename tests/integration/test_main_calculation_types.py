# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app
from app.models.user import User
from app.auth.dependencies import get_current_active_user


def create_user(db_session):
    data = {
        "first_name": "Calc",
        "last_name": "User",
        "email": f"{uuid4()}@ex.com",
        "username": f"u{uuid4()}",
        "password": "ValidPass1!"
    }
    u = User(**data)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_create_each_calculation_type(monkeypatch, db_session):
    user = create_user(db_session)
    app.dependency_overrides[get_current_active_user] = lambda: user
    client = TestClient(app)

    payloads = [
        {"type": "addition", "inputs": [1, 2]},
        {"type": "subtraction", "inputs": [5, 2]},
        {"type": "multiplication", "inputs": [2, 3]},
        {"type": "division", "inputs": [10, 2]},
        {"type": "power", "inputs": [2, 4]},
    ]

    for p in payloads:
        r = client.post("/calculations", json=p)
        assert r.status_code == 201
        j = r.json()
        assert "id" in j

    app.dependency_overrides.pop(get_current_active_user, None)
