import logging
from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from .fakes import line, tt_route

CHI, DEN = (-87.63, 41.88), (-104.99, 39.74)
DIRECT = line(CHI, DEN, 120)
NORTHERN = line(CHI, (-96.0, 44.5), 60) + line((-96.0, 44.5), DEN, 60)[1:]
SOUTHERN = line(CHI, (-96.0, 37.5), 60) + line((-96.0, 37.5), DEN, 60)[1:]


def soon(hours=2):
    return (timezone.now() + timedelta(hours=hours)).replace(microsecond=0)


def body(**over):
    data = {
        "origin": {"lat": CHI[1], "lon": CHI[0], "label": "Chicago, IL"},
        "destination": {"lat": DEN[1], "lon": DEN[0], "label": "Denver, CO"},
        "departure": soon().isoformat(),
        "load_lb": 42_000,
        "interval_mi": 25,
    }
    return data | over


def post(client, data):
    return client.post("/api/plan", data, content_type="application/json")


@pytest.fixture
def three(apis):
    apis.routes = [tt_route(DIRECT), tt_route(NORTHERN), tt_route(SOUTHERN)]
    return apis


def storm_on_direct(mph):
    def weather(lon, lat, t):
        # Only touches the direct line, which crosses ~41 N around Nebraska.
        hit = -99 < lon < -95 and 40.4 < lat < 41.2
        return {"wind": mph if hit else 8.0, "gust": 0.0, "rain": 0.0, "showers": 0.0, "snow": 0.0}

    return weather


def test_plan_calm_weather_picks_fastest(client, three):
    resp = post(client, body())
    assert resp.status_code == 200
    data = resp.json()
    assert [r["id"] for r in data["routes"]] == ["A", "B", "C"]
    assert data["recommended_id"] == "A"
    assert data["explanation"].startswith("Route A: same risk as Route")
    assert data["warnings"] == []
    a = data["routes"][0]
    assert a["rank"] == 1
    assert a["summary"]["miles_by_level"]["LOW"] == a["distance_mi"]
    assert {s["level"] for s in a["segments"]} == {"LOW"}


def test_checkpoints_follow_interval(client, three):
    a25 = post(client, body(interval_mi=25)).json()["routes"][0]
    a50 = post(client, body(interval_mi=50)).json()["routes"][0]
    miles = [cp["mile"] for cp in a25["checkpoints"]]
    assert miles[:3] == [0, 25, 50]
    assert miles[-1] == a25["distance_mi"]
    assert len(a50["checkpoints"]) < len(a25["checkpoints"])
    assert sum(cp["covered_mi"] for cp in a25["checkpoints"]) == pytest.approx(
        a25["distance_mi"], abs=0.1
    )


def test_checkpoint_shape(client, three):
    cp = post(client, body()).json()["routes"][0]["checkpoints"][1]
    assert set(cp) == {
        "mile",
        "lat",
        "lon",
        "eta",
        "covered_mi",
        "road",
        "weather",
        "level",
        "reason",
        "levels",
    }
    assert set(cp["weather"]) == {"wind_mph", "gust_mph", "rain_in_hr", "snow_in_hr"}
    assert cp["eta"].endswith("Z")
    assert cp["level"] == "LOW" and cp["reason"] == "Low risk"


def test_arrival_matches_duration(client, three):
    r = post(client, body()).json()["routes"][0]
    dep = datetime.fromisoformat(r["departure"])
    arr = datetime.fromisoformat(r["arrival"])
    assert (arr - dep).total_seconds() == pytest.approx(r["duration_s"], abs=1)


def test_geometry_is_simplified(client, three):
    r = post(client, body()).json()["routes"][0]
    assert len(r["geometry"]) < len(DIRECT)
    assert r["geometry"][0] == [round(CHI[0], 5), round(CHI[1], 5)]


def test_heavy_load_in_wind_avoids_route(client, three):
    three.weather = storm_on_direct(50)
    data = post(client, body(load_lb=35_000)).json()
    a = data["routes"][0]
    assert a["summary"]["miles_by_level"]["NO_TRAVEL"] > 0
    assert data["recommended_id"] != "A"
    ranks = {r["id"]: r["rank"] for r in data["routes"]}
    assert sorted(ranks.values()) == [1, 2, 3]
    assert ranks[data["recommended_id"]] == 1
    assert ranks["A"] == 3
    assert "Route A is" in data["explanation"]
    assert data["explanation"].endswith("No Travel miles.")
    assert "NO_TRAVEL" in {s["level"] for s in a["segments"]}
    hit = next(cp for cp in a["checkpoints"] if cp["level"] == "NO_TRAVEL")
    assert hit["reason"] == "Wind 50.0 mph with 35,000 lb load"


def test_weather_stays_local_to_each_checkpoint(client, three):
    def narrow_storm(lon, lat, t):
        hit = -97.1 <= lon <= -96.9
        return {"wind": 60.0 if hit else 8.0, "gust": 0.0, "rain": 0.0, "showers": 0.0, "snow": 0.0}

    three.weather = narrow_storm
    a = post(client, body(interval_mi=10)).json()["routes"][0]
    blocked = [cp["lon"] for cp in a["checkpoints"] if cp["level"] == "NO_TRAVEL"]
    assert blocked
    assert all(-97.16 < lon < -96.84 for lon in blocked)  # forecast cells are 0.1 degree


def test_light_load_in_same_wind_is_only_severe(client, three):
    three.weather = storm_on_direct(50)
    a = post(client, body(load_lb=20_000)).json()["routes"][0]
    assert a["summary"]["miles_by_level"]["NO_TRAVEL"] == 0
    assert a["summary"]["miles_by_level"]["SEVERE"] > 0


def test_all_routes_blocked_warns(client, three):
    three.weather = lambda lon, lat, t: {
        "wind": 60.0, "gust": 70.0, "rain": 0.0, "showers": 0.0, "snow": 0.0
    }  # fmt: skip
    data = post(client, body()).json()
    assert data["warnings"][0].startswith("Every route crosses No Travel")


def test_single_route_warns(client, apis):
    apis.routes = [tt_route(DIRECT)]
    apis.detour_routes = []
    data = post(client, body()).json()
    assert len(data["routes"]) == 1
    assert "Only 1 distinct route found for this trip." in data["warnings"]
    assert data["explanation"] == "Route A is the only route found."


def test_response_never_contains_key(client, three):
    assert "test-key-123" not in post(client, body()).content.decode()


def test_key_never_logged(client, three, caplog):
    caplog.set_level(logging.DEBUG)
    three.fail["api.tomtom.com"] = [503]  # also exercise the retry and error logging
    post(client, body())
    assert "test-key-123" not in caplog.text
    assert "TomTom 200" in caplog.text  # our own timing lines still show up


def test_departure_with_offset_is_utc(client, three):
    local = soon(3).astimezone(timezone.get_fixed_timezone(-360))
    r = post(client, body(departure=local.isoformat())).json()
    assert r["routes"][0]["departure"] == local.astimezone(UTC).isoformat().replace("+00:00", "Z")


@pytest.mark.parametrize(
    "over, message",
    [
        ({"departure": "2020-01-01T00:00:00Z"}, "departure: Departure is in the past"),
        ({"departure": (timezone.now() - timedelta(minutes=30)).isoformat()}, "departure:"),
        ({"departure": (timezone.now() + timedelta(days=8)).isoformat()}, "departure: Forecasts"),
        ({"destination": {"lat": CHI[1], "lon": CHI[0]}}, "Origin and destination are the same"),
        ({"interval_mi": 30}, "interval_mi:"),
        ({"load_lb": 90_000}, "load_lb:"),
        ({"load_lb": -1}, "load_lb:"),
        ({"origin": {"lat": 95, "lon": 0}}, "origin.lat:"),
        ({"departure": "tomorrow"}, "departure:"),
    ],
)  # fmt: skip
def test_invalid_input(client, three, over, message):
    resp = post(client, body(**over))
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "INVALID_INPUT"
    assert err["message"].startswith(message)


def test_missing_field(client, three):
    data = body()
    del data["load_lb"]
    err = post(client, data).json()["error"]
    assert err["message"] == "load_lb: This field is required."


def test_interval_defaults_to_25(client, three):
    data = body()
    del data["interval_mi"]
    miles = [cp["mile"] for cp in post(client, data).json()["routes"][0]["checkpoints"]]
    assert miles[1] == 25


def test_departure_a_few_minutes_ago_becomes_now(client, three):
    resp = post(client, body(departure=(timezone.now() - timedelta(minutes=3)).isoformat()))
    assert resp.status_code == 200
    dep = datetime.fromisoformat(resp.json()["routes"][0]["departure"])
    assert abs((dep - datetime.now(UTC)).total_seconds()) < 60


def test_bad_json(client, three):
    resp = client.post("/api/plan", "{nope", content_type="application/json")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PARSE_ERROR"


def test_get_not_allowed(client):
    resp = client.get("/api/plan")
    assert resp.status_code == 405
    assert resp.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_no_route(client, apis):
    apis.fail["api.tomtom.com"] = [400]
    resp = post(client, body())
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "NO_ROUTE"


def test_tomtom_down(client, apis):
    apis.fail["api.tomtom.com"] = [500, 500, 500]
    resp = post(client, body())
    assert resp.status_code == 502
    assert (
        resp.json()["error"]["message"] == "Couldn't get data from TomTom. Try again in a minute."
    )


def test_key_not_configured(client, apis, settings):
    settings.TOMTOM_API_KEY = ""
    resp = post(client, body())
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "NOT_CONFIGURED"


def test_forecast_out_of_range(client, three):
    three.fail["api.open-meteo.com"] = [400]
    resp = post(client, body())
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "FORECAST_UNAVAILABLE"


def test_forecast_with_gaps(client, three):
    three.weather = lambda lon, lat, t: {
        "wind": None, "gust": 0.0, "rain": 0.0, "showers": 0.0, "snow": 0.0
    }  # fmt: skip
    assert post(client, body()).json()["error"]["code"] == "FORECAST_UNAVAILABLE"


def test_geocode_short_query(client, apis):
    assert client.get("/api/geocode?q=d").json() == []
    assert apis.calls == []


def test_geocode(client, apis):
    apis.geocode_results = [
        {"address": {"freeformAddress": "Denver, CO"}, "position": {"lat": 39.74, "lon": -104.99}}
    ]
    assert client.get("/api/geocode?q=denv").json() == [
        {"label": "Denver, CO", "lat": 39.74, "lon": -104.99}
    ]


def test_routes_name_their_states(client, apis):
    data = tt_route(DIRECT)
    for i, step in enumerate(data["guidance"]["instructions"]):
        step["stateCode"] = ["IL", "IA", "NE", "CO"][min(3, i // 3)]
    apis.routes = [data, tt_route(NORTHERN), tt_route(SOUTHERN)]
    direct = next(r for r in post(client, body()).json()["routes"] if r["id"] == "A")
    assert direct["states"] == ["Illinois", "Iowa", "Nebraska", "Colorado"]


def test_routes_name_their_highways(client, apis):
    data = tt_route(DIRECT)
    steps = data["guidance"]["instructions"]
    # Like real TomTom guidance: every step on a numbered road carries its number.
    for i, step in enumerate(steps):
        step["roadNumbers"] = ["I-88 W"] if i < 2 else ["I-80 W"]
    apis.routes = [data, tt_route(NORTHERN), tt_route(SOUTHERN)]
    direct = next(r for r in post(client, body()).json()["routes"] if r["id"] == "A")
    assert direct["via"] == ["I-88", "I-80"]
    assert direct["checkpoints"][0]["road"] == "I-88"
    assert direct["checkpoints"][-1]["road"] == "I-80"


def test_missing_road_numbers_leave_via_empty(client, three):
    route = post(client, body()).json()["routes"][0]
    assert route["via"] == []
    assert route["states"] == []
    assert route["checkpoints"][0]["road"] is None
