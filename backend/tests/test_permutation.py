import pytest

from app.permutation import (
    apply_row,
    compose,
    cycles,
    identity,
    inverse,
    order,
    power,
    product,
)


def test_identity_and_apply_step_convention():
    p = (1, 0, 2, 3)
    old = (0, 1, 2, 3)
    assert apply_row(old, p) == (1, 0, 2, 3)
    assert apply_row((1, 0, 2, 3), p) == (0, 1, 2, 3)


def test_compose_apply_second_first():
    # new[i] = old[p[i]]: applying q first, then p, equals compose(q, p).
    p = (1, 0, 2, 3)
    q = (1, 2, 0, 3)
    row = (3, 2, 1, 0)
    assert apply_row(apply_row(row, q), p) == apply_row(row, compose(q, p))


def test_inverse_roundtrip():
    p = (2, 0, 3, 1)
    pinv = inverse(p)
    assert compose(p, pinv) == identity(4)
    assert compose(pinv, p) == identity(4)


def test_power_matches_repeated_compose():
    p = (1, 2, 0, 4, 3)
    acc = identity(5)
    for k in range(1, 8):
        acc = compose(acc, p)
        assert power(p, k) == acc
    assert power(p, 0) == identity(5)
    assert order(p) == 6
    assert power(p, order(p)) == identity(5)
    assert power(p, -1) == inverse(p)
    assert power(p, 10**12 + 7) == power(p, (10**12 + 7) % order(p))


def test_power_huge_exponent_is_exact():
    p = (1, 0, 2, 3)
    assert power(p, 10**12) == identity(4)
    assert power(p, 10**12 + 1) == p


def test_cycles_and_order():
    assert cycles((1, 0, 3, 2)) == [(0, 1), (2, 3)]
    assert order((1, 0, 3, 2)) == 2
    assert order(identity(4)) == 1


def test_product_order():
    p = (1, 0, 2, 3)
    assert product([p, p]) == identity(4)
    assert product([p, p, p]) == p
    with pytest.raises(ValueError):
        product([])
    with pytest.raises(ValueError):
        compose((0, 1), (0, 1, 2))
