from datetime import UTC, datetime, timedelta, timezone
from itertools import pairwise

import pytest

from routing.domain.checkpoints import build_checkpoints, checkpoint_miles, coverage, eta_seconds
from routing.domain.geometry import cumulative_miles
from routing.domain.models import Route

DEPART = datetime(2026, 11, 12, 14, 0, tzinfo=UTC)


def straight_route(degrees=2.0, hours=2.0, distance_mi=None):
    pts = [(0.0, i / 10) for i in range(int(degrees * 10) + 1)]
    length = cumulative_miles(pts)[-1]
    dist = distance_mi or length
    secs = hours * 3600
    return Route("A", pts, dist, secs, profile=[(0.0, 0.0), (dist, secs)])


@pytest.mark.parametrize(
    "total, interval, expected",
    [
        (100, 25, [0, 25, 50, 75, 100]),
        (110, 25, [0, 25, 50, 75, 100, 110]),
        (10, 25, [0, 10]),
        (50, 50, [0, 50]),
        (0, 25, [0]),
        (75.0000000001, 25, [0, 25, 50, 75]),
    ],
)
def test_checkpoint_miles(total, interval, expected):
    assert checkpoint_miles(total, interval) == pytest.approx(expected)


def test_long_route_does_not_drift():
    miles = checkpoint_miles(1003.4, 10)
    assert len(miles) == 102
    assert miles[-2] == 1000
    assert miles[-1] == 1003.4


@pytest.mark.parametrize(
    "miles, expected",
    [
        ([0, 25, 50, 75, 100], [12.5, 25, 25, 25, 12.5]),
        ([0, 25, 50, 60], [12.5, 25, 17.5, 5]),
        ([0, 10], [5, 5]),
        ([0], [0]),
    ],
)
def test_coverage(miles, expected):
    assert coverage(miles) == pytest.approx(expected)


@pytest.mark.parametrize("interval", [10, 25, 50])
@pytest.mark.parametrize("total", [0.4, 9.99, 25, 137.3, 1003.4, 2789.1])
def test_coverage_sums_to_route_length(total, interval):
    assert sum(coverage(checkpoint_miles(total, interval))) == pytest.approx(total)


PROFILE = [(0, 0), (100, 3600), (200, 9000)]


@pytest.mark.parametrize(
    "mile, secs", [(-1, 0), (0, 0), (50, 1800), (100, 3600), (150, 6300), (200, 9000), (250, 9000)]
)
def test_eta_interpolation(mile, secs):
    assert eta_seconds(PROFILE, mile) == pytest.approx(secs)


def test_eta_with_repeated_profile_mile():
    profile = [(0, 0), (10, 600), (10, 900), (20, 1500)]  # a stop at mile 10
    assert eta_seconds(profile, 15) == pytest.approx(1200)


def test_build_checkpoints_endpoints_and_etas():
    route = straight_route()
    cps = build_checkpoints(route, 25, DEPART)

    expected = [0, 25, 50, 75, 100, 125, round(route.distance_mi, 2)]
    assert [round(cp.mile, 2) for cp in cps] == expected
    assert (cps[0].lon, cps[0].lat) == (0.0, 0.0)
    assert (cps[-1].lon, cps[-1].lat) == pytest.approx((0.0, 2.0))
    assert cps[0].eta == DEPART
    assert cps[-1].eta == DEPART + timedelta(hours=2)
    assert all(a.eta < b.eta for a, b in pairwise(cps))
    assert sum(cp.covered_mi for cp in cps) == pytest.approx(route.distance_mi)


def test_router_distance_is_scaled_onto_geometry():
    route = straight_route(distance_mi=152.0)  # polyline is ~138.2 mi
    cps = build_checkpoints(route, 76, DEPART)
    assert [cp.lat for cp in cps] == pytest.approx([0, 1, 2])


def test_eta_converted_to_utc():
    local = DEPART.astimezone(timezone(timedelta(hours=-6)))
    cps = build_checkpoints(straight_route(), 50, local)
    assert cps[0].eta == DEPART
    assert cps[0].eta.utcoffset() == timedelta(0)


def test_naive_departure_rejected():
    with pytest.raises(ValueError):
        build_checkpoints(straight_route(), 25, datetime(2026, 11, 12, 14, 0))
