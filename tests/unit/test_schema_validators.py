# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest

from app.schemas.user import UserCreate
from app.schemas.calculation import CalculationBase


def test_usercreate_password_strength_checks():
    bad = {
        "first_name": "A",
        "last_name": "B",
        "email": "a@b.com",
        "username": "user123",
        "password": "alllower1!",
        "confirm_password": "alllower1!",
    }
    with pytest.raises(Exception):
        UserCreate(**bad)


def test_calculationbase_validators():
    # invalid type
    with pytest.raises(Exception):
        CalculationBase(type="unknown", inputs=[1, 2])

    # inputs not list
    with pytest.raises(Exception):
        CalculationBase(type="addition", inputs="notalist")

    # power requires exactly two
    with pytest.raises(Exception):
        CalculationBase(type="power", inputs=[1, 2, 3])
