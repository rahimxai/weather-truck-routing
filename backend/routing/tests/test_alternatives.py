import pytest

from routing.domain.alternatives import detour_points, same_corridor
from routing.domain.geometry import haversine_mi

from .fakes import line

CHICAGO, DENVER = (-87.63, 41.88), (-104.99, 39.74)


def test_detours_sit_either_side_of_midpoint():
    vias = detour_points(CHICAGO, DENVER, fractions=(0.2, -0.2))
    mid = ((CHICAGO[0] + DENVER[0]) / 2, (CHICAGO[1] + DENVER[1]) / 2)
    straight = haversine_mi(CHICAGO, DENVER)
    for via in vias:
        assert haversine_mi(via, mid) == pytest.approx(0.2 * straight, rel=0.05)
    lats = sorted(lat for _, lat in vias)
    assert lats[0] < mid[1] < lats[1]  # one north, one south of an east-west trip


def test_detour_is_equidistant_from_both_ends():
    (via,) = detour_points(CHICAGO, DENVER, fractions=(0.3,))
    assert haversine_mi(via, CHICAGO) == pytest.approx(haversine_mi(via, DENVER), rel=0.02)


def test_no_detours_for_same_point():
    assert detour_points(CHICAGO, CHICAGO) == []


def test_same_line_is_same_corridor():
    pts = line(CHICAGO, DENVER, 200)
    assert same_corridor(pts, pts)


def test_tiny_shift_is_same_corridor():
    a = line(CHICAGO, DENVER, 200)
    b = [(x + 0.003, y) for x, y in a]
    assert same_corridor(a, b)


def test_parallel_route_is_different():
    a = line(CHICAGO, DENVER, 200)
    b = [(x, y + 1.0) for x, y in a]
    assert not same_corridor(a, b)
