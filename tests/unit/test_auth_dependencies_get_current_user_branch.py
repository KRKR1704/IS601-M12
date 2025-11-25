# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest
from fastapi import HTTPException

from app.auth import dependencies
from app.models import user as user_module


def test_get_current_user_unsupported_type(monkeypatch):
    """If User.verify_token returns an unsupported type, get_current_user
    should raise the credentials HTTPException (the `else` branch at line 65).
    """
    monkeypatch.setattr(user_module.User, "verify_token", staticmethod(lambda token: 123))
    with pytest.raises(HTTPException) as excinfo:
        dependencies.get_current_user(token="dummy")

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Could not validate credentials"
