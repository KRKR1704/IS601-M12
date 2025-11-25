# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
import runpy
import sys
import types

from app.auth import jwt as auth_jwt
from app.main import lifespan, app as fastapi_app


def test_run_lifespan_directly():
    # Execute the lifespan context manager to exercise startup code
    async def _run():
        async with lifespan(fastapi_app):
            pass
    asyncio.run(_run())


def test_run_module_as_main_monkeypatched_uvicorn(monkeypatch):
    # Insert a fake uvicorn module so running app.main as __main__ won't start a server
    fake_uvicorn = types.SimpleNamespace(run=lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    # Run the module as __main__; this will execute the guarded uvicorn.run line
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        runpy.run_module("app.main", run_name="__main__")


def test_jwt_helpers_hash_and_verify():
    pw = "StrongPass1!"
    h = auth_jwt.get_password_hash(pw)
    assert auth_jwt.verify_password(pw, h)


def test_create_and_decode_refresh_token():
    user_id = "test-refresh-id"
    token = auth_jwt.create_token(user_id, auth_jwt.TokenType.REFRESH)
    payload = asyncio.run(auth_jwt.decode_token(token, auth_jwt.TokenType.REFRESH))
    assert payload["sub"] == user_id
