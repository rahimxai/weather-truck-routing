import logging
import time
from datetime import timedelta

from ..adapters import open_meteo
from ..domain.heatmap import HOURS, corridor_cells, encode, score_frames
from ..domain.scenarios import scenario_weather

log = logging.getLogger(__name__)


def corridor_heatmap(routes, departure, load_lb, scenario=None):
    """Grid cells along the routes and their encoded risk frames for 0-48 h after departure."""
    started = time.perf_counter()
    cells, size = corridor_cells(routes)
    if scenario:
        # Same anchor as the plan: route A's two ends.
        storm = scenario_weather(scenario, routes[0][0], routes[0][-1], departure)
        frames = score_frames(cells, departure, load_lb, weather=lambda c, t: storm(*c, t))
    else:
        end = departure + timedelta(hours=HOURS - 1)
        frames = score_frames(open_meteo.forecasts(cells, departure, end), departure, load_lb)
    frames = encode(frames)
    log.info(
        "heatmap: %d cells at %.2f deg in %.0f ms",
        len(cells),
        size,
        (time.perf_counter() - started) * 1000,
    )
    return cells, size, frames
