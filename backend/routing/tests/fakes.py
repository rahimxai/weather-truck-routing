"""Fake TomTom and Open-Meteo servers, shaped like their documented responses."""

import json
import threading
from datetime import UTC, datetime
from urllib.parse import unquote

import httpx

from routing.domain.geometry import cumulative_miles
from routing.domain.units import M_PER_MI


def line(a, b, n=50):
    """n+1 evenly spaced (lon, lat) points from a to b."""
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


def tt_route(pts, mph=55.0, legs=1):
    """A Calculate Route `routes[]` item driving `pts` at a steady speed."""
    cum = cumulative_miles(pts)
    secs = [round(m / mph * 3600) for m in cum]
    step = max(1, len(pts) // 10)
    instructions = [
        {
            "routeOffsetInMeters": round(cum[i] * M_PER_MI),
            "travelTimeInSeconds": secs[i],
            "point": {"latitude": pts[i][1], "longitude": pts[i][0]},
            "maneuver": "STRAIGHT",
        }
        for i in range(0, len(pts), step)
    ]
    cut = len(pts) // legs
    chunks = [pts[i * cut : (i + 1) * cut + 1] for i in range(legs)]
    return {
        "summary": {
            "lengthInMeters": round(cum[-1] * M_PER_MI),
            "travelTimeInSeconds": secs[-1],
            "departureTime": "2026-11-12T14:00:00+00:00",
        },
        "legs": [
            {"points": [{"latitude": y, "longitude": x} for x, y in chunk]} for chunk in chunks
        ],
        "guidance": {"instructions": instructions},
    }


def calm(lon, lat, t):
    return {"wind": 10.0, "gust": 18.0, "rain": 0.0, "showers": 0.0, "snow": 0.0}


class FakeApis:
    """httpx transport handler; tests set routes, detour_routes, weather, fail, etc."""

    def __init__(self):
        self.calls = []
        self.routes = []
        self.detour_routes = []
        self.weather = calm
        self.fail = {}  # host -> list of status codes to return before succeeding
        self.geocode_results = []
        self.detour_status = 200
        self._lock = threading.Lock()  # detour requests arrive from several threads

    def transport(self):
        return httpx.MockTransport(self)

    def client(self):
        return httpx.Client(transport=self.transport())

    def __call__(self, request):
        self.calls.append(request)
        fails = self.fail.get(request.url.host)
        if fails:
            status = fails.pop(0)
            if status == "timeout":
                raise httpx.ReadTimeout("timed out", request=request)
            return httpx.Response(status, text="<error>nope</error>")
        if request.url.host == "api.tomtom.com":
            return self.tomtom(request)
        return self.open_meteo(request)

    def tomtom(self, request):
        path = unquote(request.url.path)
        if path.startswith("/search/2/geocode/"):
            return httpx.Response(200, json={"results": self.geocode_results})
        stops = path.split("/calculateRoute/")[1].removesuffix("/json").split(":")
        if len(stops) == 2:
            return httpx.Response(200, json={"routes": self.routes})
        if self.detour_status != 200:
            return httpx.Response(self.detour_status, text="<error>nope</error>")
        with self._lock:
            routes, self.detour_routes = self.detour_routes[:1], self.detour_routes[1:]
        return httpx.Response(200, json={"routes": routes})

    def open_meteo(self, request):
        q = request.url.params
        lats = [float(v) for v in q["latitude"].split(",")]
        lons = [float(v) for v in q["longitude"].split(",")]
        first = datetime.fromisoformat(q["start_hour"]).replace(tzinfo=UTC)
        last = datetime.fromisoformat(q["end_hour"]).replace(tzinfo=UTC)
        times = list(range(int(first.timestamp()), int(last.timestamp()) + 1, 3600))
        out = []
        for lon, lat in zip(lons, lats, strict=True):
            rows = [self.weather(lon, lat, t) for t in times]
            out.append(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly_units": {
                        "time": "unixtime",
                        "wind_speed_10m": "mp/h",
                        "wind_gusts_10m": "mp/h",
                        "rain": "inch",
                        "showers": "inch",
                        "snowfall": "inch",
                    },
                    "hourly": {
                        "time": times,
                        "wind_speed_10m": [r["wind"] for r in rows],
                        "wind_gusts_10m": [r["gust"] for r in rows],
                        "rain": [r["rain"] for r in rows],
                        "showers": [r["showers"] for r in rows],
                        "snowfall": [r["snow"] for r in rows],
                    },
                }
            )
        body = out[0] if len(out) == 1 else out
        return httpx.Response(
            200, content=json.dumps(body), headers={"content-type": "application/json"}
        )
