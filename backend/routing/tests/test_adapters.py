from datetime import UTC, datetime

import httpx
import pytest

from routing.adapters import http, open_meteo, tomtom
from routing.adapters.http import backoff, get_json
from routing.errors import ForecastUnavailable, NoRoute, NotConfigured, UpstreamError

from .fakes import line, tt_route

CHICAGO, DENVER = (-87.63, 41.88), (-104.99, 39.74)
DEPART = datetime(2026, 11, 12, 14, tzinfo=UTC)
NORTH = line(CHICAGO, (-88.0, 43.5), 30)
SOUTH = line(CHICAGO, (-91.0, 39.5), 30)
WEST = line(CHICAGO, DENVER, 30)


def routes_of(apis, *lines):
    return [tt_route(pts) for pts in lines]


def test_parse_route_joins_legs_and_builds_profile():
    data = tt_route(WEST, mph=60, legs=2)
    route = tomtom.parse_route(data, "A")
    assert route.geometry[0] == WEST[0] and route.geometry[-1] == WEST[-1]
    assert route.distance_mi == pytest.approx(data["summary"]["lengthInMeters"] / 1609.344)
    assert route.profile[0] == (0, 0)
    assert route.profile[-1] == (route.distance_mi, route.duration_s)


def test_profile_follows_uneven_speed():
    slow, fast = line(CHICAGO, (-96.0, 40.8), 30), line((-96.0, 40.8), DENVER, 30)[1:]
    data = tt_route(slow + fast, mph=60)
    half = len(data["guidance"]["instructions"]) // 2
    # Make the first half take twice as long: shift every later instruction's time.
    first_half_s = data["guidance"]["instructions"][half]["travelTimeInSeconds"]
    for step in data["guidance"]["instructions"][half:]:
        step["travelTimeInSeconds"] += first_half_s
    data["summary"]["travelTimeInSeconds"] += first_half_s
    route = tomtom.parse_route(data)
    mid_mile = data["guidance"]["instructions"][half]["routeOffsetInMeters"] / 1609.344
    assert (mid_mile, 2 * first_half_s) in route.profile


def test_route_request_params(apis):
    apis.routes = routes_of(apis, WEST, NORTH, SOUTH)
    tomtom.truck_routes(CHICAGO, DENVER, DEPART, 42_000)
    q = apis.calls[0].url.params
    assert apis.calls[0].url.path.endswith("/calculateRoute/41.88,-87.63:39.74,-104.99/json")
    assert q["travelMode"] == "truck"
    assert q["vehicleCommercial"] == "true"
    assert q["vehicleWeight"] == "19051"  # 42,000 lb in kg
    assert q["departAt"] == "2026-11-12T14:00:00+00:00"
    assert q["maxAlternatives"] == "2"
    assert q["instructionsType"] == "coded"


def test_three_routes_get_ids(apis):
    apis.routes = routes_of(apis, WEST, NORTH, SOUTH)
    routes = tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)
    assert [r.id for r in routes] == ["A", "B", "C"]
    assert len(apis.calls) == 1  # no detours needed


def test_detours_fill_missing_alternatives(apis):
    apis.routes = routes_of(apis, WEST)
    apis.detour_routes = routes_of(apis, NORTH, SOUTH, NORTH)
    routes = tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)
    assert [r.id for r in routes] == ["A", "B", "C"]
    assert routes[0].geometry[-1] == WEST[-1]


def test_duplicate_detours_are_dropped(apis):
    apis.routes = routes_of(apis, WEST)
    apis.detour_routes = routes_of(apis, WEST, WEST, NORTH, WEST)
    routes = tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)
    assert len(routes) == 2


@pytest.mark.parametrize("status", [400, 500])
def test_failed_detours_are_skipped(apis, status):
    apis.routes = routes_of(apis, WEST, NORTH)
    apis.detour_status = status
    assert len(tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)) == 2


def test_empty_detours_are_skipped(apis):
    apis.routes = routes_of(apis, WEST, NORTH)
    assert len(tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)) == 2


def test_unroutable_is_no_route(apis):
    apis.fail["api.tomtom.com"] = [400]
    with pytest.raises(NoRoute):
        tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)


def test_empty_routes_is_no_route(apis):
    apis.routes = []
    with pytest.raises(NoRoute):
        tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)


def test_bad_key_is_upstream_error_without_key(apis):
    apis.fail["api.tomtom.com"] = [403]
    with pytest.raises(UpstreamError) as e:
        tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)
    assert "test-key-123" not in str(e.value)
    assert e.value.status == 502


def test_rate_limit_is_retried(apis):
    apis.fail["api.tomtom.com"] = [429, 503]
    apis.routes = routes_of(apis, WEST, NORTH, SOUTH)
    assert len(tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)) == 3


def test_rate_limit_that_persists_is_503(apis):
    apis.fail["api.tomtom.com"] = [429, 429, 429]
    with pytest.raises(UpstreamError) as e:
        tomtom.truck_routes(CHICAGO, DENVER, DEPART, 0)
    assert e.value.status == 503


def test_missing_key(apis, settings):
    settings.TOMTOM_API_KEY = ""
    with pytest.raises(NotConfigured):
        tomtom.geocode("denver")


def test_geocode_maps_results_and_encodes_query(apis):
    apis.geocode_results = [
        {"address": {"freeformAddress": "Denver, CO"}, "position": {"lat": 39.74, "lon": -104.99}}
    ]
    assert tomtom.geocode("St. Louis/MO") == [{"label": "Denver, CO", "lat": 39.74, "lon": -104.99}]
    assert apis.calls[0].url.raw_path.startswith(b"/search/2/geocode/St.%20Louis%2FMO.json")
    assert apis.calls[0].url.params["countrySet"] == "US,CA"


def test_timeouts_are_retried():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) < 3:
            raise httpx.ConnectTimeout("slow", request=request)
        return httpx.Response(200, json={"ok": True})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert get_json(client, "X", "https://x.test/a", {"key": "secret"}) == {"ok": True}
    assert len(attempts) == 3


def test_client_errors_are_not_retried():
    attempts = []

    def handler(request):
        attempts.append(1)
        return httpx.Response(404)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(UpstreamError),
    ):
        get_json(client, "X", "https://x.test/a", {"key": "secret"})
    assert len(attempts) == 1


def test_non_json_success_is_upstream_error():
    def handler(request):
        return httpx.Response(200, text="<html>")

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(UpstreamError),
    ):
        get_json(client, "X", "https://x.test/a", {})


def test_forecast_batches_and_params(apis):
    pts = [(-90 + i * 0.1, 40.0) for i in range(120)]
    series = open_meteo.forecasts(pts, DEPART, datetime(2026, 11, 13, 2, 30, tzinfo=UTC))
    assert len(series) == 120
    assert len(apis.calls) == 3  # batches of 50
    q = apis.calls[0].url.params
    assert q["wind_speed_unit"] == "mph"
    assert q["precipitation_unit"] == "inch"
    assert "showers" in q["hourly"]
    assert q["start_hour"] == "2026-11-12T13:00"
    assert q["end_hour"] == "2026-11-13T04:00"


def test_forecast_single_location(apis):
    assert len(open_meteo.forecasts([(-90.0, 40.0)], DEPART, DEPART)) == 1


def test_forecast_out_of_range_is_unavailable(apis):
    apis.fail["api.open-meteo.com"] = [400]
    with pytest.raises(ForecastUnavailable):
        open_meteo.forecasts([(-90.0, 40.0)], DEPART, DEPART)


def test_forecast_no_points(apis):
    assert open_meteo.forecasts([], DEPART, DEPART) == []
    assert apis.calls == []


def test_forecast_server_error(apis):
    apis.fail["api.open-meteo.com"] = [500, 500, 500]
    with pytest.raises(UpstreamError):
        open_meteo.forecasts([(-90.0, 40.0)], DEPART, DEPART)


def test_forecast_wrong_location_count(apis, monkeypatch):
    monkeypatch.setattr(apis, "open_meteo", lambda req: httpx.Response(200, json=[]))
    with pytest.raises(UpstreamError):
        open_meteo.forecasts([(-90.0, 40.0), (-91.0, 40.0)], DEPART, DEPART)


def test_forecast_unexpected_unit(apis, monkeypatch):
    real = apis.open_meteo

    def odd_units(request):
        resp = real(request)
        data = resp.json()
        data["hourly_units"]["snowfall"] = "ft"
        return httpx.Response(200, json=data)

    monkeypatch.setattr(apis, "open_meteo", odd_units)
    with pytest.raises(UpstreamError):
        open_meteo.forecasts([(-90.0, 40.0)], DEPART, DEPART)


def test_backoff_429_uses_retry_after():
    assert backoff(1, 429, "3") == 3.0


def test_backoff_429_retry_after_is_capped():
    assert backoff(1, 429, "120") == http.MAX_WAIT_S


def test_backoff_429_without_header_grows():
    assert [backoff(i, 429) for i in (1, 2, 3)] == [2.0, 4.0, 5.0]


def test_backoff_429_with_date_header_falls_back():
    assert backoff(1, 429, "Wed, 21 Oct 2026 07:28:00 GMT") == 2.0


def test_backoff_5xx_is_short():
    assert [backoff(i, 503) for i in (1, 2)] == [0.5, 1.0]


def test_open_meteo_rate_limit_waits_then_succeeds(apis, monkeypatch):
    waits = []
    monkeypatch.setattr(http.time, "sleep", waits.append)
    apis.fail["api.open-meteo.com"] = [429]
    assert len(open_meteo.forecasts([(-90.0, 40.0)], DEPART, DEPART)) == 1
    assert waits == [2.0]
