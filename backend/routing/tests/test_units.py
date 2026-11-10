import pytest

from routing.domain.units import kg_to_lb, lb_to_kg, m_to_mi, mi_to_m


def test_lb_to_kg_exact():
    assert lb_to_kg(1) == 0.45359237


def test_max_load_in_kg():
    assert lb_to_kg(80_000) == pytest.approx(36_287.39, abs=0.01)


def test_lb_kg_round_trip():
    assert kg_to_lb(lb_to_kg(42_000)) == pytest.approx(42_000)


def test_mile_in_metres():
    assert m_to_mi(1609.344) == 1
    assert mi_to_m(25) == pytest.approx(40_233.6)
