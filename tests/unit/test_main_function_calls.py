# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest
from fastapi import HTTPException

from app.main import register, login_json, login_form, create_calculation
from app.schemas.user import UserCreate, UserLogin
from app.schemas.calculation import CalculationBase
from app.models.user import User
from fastapi.security import OAuth2PasswordRequestForm


def test_register_and_duplicate_direct_call(db_session):
    uc = UserCreate(
        first_name="A",
        last_name="B",
        email="a@example.com",
        username="user_direct",
        password="ValidPass1!",
        confirm_password="ValidPass1!"
    )

    user = register(uc, db=db_session)
    assert isinstance(user, User)

    # duplicate should raise HTTPException
    with pytest.raises(HTTPException) as excinfo:
        register(uc, db=db_session)
    assert excinfo.value.status_code == 400


def test_login_json_invalid_and_form(db_session):
    # create a user via model helper
    data = {
        "first_name": "L",
        "last_name": "O",
        "email": "login@example.com",
        "username": "loginuser",
        "password": "ValidPass1!"
    }
    # use User.register to ensure hashing
    u = User.register(db_session, data)
    db_session.commit()
    db_session.refresh(u)

    # invalid password
    with pytest.raises(HTTPException):
        login_json(UserLogin(username="loginuser", password="wrongpass"), db=db_session)

    # form login success
    form = OAuth2PasswordRequestForm(username="loginuser", password="ValidPass1!", scope="")
    result = login_form(form_data=form, db=db_session)
    assert "access_token" in result


def test_create_calculation_bad_inputs_raises(monkeypatch, db_session):
    data = {
        "first_name": "C",
        "last_name": "U",
        "email": "calc@example.com",
        "username": "calcuser",
        "password": "ValidPass1!"
    }
    u = User.register(db_session, data)
    db_session.commit()
    db_session.refresh(u)

    def fake_create(*args, **kwargs):
        raise ValueError("bad calculation")

    monkeypatch.setattr("app.main.Calculation.create", fake_create)
    calc = CalculationBase(type="addition", inputs=[1, 2])
    with pytest.raises(HTTPException) as excinfo:
        create_calculation(calc, current_user=u, db=db_session)
    assert excinfo.value.status_code == 400
