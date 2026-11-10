import base64
from datetime import timedelta

import pytest
from django.utils import timezone

from routing.domain.heatmap import HOURS

from .fakes import line

CHI, DEN = (-87.63, 41.88), (-104.99, 39.74)


def soon():
    return (timezone.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)


def body(**over):
    data = {
        "routes": [line(CHI, DEN, 60), line(CHI, (-96, 44.5), 30) + line((-96, 44.5), DEN, 30)],
        "departure": soon().isoformat(),
        "load_lb": 42_000,
    }
    return data | over


def post(client, data):
    return client.post("/api/heatmap", data, content_type="application/json")


def frames_of(data, metric="risk"):
    return base64.b64decode(data["frames"][metric])


def test_heatmap_shape(client, apis):
    data = post(client, body()).json()
    n = len(data["points"])
    assert n > 50
    assert data["hours"] == 49  # departure hour plus 48, per the spec
    assert set(data["frames"]) == {"risk", "wind", "rain", "snow"}
    assert all(len(frames_of(data, m)) == 49 * n for m in data["frames"])
    assert data["start"].endswith("Z")
    assert data["cell_deg"] in (0.2, 0.25, 0.3)


def test_storm_moves_into_frames(client, apis):
    start = int(soon().timestamp())

    def passing_storm(lon, lat, t):
        hit = t >= start + 12 * 3600 and lon < -100
        return {"wind": 60.0 if hit else 8.0, "gust": 0.0, "rain": 0.0, "showers": 0.0, "snow": 0.0}

    apis.weather = passing_storm
    data = post(client, body()).json()
    n = len(data["points"])
    risk = frames_of(data)
    west = [i for i, (lon, _) in enumerate(data["points"]) if lon < -100.5]
    assert west
    assert all(risk[0 * n + i] == 0 for i in west)
    assert all(risk[13 * n + i] == 4 for i in west)
    east = [i for i, (lon, _) in enumerate(data["points"]) if lon > -99]
    assert all(risk[13 * n + i] == 0 for i in east)


def test_forecast_requested_for_whole_window(client, apis):
    post(client, body())
    q = apis.calls[0].url.params
    start = soon()
    assert q["start_hour"] == (start - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    assert q["end_hour"] == (start + timedelta(hours=HOURS + 1)).strftime("%Y-%m-%dT%H:%M")


def test_departure_is_not_clamped(client, apis):
    dep = timezone.now() - timedelta(minutes=3)
    data = post(client, body(departure=dep.isoformat())).json()
    assert data["start"] == dep.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@pytest.mark.parametrize(
    "over, message",
    [
        ({"routes": []}, "routes:"),
        ({"routes": [line(CHI, DEN, 5)] * 4}, "routes:"),
        ({"routes": [[[CHI[0], CHI[1]]]]}, "routes.0: A route needs 2"),
        ({"routes": [[[-87.6, 41.8], [200, 41.8]]]}, "routes.0: Coordinates are out of range."),
        ({"routes": [[[-87.6, 41.8], "x"]]}, "routes.0: Each point must be [lon, lat]."),
        ({"routes": [[[-87.6, 41.8, 3], [-88, 41]]]}, "routes.0: Each point must be [lon, lat]."),
        ({"departure": "2020-01-01T00:00:00Z"}, "departure: Departure is in the past"),
        ({"load_lb": 90_000}, "load_lb:"),
    ],
)
def test_invalid_heatmap_request(client, apis, over, message):
    resp = post(client, body(**over))
    assert resp.status_code == 400
    assert resp.json()["error"]["message"].startswith(message)
    assert apis.calls == []


def test_forecast_down(client, apis):
    apis.fail["api.open-meteo.com"] = [500] * 100  # every batch, every retry
    resp = post(client, body())
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "UPSTREAM_ERROR"


def test_heatmap_get_not_allowed(client):
    assert client.get("/api/heatmap").status_code == 405
