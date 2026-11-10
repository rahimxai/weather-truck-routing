import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from routing.domain.models import Checkpoint, Route
from routing.domain.places import locate, primary_road, road_at, states_crossed, via_roads
from routing.domain.units import m_to_mi

# Real TomTom guidance for three truck routes from Chicago to Denver.
REAL = json.loads((Path(__file__).parent / "data" / "tomtom_chicago_denver.json").read_text())


def real(i):
    r = REAL["routes"][i]
    steps = r["instructions"]
    roads = [(m_to_mi(s["routeOffsetInMeters"]), primary_road(s.get("roadNumbers"))) for s in steps]
    return roads, [s.get("stateCode") for s in steps], m_to_mi(r["lengthInMeters"])


def test_primary_road_drops_direction():
    assert primary_road(["I-88 W"]) == "I-88"


def test_primary_road_prefers_interstate():
    assert primary_road(["US-6 W", "I-80 W"]) == "I-80"


def test_primary_road_first_interstate_in_concurrency():
    assert primary_road(["I-55 S", "I-72 W", "US-36 W"]) == "I-55"


def test_primary_road_business_loop_is_not_interstate():
    assert primary_road(["US-287 N", "I-70 Bus W"]) == "US-287"


def test_primary_road_falls_back_to_first():
    assert primary_road(["US-385 S", "US-20 E"]) == "US-385"


def test_primary_road_empty():
    assert primary_road([]) is None
    assert primary_road(None) is None
    assert primary_road(["", "  "]) is None


ROADS = [(0, None), (5, "I-88"), (100, "I-80")]


def test_road_at_start_middle_and_end():
    assert [road_at(ROADS, m) for m in (0, 4.9, 5, 50, 100, 900)] == [
        None,
        None,
        "I-88",
        "I-88",
        "I-80",
        "I-80",
    ]


def test_road_at_without_roads():
    assert road_at([], 10) is None


def test_via_merges_across_a_short_street():
    roads = [(0, None), (2, "I-80"), (400, None), (400.2, "I-80"), (900, "I-76")]
    assert via_roads(roads, 1000) == ["I-80", "I-76"]


def test_via_keeps_four_longest_in_order():
    lengths = [100, 100, 300, 100, 100, 100]
    starts = [sum(lengths[:i]) for i in range(6)]
    roads = [(s, f"I-{i}") for i, s in enumerate(starts)]
    assert via_roads(roads, sum(lengths)) == ["I-0", "I-1", "I-2", "I-3"]


def test_via_without_roads():
    assert via_roads([], 500) == []


@pytest.mark.parametrize(
    "i, via",
    [
        (0, ["I-88", "I-80", "I-76"]),
        (1, ["I-57", "I-72", "I-55", "I-70"]),
        (2, ["I-39", "I-90", "SD-79", "I-25"]),
    ],
)
def test_real_routes_via(i, via):
    roads, _, total = real(i)
    assert via_roads(roads, total) == via


@pytest.mark.parametrize(
    "i, states",
    [
        (0, ["Illinois", "Iowa", "Nebraska", "Colorado"]),
        (1, ["Illinois", "Missouri", "Kansas", "Colorado"]),
        (
            2,
            [
                "Illinois",
                "Wisconsin",
                "Minnesota",
                "South Dakota",
                "Nebraska",
                "Wyoming",
                "Colorado",
            ],
        ),
    ],
)
def test_real_routes_states(i, states):
    _, codes, _ = real(i)
    assert states_crossed(codes) == states


def test_states_keep_first_visit_order():
    assert states_crossed(["IL", "IA", "IL", "IA", "NE"]) == ["Illinois", "Iowa", "Nebraska"]


def test_unknown_state_code_shown_as_is():
    assert states_crossed(["WA", "BC"]) == ["Washington", "BC"]


def test_states_skip_missing_codes():
    assert states_crossed([None, "", "CO"]) == ["Colorado"]


def test_locate_names_the_road_at_each_checkpoint():
    roads, _, total = real(0)
    route = Route("A", [], total, 0, [], roads)
    t = datetime(2026, 11, 12, tzinfo=UTC)
    cps = [Checkpoint(mile=m, lon=0, lat=0, eta=t, covered_mi=1) for m in (0, 100, 500, total)]
    assert [cp.road for cp in locate(route, cps)] == [None, "I-88", "I-80", None]
