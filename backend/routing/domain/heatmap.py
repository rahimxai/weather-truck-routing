import base64
import math
from datetime import timedelta

import numpy as np
import shapely
from shapely import LineString

from .forecast import weather_at
from .risk import classify

HOURS = 49  # the departure hour, then every hour to +48 h
BUFFER_KM = 40
KM_PER_DEG_LAT = 111.32
# Near the forecast models' own resolution first; coarser only to stay under the cap.
CELL_SIZES = (0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0)
MAX_CELLS = 600
METRICS = ("risk", "wind", "rain", "snow")
NO_DATA = 255


def corridor_cells(routes, buffer_km=BUFFER_KM, max_cells=MAX_CELLS):
    """Centres of grid cells within buffer_km of any route, and the cell size in degrees.

    Cells sit on a global grid (multiples of the size), so a place always maps to the same cell.
    """
    lat0 = float(np.mean([lat for line in routes for _, lat in line]))
    # Shrink longitude so a degree is the same distance both ways, then buffer in degrees.
    k = math.cos(math.radians(lat0))
    lines = [LineString([(lon * k, lat) for lon, lat in line]) for line in routes]
    corridor = shapely.union_all(lines).buffer(buffer_km / KM_PER_DEG_LAT)
    west, south, east, north = corridor.bounds

    for size in CELL_SIZES:
        lons = np.arange(math.floor(west / k / size), math.ceil(east / k / size) + 1) * size
        lats = np.arange(math.floor(south / size), math.ceil(north / size) + 1) * size
        xs, ys = np.meshgrid(lons, lats)
        inside = shapely.contains_xy(corridor, xs * k, ys)
        if inside.sum() <= max_cells or size == CELL_SIZES[-1]:
            cells = [
                (round(float(x), 4), round(float(y), 4))
                for x, y in zip(xs[inside], ys[inside], strict=True)
            ]
            return cells, size


def score_frames(sources, departure, load_lb, weather=weather_at, hours=HOURS):
    """Risk levels (0-4) per metric for every cell and hour, hour-major: frame[h * n + i].

    `weather(source, time)` gives one cell's weather; by default sources are forecast Series.
    Uses the same classifier as the route checkpoints, so the map and the routes agree.
    """
    n = len(sources)
    frames = {m: bytearray(hours * n) for m in METRICS}
    times = [departure + timedelta(hours=h) for h in range(hours)]
    for i, src in enumerate(sources):
        for h, t in enumerate(times):
            try:
                risk = classify(weather(src, t), load_lb)
            except ValueError:
                values = (NO_DATA,) * len(METRICS)
            else:
                values = (risk.level, risk.wind, risk.rain, risk.snow)
            for m, v in zip(METRICS, values, strict=True):
                frames[m][h * n + i] = v
    return frames


def encode(frames):
    return {m: base64.b64encode(bytes(b)).decode("ascii") for m, b in frames.items()}
