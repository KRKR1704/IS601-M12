# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest
from app.schemas.user import UserCreate


def test_user_password_requires_uppercase():
    bad = {
        "first_name": "A",
        "last_name": "B",
        "email": "a@b.com",
        "username": "userx",
        "password": "lowercase1!",
        "confirm_password": "lowercase1!",
    }
    with pytest.raises(Exception):
        UserCreate(**bad)


def test_user_password_requires_digit():
    bad = {
        "first_name": "A",
        "last_name": "B",
        "email": "a@b.com",
        "username": "userx",
        "password": "NoDigits!",
        "confirm_password": "NoDigits!",
    }
    with pytest.raises(Exception):
        UserCreate(**bad)


def test_user_password_requires_special_char():
    bad = {
        "first_name": "A",
        "last_name": "B",
        "email": "a@b.com",
        "username": "userx",
        "password": "NoSpecial1",
        "confirm_password": "NoSpecial1",
    }
    with pytest.raises(Exception):
        UserCreate(**bad)


def test_user_password_too_short():
    bad = {
        "first_name": "A",
        "last_name": "B",
        "email": "a@b.com",
        "username": "userx",
        "password": "S1!a",
        "confirm_password": "S1!a",
    }
    with pytest.raises(Exception):
        UserCreate(**bad)
