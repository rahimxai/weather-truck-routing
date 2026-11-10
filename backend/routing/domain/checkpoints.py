from bisect import bisect_left
from datetime import UTC, timedelta
from itertools import pairwise

from .geometry import cumulative_miles, point_at_mile, slice_line
from .models import Checkpoint, Route


def checkpoint_miles(total, interval):
    """Mile 0, every `interval` miles, and the destination."""
    # Multiply instead of adding up steps so long routes don't drift.
    miles = [i * interval for i in range(int(total // interval) + 1)]
    if total - miles[-1] > 1e-6:
        miles.append(total)
    return miles


def coverage(miles):
    """Road each checkpoint owns: halfway to each neighbour, so it sums to the route length."""
    bounds = [miles[0], *((a + b) / 2 for a, b in pairwise(miles)), miles[-1]]
    return [end - start for start, end in pairwise(bounds)]


def time_profile(pairs, distance_mi, duration_s):
    """Clean (mile, seconds) pairs from the router into a profile that starts at (0, 0),
    ends at the arrival, and never goes back in time."""
    raw = sorted([(0.0, 0.0), *pairs, (distance_mi, duration_s)])
    out, t = [], 0.0
    for mile, secs in raw:
        t = min(max(t, secs), duration_s)
        out.append((min(max(mile, 0.0), distance_mi), t))
    return out


def risk_spans(cps):
    """Merge neighbouring checkpoints with the same level into (level, start_mi, end_mi)."""
    spans, start = [], 0.0
    for cp in cps:
        end = start + cp.covered_mi
        if end > start:
            if spans and spans[-1][0] == cp.risk.level:
                spans[-1] = (cp.risk.level, spans[-1][1], end)
            else:
                spans.append((cp.risk.level, start, end))
        start = end
    return spans


def risk_segments(route: Route, cps):
    """(level, path) pieces of the route line, split where the checkpoint level changes."""
    cum = cumulative_miles(route.geometry)
    scale = cum[-1] / route.distance_mi if route.distance_mi else 0.0
    return [
        (level, slice_line(route.geometry, cum, start * scale, end * scale))
        for level, start, end in risk_spans(cps)
    ]


def eta_seconds(profile, mile):
    """Seconds after departure at a mile, interpolated along the router's time profile."""
    miles = [m for m, _ in profile]
    if mile <= miles[0]:
        return profile[0][1]
    if mile >= miles[-1]:
        return profile[-1][1]
    i = bisect_left(miles, mile)
    (m0, t0), (m1, t1) = profile[i - 1], profile[i]
    return t0 + (t1 - t0) * (mile - m0) / (m1 - m0)


def build_checkpoints(route: Route, interval_mi, departure):
    if departure.tzinfo is None:
        raise ValueError("departure must be timezone-aware")
    departure = departure.astimezone(UTC)

    miles = checkpoint_miles(route.distance_mi, interval_mi)
    cum = cumulative_miles(route.geometry)
    # The router's distance and the polyline length differ slightly; scale so the
    # destination checkpoint lands on the last point of the line.
    scale = cum[-1] / route.distance_mi if route.distance_mi else 0.0

    cps = []
    for mile, covered in zip(miles, coverage(miles), strict=True):
        lon, lat = point_at_mile(route.geometry, cum, mile * scale)
        eta = departure + timedelta(seconds=eta_seconds(route.profile, mile))
        cps.append(Checkpoint(mile=mile, lon=lon, lat=lat, eta=eta, covered_mi=covered))
    return cps
