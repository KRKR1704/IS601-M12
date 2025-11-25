# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.models.calculation import Calculation
from app.models.user import User
from app.auth.dependencies import get_current_active_user


def make_user_for_dependency(db_session):
    data = {
        "first_name": "Dep",
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


def test_create_list_get_update_delete_calculation(monkeypatch, db_session):
    # Create a persisted user and monkeypatch dependency to return it
    user = make_user_for_dependency(db_session)

    # Override the dependency used by the routes to return our test user
    app.dependency_overrides[get_current_active_user] = lambda: user

    client = TestClient(app)

    # create addition calculation
    payload = {"type": "addition", "inputs": [1, 2, 3]}
    r = client.post("/calculations", json=payload)
    assert r.status_code == 201
    cid = r.json()["id"]

    # list calculations
    r = client.get("/calculations")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    # get calculation with invalid id
    r = client.get("/calculations/not-a-uuid")
    assert r.status_code == 400

    # get non-existent calculation
    r = client.get(f"/calculations/{uuid4()}")
    assert r.status_code in (404, 400)

    # update invalid id (body validation may return 422 for invalid inputs)
    r = client.put("/calculations/not-a-uuid", json={"inputs": [5]})
    assert r.status_code in (400, 422)

    # delete invalid id
    r = client.delete("/calculations/not-a-uuid")
    assert r.status_code == 400

    # cleanup dependency override
    app.dependency_overrides.pop(get_current_active_user, None)
