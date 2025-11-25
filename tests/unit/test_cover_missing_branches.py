# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import importlib
import uuid
from datetime import timedelta, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import JWTError

from app.auth import dependencies as auth_deps
from app.core import config as app_config
from app.auth import jwt as jwt_module
from app.models import calculation as calc_models
from app.models.user import User
from app.schemas.calculation import CalculationBase, CalculationType
from app.schemas.user import UserCreate, PasswordUpdate
from app.main import app


def test_get_current_user_token_none_raises():
    # Simulate verify_token returning None
    orig = User.verify_token
    User.verify_token = classmethod(lambda cls, t: None)
    with pytest.raises(Exception) as excinfo:
        auth_deps.get_current_user(token="invalid")
    assert "Could not validate credentials" in str(excinfo.value)
    User.verify_token = orig


def test_get_current_user_minimal_payload_and_uuid_payload():
    # dict with sub only
    sub_id = uuid.uuid4()
    orig = User.verify_token
    User.verify_token = classmethod(lambda cls, t: {"sub": str(sub_id)})
    resp = auth_deps.get_current_user(token="tok")
    assert resp.id is not None

    # return a UUID directly
    User.verify_token = classmethod(lambda cls, t: sub_id)
    resp2 = auth_deps.get_current_user(token="tok2")
    assert resp2.id == sub_id
    User.verify_token = orig


def test_get_current_active_user_inactive_raises():
    from app.schemas.user import UserResponse
    user = UserResponse(
        id=uuid.uuid4(), username="u", email="e@e.com", first_name="a", last_name="b",
        is_active=False, is_verified=False, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    with pytest.raises(Exception) as excinfo:
        auth_deps.get_current_active_user(current_user=user)
    assert "Inactive user" in str(excinfo.value)


def test_config_postgres_branch(monkeypatch):
    # Reload module with TEST_DATABASE=postgres to exercise branch
    monkeypatch.setenv("TEST_DATABASE", "postgres")
    import importlib
    import app.core.config as cfg
    importlib.reload(cfg)
    assert "postgresql" in cfg.settings.DATABASE_URL


def test_create_calculation_endpoint_handles_valueerror(test_user, monkeypatch):
    client = TestClient(app)
    token = jwt_module.create_token(test_user.id, jwt_module.TokenType.ACCESS)

    def _bad_create(calculation_type, user_id, inputs):
        raise ValueError("bad")

    monkeypatch.setattr(calc_models.AbstractCalculation, "create", classmethod(lambda cls, *a, **k: (_ for _ in ()).throw(ValueError("bad"))))

    r = client.post("/calculations", headers={"Authorization": f"Bearer {token}"}, json={"type":"addition","inputs":[1,2]})
    assert r.status_code == 400


def test_calculation_model_edge_cases():
    # Addition errors
    add = calc_models.Addition(user_id=uuid.uuid4(), inputs="notalist")
    with pytest.raises(ValueError):
        add.get_result()
    add2 = calc_models.Addition(user_id=uuid.uuid4(), inputs=[1])
    with pytest.raises(ValueError):
        add2.get_result()

    # Division by zero
    div = calc_models.Division(user_id=uuid.uuid4(), inputs=[10, 0])
    with pytest.raises(ValueError):
        div.get_result()

    # Power wrong inputs
    p = calc_models.Power(user_id=uuid.uuid4(), inputs=[2])
    with pytest.raises(ValueError):
        p.get_result()


def test_user_verify_token_and_register_edgecases(db_session):
    # verify_token returns None on invalid token
    assert User.verify_token("not-a-token") is None

    # register with short password
    with pytest.raises(ValueError):
        User.register(db_session, {"first_name":"a","last_name":"b","email":"x@x.com","username":"u","password":"short"})


def test_calculation_schema_validators():
    # invalid type
    with pytest.raises(ValueError):
        CalculationBase(type=123, inputs=[1,2])
    # inputs not list
    with pytest.raises(ValueError):
        CalculationBase(type="addition", inputs="nope")
    # power requires exactly two
    with pytest.raises(ValueError):
        CalculationBase(type="power", inputs=[2,3,4])


def test_user_schema_password_validators():
    # passwords do not match
    with pytest.raises(ValueError):
        UserCreate(first_name="a", last_name="b", email="x@x.com", username="u", password="Aa1!aaaa", confirm_password="diff")

    # missing uppercase
    with pytest.raises(ValueError):
        UserCreate(first_name="a", last_name="b", email="x@x.com", username="u", password="aa1!aaaa", confirm_password="aa1!aaaa")

    # password update same as current
    with pytest.raises(ValueError):
        PasswordUpdate(current_password="Old1!pass", new_password="Old1!pass", confirm_new_password="Old1!pass")
