import base64
import math
from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from routing.domain.alternatives import detour_points
from routing.domain.risk import classify
from routing.domain.scenarios import ramp, scenario_weather, winter_storm

from .fakes import line, tt_route

CHI, DEN = (-87.63, 41.88), (-104.99, 39.74)
DEPART = datetime(2026, 11, 12, 14, tzinfo=UTC)
MID = ((CHI[0] + DEN[0]) / 2, (CHI[1] + DEN[1]) / 2)


def at(fraction_along, fraction_off=0.0):
    """A point a given fraction of the trip along and off the straight line from the middle."""
    dx, dy = DEN[0] - CHI[0], DEN[1] - CHI[1]
    # Perpendicular in the same squashed frame the storm uses is close enough for these checks.
    return (
        MID[0] + dx * fraction_along - dy * fraction_off * 1.3,
        MID[1] + dy * fraction_along + dx * fraction_off * 0.75,
    )


def wx(pt, hours=10):
    return winter_storm(CHI, DEN, DEPART)(*pt, DEPART + timedelta(hours=hours))


@pytest.mark.parametrize(
    "x, inner, outer, out",
    [(0, 1, 2, 1), (1, 1, 2, 1), (1.5, 1, 2, 0.5), (-1.5, 1, 2, 0.5), (3, 1, 2, 0)],
)  # fmt: skip
def test_ramp(x, inner, outer, out):
    assert ramp(x, inner, outer) == out


def test_core_is_severe_wind():
    assert wx(MID).wind_mph == pytest.approx(48)


def test_line_is_high_wind():
    assert wx(at(0.06)).wind_mph == pytest.approx(41)


def test_snow_bands_either_side():
    assert wx(at(0.15, 0.25)).snow_in_hr == pytest.approx(1.4)
    assert wx(at(0.15, -0.25)).snow_in_hr == pytest.approx(1.4)
    assert wx(at(0.0, 0.25)).snow_in_hr == pytest.approx(2.3)


def test_calm_away_from_storm():
    w = wx(at(0.45, 0.0))
    assert (w.wind_mph, w.snow_in_hr) == (10, 0)
    assert wx(at(0.0, 0.6)).snow_in_hr == 0


def test_storm_builds_then_fades():
    assert wx(MID, hours=0).wind_mph == pytest.approx(10 + 38 / 3)
    assert wx(MID, hours=40).wind_mph == pytest.approx(10 + 38 / 2)
    assert wx(MID, hours=48).wind_mph == 10


def test_load_rules_show_in_the_storm():
    core, line_ = wx(MID), wx(at(0.06))
    assert classify(core, 25_000).level.name == "SEVERE"
    assert classify(core, 45_000).level.name == "NO_TRAVEL"
    assert classify(line_, 25_000).level.name == "HIGH"
    assert classify(line_, 45_000).level.name == "SEVERE"


def test_unknown_scenario():
    with pytest.raises(ValueError):
        scenario_weather("heatwave", CHI, DEN, DEPART)


# The demo from the plan: same trip at 25,000 and 45,000 lb, and the pick flips.


def detour_route(via):
    return line(CHI, via, 60) + line(via, DEN, 60)[1:]


@pytest.fixture
def storm_trip(apis):
    a = line(CHI, DEN, 120)
    b, c = (detour_route(v) for v in detour_points(CHI, DEN, fractions=(0.22, -0.22)))
    apis.routes = [tt_route(a, 62), tt_route(b, 58), tt_route(c, 58)]
    return apis


def plan(client, load_lb, scenario="winter_storm"):
    body = {
        "origin": {"lat": CHI[1], "lon": CHI[0]},
        "destination": {"lat": DEN[1], "lon": DEN[0]},
        "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_lb": load_lb,
        "scenario": scenario,
    }
    return client.post("/api/plan", body, content_type="application/json").json()


def route(data, id):
    return next(r for r in data["routes"] if r["id"] == id)


def test_light_load_takes_the_windy_direct_route(client, storm_trip):
    data = plan(client, 25_000)
    assert data["scenario"] == "winter_storm"
    assert data["recommended_id"] == "A"
    a = route(data, "A")["summary"]["miles_by_level"]
    assert a["NO_TRAVEL"] == 0 and a["SEVERE"] > 0


def test_heavy_load_avoids_it(client, storm_trip):
    data = plan(client, 45_000)
    assert data["recommended_id"] != "A"
    a = route(data, "A")["summary"]["miles_by_level"]
    assert a["NO_TRAVEL"] > 0
    assert "No Travel miles" in data["explanation"]


def test_scenario_never_calls_the_forecast(client, storm_trip):
    plan(client, 45_000)
    assert not [c for c in storm_trip.calls if c.url.host == "api.open-meteo.com"]


def test_live_plan_says_so(client, storm_trip):
    data = plan(client, 25_000, scenario=None)
    assert data["scenario"] is None
    assert [c for c in storm_trip.calls if c.url.host == "api.open-meteo.com"]


def test_unknown_scenario_rejected(client, storm_trip):
    resp = client.post(
        "/api/plan",
        {"origin": {"lat": 41, "lon": -87}, "destination": {"lat": 39, "lon": -104},
         "departure": timezone.now().isoformat(), "load_lb": 1, "scenario": "heatwave"},
        content_type="application/json",
    )  # fmt: skip
    assert resp.status_code == 400
    assert resp.json()["error"]["message"].startswith("scenario:")


def test_heatmap_draws_the_same_storm(client, storm_trip):
    data = plan(client, 45_000)
    a = route(data, "A")
    body = {
        "routes": [r["geometry"] for r in data["routes"]],
        "departure": a["departure"],
        "load_lb": 45_000,
        "scenario": "winter_storm",
    }
    heat = client.post("/api/heatmap", body, content_type="application/json").json()
    assert heat["scenario"] == "winter_storm"
    assert not [c for c in storm_trip.calls if c.url.host == "api.open-meteo.com"]

    risk = base64.b64decode(heat["frames"]["risk"])
    n = len(heat["points"])
    start = datetime.fromisoformat(heat["start"])
    # Cells are coarser than the storm's core, so allow one cell of slack: near every
    # No Travel checkpoint on A, at the hour the truck is there, the map shows No Travel too.
    for cp in (cp for cp in a["checkpoints"] if cp["level"] == "NO_TRAVEL"):
        hour = round((datetime.fromisoformat(cp["eta"]) - start).total_seconds() / 3600)
        near = [
            i
            for i, (x, y) in enumerate(heat["points"])
            if abs(x - cp["lon"]) <= heat["cell_deg"] * 1.5
            and abs(y - cp["lat"]) <= heat["cell_deg"] * 1.5
        ]
        levels = [risk[hour * n + i] for i in near]
        assert 4 in levels
        assert min(levels) >= 1  # nothing near the core reads as calm


DAL, MSP = (-96.8, 32.78), (-93.27, 44.98)  # a mostly north-south trip


def trip_point(origin, dest, along, off):
    """A point at fractions of the trip along it and to its left, laid out in km."""
    (lon1, lat1), (lon2, lat2) = origin, dest
    mid_lon, mid_lat = (lon1 + lon2) / 2, (lat1 + lat2) / 2
    k = math.cos(math.radians(mid_lat)) * 111.32
    dx, dy = (lon2 - lon1) * k, (lat2 - lat1) * 111.32
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    x, y = (along * ux - off * uy) * length, (along * uy + off * ux) * length
    return mid_lon + x / k, mid_lat + y / 111.32


@pytest.mark.parametrize("off", [0.33, -0.33])
def test_snow_bands_follow_any_trip_direction(off):
    storm = winter_storm(DAL, MSP, DEPART)
    w = storm(*trip_point(DAL, MSP, 0.15, off), DEPART + timedelta(hours=10))
    assert w.snow_in_hr == pytest.approx(1.4)


def test_wind_follows_any_trip_direction():
    storm = winter_storm(DAL, MSP, DEPART)
    w = storm(*trip_point(DAL, MSP, 0.06, 0.05), DEPART + timedelta(hours=10))
    assert w.wind_mph == pytest.approx(41)
