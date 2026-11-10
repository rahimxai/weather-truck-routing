import re
from bisect import bisect_right
from dataclasses import replace

INTERSTATE = re.compile(r"^I-\d+$")
DIRECTION = re.compile(r"\s+[NSEW]$")
MAX_VIA = 4
# Shorter stretches are connectors, ramps or the first and last streets.
MIN_VIA_MI = 20
MIN_VIA_SHARE = 0.05

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}  # fmt: skip


def primary_road(numbers):
    """The road to name for a step: an interstate if there is one, else the first number.

    TomTom gives signed directions ("I-80 W"); they're dropped so both directions are one road.
    """
    names = [DIRECTION.sub("", n.strip()) for n in numbers or [] if n and n.strip()]
    return next((n for n in names if INTERSTATE.match(n)), names[0] if names else None)


def road_at(roads, mile):
    """The road a mile is on, from (start_mile, road) pairs sorted by mile."""
    i = bisect_right([m for m, _ in roads], mile)
    return roads[i - 1][1] if i else None


def via_roads(roads, total_mi):
    """The main roads in driving order: long stretches only, repeats merged, at most four."""
    stretches = []
    for i, (start, road) in enumerate(roads):
        end = roads[i + 1][0] if i + 1 < len(roads) else total_mi
        if stretches and stretches[-1][0] == road:
            stretches[-1][1] += end - start
        else:
            stretches.append([road, end - start])

    floor = max(MIN_VIA_MI, MIN_VIA_SHARE * total_mi)
    main = []
    for road, mi in stretches:
        if road is None or mi < floor:
            continue
        if main and main[-1][0] == road:
            main[-1][1] += mi
        else:
            main.append([road, mi])

    if len(main) > MAX_VIA:
        keep = sorted(range(len(main)), key=lambda i: -main[i][1])[:MAX_VIA]
        main = [main[i] for i in sorted(keep)]
    return [road for road, _ in main]


def states_crossed(codes):
    """State names in the order the route first reaches them.

    TomTom tags each guidance step with its state, so this is reliable for the order but not
    for which state a given mile is in: a long stretch with no steps keeps the last state.
    """
    seen = []
    for code in codes:
        if code and code not in seen:
            seen.append(code)
    return [STATE_NAMES.get(c, c) for c in seen]


def locate(route, cps):
    """Name the road at each checkpoint."""
    return [replace(cp, road=road_at(route.roads, cp.mile)) for cp in cps]
