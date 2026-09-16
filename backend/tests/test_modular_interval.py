"""Unit tests for the explicit modular interval primitives."""

import pytest

from app.verifier import modular_interval_has_point, smallest_positive_residue


@pytest.mark.parametrize(
    "d, modulus, expected",
    [
        (0, 3, 3),
        (1, 3, 1),
        (2, 3, 2),
        (3, 3, 3),
        (4, 3, 1),
        (-1, 3, 2),
        (-3, 3, 3),
        (10**12 + 1, 7, (10**12 + 1) % 7),
    ],
)
def test_smallest_positive_residue(d, modulus, expected):
    assert smallest_positive_residue(d, modulus) == expected
    assert 1 <= expected <= modulus
    assert expected % modulus == d % modulus


@pytest.mark.parametrize(
    "d, modulus, upper, expected",
    [
        (0, 3, 2, False),   # first positive is 3, outside [1,2]
        (0, 3, 3, True),
        (1, 3, 1, True),
        (2, 3, 1, False),
        (2, 3, 2, True),
        (-1, 5, 3, False),  # residue 4 > 3
        (-1, 5, 4, True),
        (0, 60, 10**12, True),
        (59, 60, 0, False),
    ],
)
def test_modular_interval_has_point(d, modulus, upper, expected):
    assert modular_interval_has_point(d, modulus, upper) is expected
