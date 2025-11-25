# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
from uuid import uuid4

import pytest

from app.auth import jwt as auth_jwt
from app.models.user import User


def test_get_current_user_success(db_session):
    data = {
        "first_name": "T",
        "last_name": "U",
        "email": f"u{uuid4()}@ex.com",
        "username": f"u{uuid4()}",
        "password": "ValidPass1!"
    }
    user = User(**data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = auth_jwt.create_token(str(user.id), auth_jwt.TokenType.ACCESS)
    got = asyncio.run(auth_jwt.get_current_user(token=token, db=db_session))
    assert isinstance(got, User)


def test_get_current_user_inactive(db_session):
    data = {
        "first_name": "I",
        "last_name": "N",
        "email": f"u{uuid4()}@ex.com",
        "username": f"u{uuid4()}",
        "password": "ValidPass1!"
    }
    user = User(**data)
    user.is_active = False
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = auth_jwt.create_token(str(user.id), auth_jwt.TokenType.ACCESS)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(auth_jwt.get_current_user(token=token, db=db_session))
    # should be HTTPException for inactive user
    assert "Inactive" in str(excinfo.value) or "Inactive user" in str(excinfo.value)
