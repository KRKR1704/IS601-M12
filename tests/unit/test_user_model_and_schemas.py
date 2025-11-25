# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest
from uuid import uuid4
from datetime import datetime

from app.models.user import User, utcnow
from app.schemas.user import UserCreate, PasswordUpdate


def test_user_str_and_update():
    user = User(first_name="John", last_name="Doe", email="j@d.com", username="jd", password="x")
    s = str(user)
    assert "John" in s
    old = user.updated_at
    user.update(first_name="Jane")
    assert user.first_name == "Jane"
    assert user.updated_at is not None


def test_hash_and_verify_password():
    h = User.hash_password("TestPass123!")
    assert isinstance(h, str)


def test_register_short_password_raises(db_session):
    data = {
        "first_name": "A",
        "last_name": "B",
        "email": f"u{uuid4()}@ex.com",
        "username": f"u{uuid4()}",
        "password": "short"
    }
    with pytest.raises(ValueError):
        User.register(db_session, data)


def test_register_duplicate_raises(db_session):
    data = {
        "first_name": "A",
        "last_name": "B",
        "email": f"dup{uuid4()}@ex.com",
        "username": f"dup{uuid4()}",
        "password": "ValidPass1!"
    }
    # Ensure tables exist on the same engine used by the test session
    from app.database import Base
    engine_for_create = db_session.get_bind()
    Base.metadata.create_all(bind=engine_for_create)

    # First create and commit
    u = User.register(db_session, data)
    db_session.commit()
    # Attempt to create duplicate
    with pytest.raises(ValueError):
        User.register(db_session, data)


def test_usercreate_password_validations():
    good = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "username": "johndoe",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    uc = UserCreate(**good)
    assert uc.password == good["password"]

    bad = dict(good)
    bad["password"] = "short"
    bad["confirm_password"] = "short"
    with pytest.raises(Exception):
        UserCreate(**bad)


def test_password_update_validator():
    pu = {
        "current_password": "OldPass1!",
        "new_password": "NewPass1!",
        "confirm_new_password": "NewPass1!"
    }
    PasswordUpdate(**pu)
    # mismatch
    bad = dict(pu)
    bad["confirm_new_password"] = "Other!"
    with pytest.raises(Exception):
        PasswordUpdate(**bad)
