# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import pytest
from app.models.calculation import Calculation


def test_calculation_get_result_basic_operations():
    c = Calculation.create(calculation_type="addition", user_id=None, inputs=[1, 2, 3])
    assert c.get_result() == 6

    c = Calculation.create(calculation_type="multiplication", user_id=None, inputs=[2, 3, 4])
    assert c.get_result() == 24

    c = Calculation.create(calculation_type="subtraction", user_id=None, inputs=[10, 3, 2])
    assert c.get_result() == 5


def test_calculation_division_by_zero_raises():
    with pytest.raises(ValueError):
        c = Calculation.create(calculation_type="division", user_id=None, inputs=[10, 0])
        c.get_result()


def test_calculation_power_requirements():
    # correct
    c = Calculation.create(calculation_type="power", user_id=None, inputs=[2, 3])
    assert c.get_result() == 8
    # wrong inputs count
    with pytest.raises(ValueError):
        c = Calculation.create(calculation_type="power", user_id=None, inputs=[2, 3, 4])
        c.get_result()
