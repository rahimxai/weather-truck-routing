import math
from bisect import bisect_left, bisect_right
from itertools import pairwise

from shapely import LineString

EARTH_RADIUS_MI = 3958.8


def haversine_mi(a, b):
    """Great-circle miles between two (lon, lat) points."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(pts):
    out = [0.0]
    for a, b in pairwise(pts):
        out.append(out[-1] + haversine_mi(a, b))
    return out


def point_at_mile(pts, cum, mile):
    """(lon, lat) at a distance along the line, clamped to its ends."""
    if mile <= 0:
        return pts[0]
    if mile >= cum[-1]:
        return pts[-1]
    # First vertex at or past the mile; cum[i - 1] < mile, so the segment has length.
    i = bisect_left(cum, mile)
    (x0, y0), (x1, y1) = pts[i - 1], pts[i]
    t = (mile - cum[i - 1]) / (cum[i] - cum[i - 1])
    return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)


def slice_line(pts, cum, start, end):
    """The part of the line between two distances along it."""
    inner = pts[bisect_right(cum, start) : bisect_left(cum, end)]
    return [point_at_mile(pts, cum, start), *inner, point_at_mile(pts, cum, end)]


def simplify(pts, tolerance):
    """Douglas-Peucker in degrees; keeps the payload small without visibly changing the line."""
    if len(pts) < 3:
        return list(pts)
    return list(LineString(pts).simplify(tolerance, preserve_topology=False).coords)
