# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import uuid
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.auth.jwt import create_token, TokenType
from app.models.calculation import Calculation


def _auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_update_calculation_change_type_success(db_session, test_user):
    # create an addition calculation for the user
    calc = Calculation.create(calculation_type='addition', user_id=test_user.id, inputs=[2, 3])
    db_session.add(calc)
    db_session.commit()
    db_session.refresh(calc)

    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)

    r = client.put(f"/calculations/{calc.id}", headers=_auth_header(token), json={"type": "multiplication"})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "multiplication"
    assert body["result"] == 6


def test_update_calculation_change_type_server_side_error(db_session, test_user):
    # create a calculation with 3 inputs
    calc = Calculation.create(calculation_type='addition', user_id=test_user.id, inputs=[2, 3, 4])
    db_session.add(calc)
    db_session.commit()
    db_session.refresh(calc)

    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)

    r = client.put(f"/calculations/{calc.id}", headers=_auth_header(token), json={"type": "power"})
    assert r.status_code == 400


def test_update_calculation_power_inputs_validation_422(test_user):
    client = TestClient(app)
    token = create_token(test_user.id, TokenType.ACCESS)
    create_payload = {"type": "addition", "inputs": [1, 2]}
    r_create = client.post("/calculations", headers=_auth_header(token), json=create_payload)
    assert r_create.status_code == 201
    calc_id = r_create.json()["id"]

    r = client.put(f"/calculations/{calc_id}", headers=_auth_header(token), json={"type": "power", "inputs": [2,3,4]})
    assert r.status_code == 422
