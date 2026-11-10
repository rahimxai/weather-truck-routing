import logging
import time
from dataclasses import replace

from ..adapters import open_meteo, tomtom
from ..domain.checkpoints import build_checkpoints
from ..domain.forecast import weather_at
from ..domain.places import locate, states_crossed, via_roads
from ..domain.recommend import recommend, score
from ..domain.risk import assess
from ..domain.scenarios import scenario_weather
from ..errors import ForecastUnavailable

log = logging.getLogger(__name__)


def cell(cp):
    # About 7 mi across: near the forecast models' own resolution, and lets
    # overlapping routes share one lookup.
    return (round(cp.lon, 1), round(cp.lat, 1))


def live_weather(checkpoints):
    """Checkpoint -> Weather from Open-Meteo, one batched fetch for every route."""
    cells = list(dict.fromkeys(map(cell, checkpoints)))
    start, end = min(cp.eta for cp in checkpoints), max(cp.eta for cp in checkpoints)
    series = dict(zip(cells, open_meteo.forecasts(cells, start, end), strict=True))
    return lambda cp: weather_at(series[cell(cp)], cp.eta)


def demo_weather(scenario, routes, departure):
    """Checkpoint -> Weather from a labelled scenario, anchored to route A's two ends
    (the heatmap request carries the same ends, so both draw the same storm)."""
    line = routes[0].geometry
    storm = scenario_weather(scenario, line[0], line[-1], departure)
    return lambda cp: storm(cp.lon, cp.lat, cp.eta)


def plan_trip(origin, dest, departure, load_lb, interval_mi, scenario=None):
    """Routes, checkpoint weather and risk, ranked. Returns (Recommendation, warnings)."""
    started = time.perf_counter()
    routes = tomtom.truck_routes(origin, dest, departure, load_lb)
    groups = [locate(r, build_checkpoints(r, interval_mi, departure)) for r in routes]
    flat = [cp for g in groups for cp in g]

    lookup = demo_weather(scenario, routes, departure) if scenario else live_weather(flat)

    scored = []
    for route, cps in zip(routes, groups, strict=True):
        try:
            wx = [lookup(cp) for cp in cps]
        except ValueError:
            raise ForecastUnavailable() from None
        sr = score(route, assess(cps, wx, load_lb))
        scored.append(
            replace(
                sr,
                via=via_roads(route.roads, route.distance_mi),
                states=states_crossed(route.state_codes),
            )
        )

    rec = recommend(scored)
    warnings = list(rec.warnings)
    if len(routes) < 3:
        noun = "route" if len(routes) == 1 else "routes"
        warnings.append(f"Only {len(routes)} distinct {noun} found for this trip.")

    log.info(
        "plan: %d routes, %d checkpoints, %s weather in %.0f ms",
        len(routes),
        len(flat),
        scenario or "live",
        (time.perf_counter() - started) * 1000,
    )
    return rec, warnings
