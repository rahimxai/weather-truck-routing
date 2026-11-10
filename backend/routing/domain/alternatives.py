import math

# Fractions of the straight-line distance to push a via point sideways, tried in order.
DETOURS = (0.2, -0.2, 0.35, -0.35)


def detour_points(origin, dest, fractions=DETOURS):
    """Via points off to each side of the trip's midpoint, to force different corridors."""
    (lon1, lat1), (lon2, lat2) = origin, dest
    mid_lat = (lat1 + lat2) / 2
    # Work in a locally flat frame where a degree of longitude is shorter than one of latitude.
    k = math.cos(math.radians(mid_lat))
    dx, dy = (lon2 - lon1) * k, lat2 - lat1
    length = math.hypot(dx, dy)
    if length == 0:
        return []
    nx, ny = -dy / length, dx / length
    mid_lon = (lon1 + lon2) / 2
    return [(mid_lon + nx * f * length / k, mid_lat + ny * f * length) for f in fractions]


def cells(pts, size=0.05):
    return {(round(x / size), round(y / size)) for x, y in pts}


def same_corridor(a, b, threshold=0.85):
    """True when two lines mostly share the same ~3 mile grid cells."""
    ca, cb = cells(a), cells(b)
    return len(ca & cb) / len(ca | cb) >= threshold
