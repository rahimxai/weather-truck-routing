import base64
from datetime import UTC, datetime

import pytest

from routing.domain.forecast import Series
from routing.domain.geometry import haversine_mi
from routing.domain.heatmap import (
    HOURS,
    MAX_CELLS,
    METRICS,
    NO_DATA,
    corridor_cells,
    encode,
    score_frames,
)
from routing.domain.models import Level

from .fakes import line

CHI, DEN = (-87.63, 41.88), (-104.99, 39.74)
DEPART = datetime(2026, 11, 12, 14, tzinfo=UTC)
T0 = int(DEPART.timestamp())


def nearest_mi(pt, pts):
    return min(haversine_mi(pt, p) for p in pts)


def test_cells_stay_inside_corridor():
    route = line(CHI, DEN, 300)
    cells, _ = corridor_cells([route])
    assert all(nearest_mi(c, route) < 26.5 for c in cells)  # 40 km = 24.9 mi, plus slack


def test_corridor_has_no_gaps():
    route = line(CHI, DEN, 300)
    cells, size = corridor_cells([route])
    reach = haversine_mi((0, 0), (size, size)) / 2 + 0.5
    assert all(nearest_mi(p, cells) <= reach for p in route[::10])


def test_cells_sit_on_a_global_grid():
    cells, size = corridor_cells([line(CHI, DEN, 100)])
    for x, y in cells:
        assert round(x / size, 6) == round(x / size)
        assert round(y / size, 6) == round(y / size)


def test_corridor_is_40km_wide_on_a_north_south_route():
    # East-west, a 0.2 degree cell at ~40 N is about 17 km, so 2 x 40 km is ~4.8 cells per row.
    cells, size = corridor_cells([line((-96.0, 33.0), (-96.0, 45.0), 200)])
    assert size == 0.2
    rows = {}
    for x, y in cells:
        rows.setdefault(y, []).append(x)
    widths = [len(xs) for y, xs in rows.items() if 35 < y < 43]
    assert 4.2 < sum(widths) / len(widths) < 5.4


def test_short_trip_uses_finest_grid():
    cells, size = corridor_cells([line(CHI, (-89.0, 41.5), 20)])
    assert size == 0.2
    assert 10 < len(cells) < 100


def test_long_trip_is_capped():
    ny, la = (-74.0, 40.7), (-118.2, 34.05)
    routes = [line(ny, la, 300), line(ny, (-95, 44), 150) + line((-95, 44), la, 150)]
    cells, size = corridor_cells(routes)
    assert len(cells) <= MAX_CELLS
    assert size > 0.2


def test_overlapping_routes_share_cells():
    route = line(CHI, DEN, 100)
    one, _ = corridor_cells([route])
    two, _ = corridor_cells([route, route])
    assert one == two
    assert len(set(two)) == len(two)


def series(wind):
    """One cell's hourly series covering the 49 frames (plus spares)."""
    n = HOURS + 3
    times = [T0 - 3600 + h * 3600 for h in range(n)]
    return Series(times, [wind(h - 1) for h in range(n)], [0.0] * n, [0.0] * n, [0.0] * n)


def test_frames_are_hour_major():
    calm = series(lambda h: 10.0)
    storm_later = series(lambda h: 50.0 if h >= 12 else 10.0)
    frames = score_frames([calm, storm_later], DEPART, load_lb=0)
    n = 2
    assert len(frames["risk"]) == HOURS * n
    assert frames["risk"][0 * n + 1] == Level.LOW
    assert frames["risk"][11 * n + 1] == Level.LOW  # frame h is exactly h hours after departure
    assert frames["risk"][12 * n + 1] == Level.SEVERE
    assert frames["risk"][12 * n + 0] == Level.LOW


def test_metrics_are_separate():
    n = HOURS + 3
    s = Series(
        [T0 - 3600 + h * 3600 for h in range(n)], [10.0] * n, [0.0] * n, [0.6] * n, [0.0] * n
    )
    frames = score_frames([s], DEPART, 0)
    assert frames["risk"][0] == Level.SEVERE  # 0.60 in/hr rain
    assert frames["rain"][0] == Level.SEVERE
    assert frames["wind"][0] == Level.LOW
    assert frames["snow"][0] == Level.LOW


def test_load_changes_wind_frames():
    s = series(lambda h: 50.0)
    assert score_frames([s], DEPART, 20_000)["wind"][0] == Level.SEVERE
    assert score_frames([s], DEPART, 35_000)["wind"][0] == Level.NO_TRAVEL


def test_every_metric_present():
    frames = score_frames([series(lambda h: 10.0)], DEPART, 0)
    assert tuple(frames) == METRICS


def test_missing_data_is_marked():
    s = series(lambda h: 10.0)
    s.wind[20] = None
    frames = score_frames([s], DEPART, 0)
    assert NO_DATA in frames["risk"]
    assert frames["risk"][0] == Level.LOW


def test_encode_round_trip():
    frames = {"risk": bytearray([0, 1, 2, 3, 4, 255])}
    assert base64.b64decode(encode(frames)["risk"]) == bytes([0, 1, 2, 3, 4, 255])


@pytest.mark.parametrize("routes", [[line(CHI, DEN, 50)], [line((-120, 47), (-70, 44), 50)]])
def test_cell_count_scales_sensibly(routes):
    cells, _ = corridor_cells(routes)
    assert 0 < len(cells) <= MAX_CELLS
