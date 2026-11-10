from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC
from urllib.parse import quote

from django.conf import settings

from ..domain.alternatives import detour_points, same_corridor
from ..domain.checkpoints import time_profile
from ..domain.models import Route
from ..domain.places import primary_road
from ..domain.units import lb_to_kg, m_to_mi
from ..errors import NoRoute, NotConfigured, UpstreamError
from .http import get_json, make_client

BASE = "https://api.tomtom.com"
IDS = "ABC"


def _key():
    if not settings.TOMTOM_API_KEY:
        raise NotConfigured()
    return settings.TOMTOM_API_KEY


def geocode(query):
    """Up to five US/Canada place suggestions for a partial query."""
    url = f"{BASE}/search/2/geocode/{quote(query, safe='')}.json"
    params = {
        "key": _key(),
        "typeahead": "true",
        "limit": 5,
        "countrySet": "US,CA",
        "language": "en-US",
    }
    with make_client() as client:
        data = get_json(client, "TomTom", url, params)
    return [
        {
            "label": r["address"]["freeformAddress"],
            "lat": r["position"]["lat"],
            "lon": r["position"]["lon"],
        }
        for r in data.get("results", [])
    ]


def parse_route(data, id=""):
    """One route from a Calculate Route response, with its time-vs-distance profile."""
    distance = m_to_mi(data["summary"]["lengthInMeters"])
    duration = data["summary"]["travelTimeInSeconds"]
    pts = [(p["longitude"], p["latitude"]) for leg in data["legs"] for p in leg["points"]]
    # Each instruction carries its offset from the start and the travel time to reach it.
    steps = data.get("guidance", {}).get("instructions", [])
    pairs = [(m_to_mi(s["routeOffsetInMeters"]), s["travelTimeInSeconds"]) for s in steps]
    # roadNumbers names the road followed after each step; steps on unnumbered streets are None.
    roads = [
        (m, primary_road(s.get("roadNumbers"))) for (m, _), s in zip(pairs, steps, strict=True)
    ]
    states = [s["stateCode"] for s in steps if s.get("stateCode")]
    profile = time_profile(pairs, distance, duration)
    return Route(id, pts, distance, duration, profile, roads, states)


def _calculate(client, stops, depart, load_lb, alternatives):
    locations = ":".join(f"{lat},{lon}" for lon, lat in stops)
    params = {
        "key": _key(),
        "travelMode": "truck",
        "vehicleCommercial": "true",
        "vehicleWeight": round(lb_to_kg(load_lb)),
        "departAt": depart.astimezone(UTC).isoformat(timespec="seconds"),
        "routeType": "fastest",
        "traffic": "true",
        "instructionsType": "coded",
        "maxAlternatives": alternatives,
        "alternativeType": "anyRoute",
    }
    url = f"{BASE}/routing/1/calculateRoute/{locations}/json"
    try:
        data = get_json(client, "TomTom", url, params)
    except UpstreamError as e:
        # 400 covers unroutable points (water, no road nearby, disconnected networks).
        if e.upstream_status == 400:
            raise NoRoute() from None
        raise
    return [parse_route(r) for r in data.get("routes", [])]


def _detours(origin, dest, depart, load_lb, found):
    def attempt(via):
        try:
            with make_client() as client:
                routes = _calculate(client, [origin, via, dest], depart, load_lb, 0)
        except (NoRoute, UpstreamError):
            return None
        return routes[0] if routes else None

    vias = detour_points(origin, dest)
    with ThreadPoolExecutor(len(vias)) as pool:
        candidates = list(pool.map(attempt, vias))

    extra = []
    for cand in candidates:
        if len(found) + len(extra) == 3:
            break
        if cand and not any(same_corridor(cand.geometry, r.geometry) for r in found + extra):
            extra.append(cand)
    return extra


def truck_routes(origin, dest, depart, load_lb):
    """Up to three distinct truck routes (A, B, C), the router's main route first."""
    with make_client() as client:
        found = _calculate(client, [origin, dest], depart, load_lb, 2)
    if not found:
        raise NoRoute()
    if len(found) < 3:
        # The router sometimes returns fewer alternatives; force others via side points.
        found += _detours(origin, dest, depart, load_lb, found)
    return [replace(r, id=IDS[i]) for i, r in enumerate(found[:3])]
