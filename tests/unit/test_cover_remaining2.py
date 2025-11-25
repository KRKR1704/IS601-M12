# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from jose import JWTError

from app.auth import jwt as jwt_module
from app.auth.jwt import decode_token, TokenType
from app.models.user import User
from app.models import calculation as calc_models
from app.auth import dependencies as auth_deps
from app.schemas.user import UserCreate, PasswordUpdate
from app.schemas.calculation import CalculationBase


def test_get_current_user_full_payload_branch():
    full = {
        "id": uuid.uuid4(),
        "username": "fulluser",
        "email": "f@e.com",
        "first_name": "F",
        "last_name": "U",
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    orig = User.verify_token
    User.verify_token = classmethod(lambda cls, t: {**full, "username": full["username"]})
    resp = auth_deps.get_current_user(token="tok")
    assert resp.username == "fulluser"
    User.verify_token = orig


def test_jwt_decode_raises_expired_and_jwterror(monkeypatch):
    class _Err(Exception):
        pass

    def _raise_expired(*a, **k):
        from jose.exceptions import ExpiredSignatureError
        raise ExpiredSignatureError()

    monkeypatch.setattr(jwt_module, 'jwt', jwt_module.jwt)
    monkeypatch.setattr(jwt_module.jwt, 'decode', _raise_expired)
    with pytest.raises(Exception) as e:
        asyncio.run(decode_token('t', TokenType.ACCESS))
    assert 'Token has expired' in str(e.value)

    def _raise_jwterror(*a, **k):
        raise JWTError()

    monkeypatch.setattr(jwt_module.jwt, 'decode', _raise_jwterror)
    with pytest.raises(Exception) as e2:
        asyncio.run(decode_token('t', TokenType.ACCESS))
    assert 'Could not validate credentials' in str(e2.value)


def test_main_login_form_invalid(monkeypatch, db_session):
    from app.main import app
    monkeypatch.setattr(User, 'authenticate', classmethod(lambda cls, db, u, p: None))
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post('/auth/token', data={'username': 'x', 'password': 'y'})
    assert r.status_code == 401


def test_calculation_factory_and_power_success():
    with pytest.raises(ValueError):
        calc_models.AbstractCalculation.create('bogus', user_id=uuid.uuid4(), inputs=[1,2])

    p = calc_models.Power(user_id=uuid.uuid4(), inputs=[2, 3])
    assert p.get_result() == 8


def test_user_password_and_tokens(db_session):
    hp = User.hash_password('TestPass1!')
    u = User(first_name='A', last_name='B', email='t@t.com', username='u', hashed_password=hp)
    assert u.verify_password('TestPass1!') is True

    # tokens
    at = User.create_access_token({'sub': str(uuid.uuid4())})
    rt = User.create_refresh_token({'sub': str(uuid.uuid4())})
    assert isinstance(at, str) and isinstance(rt, str)


def test_user_schema_password_branches():
    with pytest.raises(ValueError):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='u', password='NoDigit!', confirm_password='NoDigit!')

    with pytest.raises(ValueError):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='u', password='NoDigit1', confirm_password='NoDigit1')

    with pytest.raises(ValueError):
        PasswordUpdate(current_password='Old1!x', new_password='Old1!x', confirm_new_password='Old1!x')


def test_calculation_schema_more_validators():
    with pytest.raises(ValueError):
        CalculationBase(type=None, inputs=[1,2])
