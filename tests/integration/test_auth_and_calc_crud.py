# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4


def test_register_login_create_get_update_delete(db_session):
    client = TestClient(app)

    payload = {
        "first_name": "CR",
        "last_name": "UD",
        "email": f"{uuid4()}@ex.com",
        "username": f"user{uuid4().hex[:6]}",
        "password": "ValidPass1!",
        "confirm_password": "ValidPass1!"
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 201
    user = r.json()

    r = client.post("/auth/login", json={"username": payload["username"], "password": "ValidPass1!"})
    assert r.status_code == 200
    tokens = r.json()
    access = tokens["access_token"]

    headers = {"Authorization": f"Bearer {access}"}

    r = client.post("/calculations", json={"type": "addition", "inputs": [1, 2]}, headers=headers)
    assert r.status_code == 201
    cid = r.json()["id"]

    r = client.get(f"/calculations/{cid}", headers=headers)
    assert r.status_code == 200

    r = client.put(f"/calculations/{cid}", json={"inputs": [2, 3]}, headers=headers)
    assert r.status_code == 200
    assert r.json()["result"] == 5

    r = client.delete(f"/calculations/{cid}", headers=headers)
    assert r.status_code == 204

    r = client.get(f"/calculations/{cid}", headers=headers)
    assert r.status_code in (404, 400)

