# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from jose import jwt as jose_jwt
from fastapi import HTTPException

from app.models import calculation as calc_models
from app.models.user import User
from app.core.config import settings
from app.auth import jwt as jwt_module
from app.schemas.calculation import CalculationUpdate
from app.schemas.user import UserCreate, PasswordUpdate


def test_calculation_base_not_implemented_and_repr():
    c = calc_models.Calculation(user_id=uuid.uuid4(), inputs=[1, 2])
    with pytest.raises(NotImplementedError):
        c.get_result()
    r = repr(c)
    assert "Calculation" in r


def test_all_operations_success_cases():
    a = calc_models.Addition(user_id=uuid.uuid4(), inputs=[1, 2, 3])
    assert a.get_result() == 6

    s = calc_models.Subtraction(user_id=uuid.uuid4(), inputs=[10, 3, 2])
    assert s.get_result() == 5

    m = calc_models.Multiplication(user_id=uuid.uuid4(), inputs=[2, 3, 4])
    assert m.get_result() == 24

    d = calc_models.Division(user_id=uuid.uuid4(), inputs=[100, 2, 5])
    assert d.get_result() == 10


def test_user_verify_token_valid_uuid():
    uid = uuid.uuid4()
    payload = {"sub": str(uid)}
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    res = User.verify_token(token)
    assert isinstance(res, uuid.UUID)


def test_calculation_update_validator():
    with pytest.raises(ValueError):
        CalculationUpdate(inputs=[1])


def test_user_create_missing_lowercase():
    with pytest.raises(ValueError):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='u', password='NOLOWER1!', confirm_password='NOLOWER1!')


def test_get_current_user_decode_exception_branch(monkeypatch):
    async def _raise(*args, **kwargs):
        raise HTTPException(status_code=401, detail="bad token")

    monkeypatch.setattr(jwt_module, 'decode_token', _raise)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(jwt_module.get_current_user(token='t', db=None))
    assert 'bad token' in str(exc.value)


def test_get_current_user_user_not_found_and_inactive(monkeypatch):
    # decode_token returns payload with sub; db.query returns None -> 404
    async def _ok(token, token_type, verify_exp=True):
        return {"sub": str(uuid.uuid4())}

    monkeypatch.setattr(jwt_module, 'decode_token', _ok)

    class DummyDB:
        def query(self, model):
            class Q:
                def filter(self, *a, **k):
                    class F:
                        def first(self):
                            return None
                    return F()
            return Q()

    with pytest.raises(HTTPException) as exc1:
        asyncio.run(jwt_module.get_current_user(token='t', db=DummyDB()))
    assert 'User not found' in str(exc1.value)

    # Now return an inactive user to hit the inactive branch
    class InactiveUser:
        is_active = False

    class DummyDB2:
        def query(self, model):
            class Q:
                def filter(self, *a, **k):
                    class F:
                        def first(self):
                            return InactiveUser()
                    return F()
            return Q()

    with pytest.raises(HTTPException) as exc2:
        asyncio.run(jwt_module.get_current_user(token='t', db=DummyDB2()))
    assert 'Inactive user' in str(exc2.value)


def test_calculation_subclass_not_list_and_power_error():
    # Not-a-list for several subclasses
    for cls in (calc_models.Addition, calc_models.Subtraction, calc_models.Multiplication, calc_models.Division):
        inst = cls(user_id=uuid.uuid4(), inputs='no')
        with pytest.raises(ValueError):
            inst.get_result()

    # Power computation error when exponent invalid
    p = calc_models.Power(user_id=uuid.uuid4(), inputs=[2, 'x'])
    with pytest.raises(ValueError) as exc:
        p.get_result()
    assert 'Error computing power' in str(exc.value)


def test_user_init_with_hashed_password_and_verify_token_variants():
    u = User(first_name='A', last_name='B', email='e@e.com', username='u', hashed_password='hsh')
    assert u.password == 'hsh'

    # token with no sub
    token_no_sub = jose_jwt.encode({}, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    assert User.verify_token(token_no_sub) is None

    # token with non-uuid sub
    token_bad_sub = jose_jwt.encode({"sub": "not-a-uuid"}, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    assert User.verify_token(token_bad_sub) is None


def test_multiplication_len_and_power_not_list():
    # Multiplication with single input
    inst = calc_models.Multiplication(user_id=uuid.uuid4(), inputs=[2])
    with pytest.raises(ValueError):
        inst.get_result()

    # Power with non-list inputs
    p2 = calc_models.Power(user_id=uuid.uuid4(), inputs='no')
    with pytest.raises(ValueError):
        p2.get_result()


def test_user_hashed_password_property():
    u = User(first_name='A', last_name='B', email='e@e.com', username='u', password='plain')
    assert u.hashed_password == 'plain'


def test_calculation_schema_additional_validators():
    from app.schemas.calculation import CalculationBase, CalculationUpdate
    with pytest.raises(ValueError):
        CalculationBase(type='addition', inputs=[1])
    with pytest.raises(ValueError):
        CalculationBase(type='division', inputs=[10, 0])
    with pytest.raises(ValueError):
        CalculationUpdate(inputs=[1])


def test_user_schema_more_password_errors():
    # mismatch
    with pytest.raises(ValueError):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='u', password='Aa1!aaaa', confirm_password='diff')
    # too short
    with pytest.raises(ValueError):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='u', password='Aa1!', confirm_password='Aa1!')
    # missing lowercase
    with pytest.raises(ValueError):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='u', password='NOLOWER1!', confirm_password='NOLOWER1!')
    # password update same as current
    with pytest.raises(ValueError):
        PasswordUpdate(current_password='Old1!x', new_password='Old1!x', confirm_new_password='Old1!x')


def test_get_current_user_invalid_uuid_in_token(monkeypatch):
    async def _ok(token, token_type, verify_exp=True):
        return {"sub": "not-a-uuid"}

    monkeypatch.setattr(jwt_module, 'decode_token', _ok)

    class DummyDB:
        def query(self, model):
            class Q:
                def filter(self, *a, **k):
                    class F:
                        def first(self):
                            return None
                    return F()
            return Q()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(jwt_module.get_current_user(token='t', db=DummyDB()))
    # The inner UUID conversion failed but code continued and then reported user not found
    assert 'User not found' in str(exc.value)


def test_get_current_user_uuid_sub_branch(monkeypatch):
    # decode_token returns a UUID object (not a string) to hit the 'else' branch
    async def _ok(token, token_type, verify_exp=True):
        return {"sub": uuid.uuid4()}

    monkeypatch.setattr(jwt_module, 'decode_token', _ok)

    class DummyDB:
        def query(self, model):
            class Q:
                def filter(self, *a, **k):
                    class F:
                        def first(self):
                            return None
                    return F()
            return Q()

    with pytest.raises(HTTPException):
        asyncio.run(jwt_module.get_current_user(token='t', db=DummyDB()))


def test_calculation_schema_cover_lines():
    from app.schemas.calculation import CalculationBase, CalculationUpdate
    # Field-level validation may raise a pydantic ValidationError; we only
    # need to ensure invalid inputs are rejected.
    with pytest.raises(Exception):
        CalculationBase(type='addition', inputs=[1])
    with pytest.raises(Exception):
        CalculationBase(type='division', inputs=[1, 0])
    with pytest.raises(Exception):
        CalculationUpdate(inputs=[1])


def test_user_schema_cover_lines():
    # Provide valid base fields to exercise password validators
    with pytest.raises(Exception):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='johndoe', password='Aa1!aaaa', confirm_password='diff')

    with pytest.raises(Exception):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='johndoe', password='Aa1!a', confirm_password='Aa1!a')

    with pytest.raises(Exception):
        UserCreate(first_name='A', last_name='B', email='x@x.com', username='johndoe', password='NOLOWER1!', confirm_password='NOLOWER1!')

    with pytest.raises(Exception):
        PasswordUpdate(current_password='Old1!x', new_password='Old1!x', confirm_new_password='Old1!x')


def test_manual_call_model_validators():
    from app.schemas.calculation import CalculationBase, CalculationUpdate
    # Construct without validation and call the model-level validators directly
    cb = CalculationBase.model_construct(type='addition', inputs=[1])
    with pytest.raises(ValueError):
        cb.validate_inputs()

    cu = CalculationUpdate.model_construct(inputs=[1])
    with pytest.raises(ValueError):
        cu.validate_inputs()

    from app.schemas.user import UserCreate, PasswordUpdate
    uc = UserCreate.model_construct(first_name='A', last_name='B', email='x@x.com', username='johndoe', password='Aa1!aaaa', confirm_password='diff')
    with pytest.raises(ValueError):
        uc.verify_password_match()

    uc2 = UserCreate.model_construct(first_name='A', last_name='B', email='x@x.com', username='johndoe', password='short', confirm_password='short')
    with pytest.raises(ValueError):
        uc2.validate_password_strength()

    pu = PasswordUpdate.model_construct(current_password='Old1!x', new_password='New1!x', confirm_new_password='Other!')
    with pytest.raises(ValueError):
        pu.verify_passwords()

    pu2 = PasswordUpdate.model_construct(current_password='Same1!x', new_password='Same1!x', confirm_new_password='Same1!x')
    with pytest.raises(ValueError):
        pu2.verify_passwords()
