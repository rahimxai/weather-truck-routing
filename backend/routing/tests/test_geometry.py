import pytest

from routing.domain.geometry import cumulative_miles, haversine_mi, point_at_mile

LINE = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]  # due north along the prime meridian


def test_one_degree_of_latitude():
    assert haversine_mi((0, 0), (0, 1)) == pytest.approx(69.09, abs=0.01)


def test_chicago_to_denver():
    assert haversine_mi((-87.63, 41.88), (-104.99, 39.74)) == pytest.approx(920, abs=5)


def test_same_point_is_zero():
    assert haversine_mi((-87.6, 41.9), (-87.6, 41.9)) == 0


def test_cumulative_miles():
    assert cumulative_miles(LINE) == pytest.approx([0, 69.09, 138.19], abs=0.01)


def test_cumulative_single_point():
    assert cumulative_miles([(1.0, 2.0)]) == [0.0]


@pytest.mark.parametrize(
    "mile, expected",
    [(-5, (0, 0)), (0, (0, 0)), (34.547, (0, 0.5)), (69.093, (0, 1)), (500, (0, 2))],
)
def test_point_at_mile(mile, expected):
    pt = point_at_mile(LINE, cumulative_miles(LINE), mile)
    assert pt == pytest.approx(expected, abs=1e-3)


def test_point_at_mile_skips_duplicate_vertices():
    pts = [(0.0, 0.0), (0.0, 0.0), (0.0, 1.0)]
    assert point_at_mile(pts, cumulative_miles(pts), 34.547) == pytest.approx((0, 0.5), abs=1e-3)
