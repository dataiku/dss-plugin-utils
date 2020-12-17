import pytest
import numpy as np
from utils.dku_config.custom_check import CustomCheck, CustomCheckError


def test_exists():
    custom_check = CustomCheck(
        type='exists'
    )
    assert custom_check.run('test') is None
    assert custom_check.run('') is None
    assert custom_check.run([]) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(None)


def test_in():
    custom_check = CustomCheck(
        type='in',
        op=[1, 2, 3]
    )
    assert custom_check.run(1) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(4)


def test_not_in():
    custom_check = CustomCheck(
        type='not_in',
        op=[1, 2, 3]
    )
    assert custom_check.run(4) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(1)


def test_sup():
    custom_check = CustomCheck(
        type='sup',
        op=5
    )
    assert custom_check.run(7) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(3)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(-2)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(-np.Inf)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(5)


def test_inf():
    custom_check = CustomCheck(
        type='inf',
        op=5
    )
    assert custom_check.run(2) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(8)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(np.Inf)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(5)


def test_sup_eq():
    custom_check = CustomCheck(
        type='sup_eq',
        op=5
    )
    assert custom_check.run(7) is None
    assert custom_check.run(5) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(3)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(-2)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(-np.Inf)


def test_inf_eq():
    custom_check = CustomCheck(
        type='inf_eq',
        op=5
    )
    assert custom_check.run(2) is None
    assert custom_check.run(5) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(8)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(np.Inf)


def test_between():
    custom_check = CustomCheck(
        type='between',
        op=(3, 8)
    )
    assert custom_check.run(3) is None
    assert custom_check.run(5) is None
    assert custom_check.run(8) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(1)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(20)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(-np.Inf)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(np.Inf)


def test_between_strict():
    custom_check = CustomCheck(
        type='between_strict',
        op=(3, 8)
    )
    assert custom_check.run(5) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(1)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(20)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(3)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(8)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(-np.Inf)
    with pytest.raises(CustomCheckError):
        _ = custom_check.run(np.Inf)


def test_is_type():
    custom_check_list = CustomCheck(
        type='is_type',
        op=list
    )
    assert custom_check_list.run([1, 2, 3, 4]) is None
    assert custom_check_list.run([]) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check_list.run(None)
    with pytest.raises(CustomCheckError):
        _ = custom_check_list.run("test")
    with pytest.raises(CustomCheckError):
        _ = custom_check_list.run({1, 2, 3})

    custom_check_float = CustomCheck(
        type='is_type',
        op=float
    )
    assert custom_check_float.run(3.4) is None
    with pytest.raises(CustomCheckError):
        _ = custom_check_float.run("test")
    with pytest.raises(CustomCheckError):
        _ = custom_check_float.run(None)
    with pytest.raises(CustomCheckError):
        _ = custom_check_float.run(0)
    with pytest.raises(CustomCheckError):
        _ = custom_check_float.run(4)


def test_custom():
    assert CustomCheck(type='custom', cond=1 == 1).run() is None
    assert CustomCheck(type='custom', cond=len([1, 2, 3, 4]) == 4).run() is None
    with pytest.raises(CustomCheckError):
        CustomCheck(type='custom', cond=3 == 4).run()