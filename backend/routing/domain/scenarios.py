"""Labelled demo weather, so the risk rules can be shown even when the real forecast is calm.

Never mixed with live data: the plan and heatmap use either this or Open-Meteo, never both,
and the API echoes the scenario so the UI can say the weather is simulated.
"""

import math

from .models import Weather

SCENARIOS = {"winter_storm": "Simulated winter storm"}

KM_PER_DEG_LAT = 111.32


def ramp(x, inner, outer):
    """1 within inner, 0 beyond outer, linear between (all in absolute value)."""
    x = abs(x)
    if x <= inner:
        return 1.0
    if x >= outer:
        return 0.0
    return (outer - x) / (outer - inner)


def winter_storm(origin, dest, departure):
    """A storm laid across the middle of this trip, as a (lon, lat, when) -> Weather function.

    Sizes scale with the trip length D, so the shape works for short and long trips:
    - high wind (41 mph) on the direct line, with a short 48 mph core
    - heavy snow (1.4 in/hr, 2.3 at its core) in bands either side, where detours run
    At 25,000 lb the direct route has the fewest Severe miles; at 45,000 lb the load rules
    make its wind Severe and No Travel, and a snowy alternative wins instead.
    """
    (lon1, lat1), (lon2, lat2) = origin, dest
    mid_lon, mid_lat = (lon1 + lon2) / 2, (lat1 + lat2) / 2
    k = math.cos(math.radians(mid_lat)) * KM_PER_DEG_LAT
    dx, dy = (lon2 - lon1) * k, (lat2 - lat1) * KM_PER_DEG_LAT
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    start = departure.timestamp()

    def weather(lon, lat, when):
        x, y = (lon - mid_lon) * k, (lat - mid_lat) * KM_PER_DEG_LAT
        along = (x * ux + y * uy) / length  # fractions of the trip length
        off = (-x * uy + y * ux) / length
        h = (when.timestamp() - start) / 3600
        # Builds over the first couple of hours and dies out after about 40 hours.
        strength = min(1.0, max(0.0, (h + 1) / 3)) * min(1.0, max(0.0, (44 - h) / 8))

        line = ramp(off, 0.06, 0.10)
        wind = 10 + strength * line * (31 * ramp(along, 0.09, 0.13) + 7 * ramp(along, 0.02, 0.03))
        bands = ramp(along, 0.20, 0.26) * ramp(abs(off) - 0.25, 0.11, 0.15)
        snow = strength * bands * (1.4 + 0.9 * ramp(along, 0.08, 0.10))
        return Weather(wind_mph=wind, gust_mph=wind * 1.4, rain_in_hr=0.0, snow_in_hr=snow)

    return weather


def scenario_weather(name, origin, dest, departure):
    if name == "winter_storm":
        return winter_storm(origin, dest, departure)
    raise ValueError(f"Unknown scenario {name!r}")
