from datetime import UTC, datetime

import pytest

from routing.domain.models import Checkpoint, Level, Risk, Route, Weather
from routing.domain.recommend import (
    NO_TRAVEL_WARNING,
    recommend,
    score,
    summarize,
    time_note,
)
from routing.domain.risk import assess

L, M, H, S, NT = Level
DEPART = datetime(2026, 11, 12, 14, 0, tzinfo=UTC)


def cp(level, covered):
    risk = Risk(level, "test", wind=level, rain=L, snow=L)
    return Checkpoint(mile=0, lon=0, lat=0, eta=DEPART, covered_mi=covered, risk=risk)


def make(id, dur_s, *spans):
    dist = sum(mi for _, mi in spans)
    route = Route(id, [(0, 0), (0, 1)], dist, dur_s, profile=[(0, 0), (dist, dur_s)])
    return score(route, [cp(level, mi) for level, mi in spans])


def winner(*routes):
    return recommend(list(routes)).best.route.id


def test_summary_miles_and_avg_risk():
    s = summarize([cp(L, 50), cp(H, 25), cp(S, 25)], 100)
    assert s.miles_by_level == {L: 50, M: 0, H: 25, S: 25, NT: 0}
    assert s.avg_risk == 1.25  # (0*50 + 2*25 + 3*25) / 100


def test_zero_length_route_avg_is_zero():
    assert summarize([cp(L, 0)], 0).avg_risk == 0


def test_no_travel_ranks_before_severe():
    a = make("A", 100, (NT, 1), (L, 99))
    b = make("B", 900, (S, 100))
    assert winner(a, b) == "B"


def test_fewest_severe_wins():
    a = make("A", 100, (S, 10), (L, 90))
    b = make("B", 900, (H, 100))
    assert winner(a, b) == "B"


def test_fewest_high_wins_over_avg_risk():
    a = make("A", 100, (H, 30), (L, 170))
    b = make("B", 900, (H, 10), (M, 190))  # higher average, fewer High miles
    assert winner(a, b) == "B"


def test_avg_risk_breaks_tie():
    a = make("A", 100, (M, 50), (L, 50))
    b = make("B", 900, (M, 20), (L, 80))
    assert winner(a, b) == "B"


def test_duration_breaks_tie():
    a = make("A", 900, (L, 100))
    b = make("B", 100, (L, 100))
    assert winner(a, b) == "B"


def test_rounding_stops_float_noise_deciding():
    a = make("A", 100, (S, 25.04), (L, 74.96))
    b = make("B", 900, (S, 25.0), (L, 75.0))
    assert winner(a, b) == "A"  # 25.0 vs 25.0 Severe, same avg at 0.01, A is faster


def test_exact_tie_keeps_router_order():
    a = make("A", 100, (L, 100))
    b = make("B", 100, (L, 100))
    rec = recommend([a, b])
    assert rec.best.route.id == "A"
    assert rec.explanation == "Route A and Route B tie on risk and travel time."


def test_ranked_order_is_full():
    a = make("A", 100, (S, 10), (L, 90))
    b = make("B", 100, (H, 10), (L, 90))
    c = make("C", 100, (NT, 10), (L, 90))
    assert [r.route.id for r in recommend([a, b, c]).ranked] == ["B", "A", "C"]


def test_explain_no_travel():
    a = make("A", 3600, (NT, 12.5), (L, 87.5))
    b = make("B", 4500, (L, 100))
    assert (
        recommend([a, b]).explanation
        == "Route B: 0 No Travel miles vs 12.5 on Route A; 15 min longer."
    )


def test_explain_avg_risk():
    a = make("A", 3600, (M, 25), (L, 75))
    b = make("B", 7500, (M, 10), (L, 90))
    assert recommend([a, b]).explanation == (
        "Route B: same Severe and High miles as Route A, "
        "lower average risk (0.10 vs 0.25); 1 h 05 min longer."
    )


def test_explain_duration():
    a = make("A", 3600, (L, 100))
    b = make("B", 4320, (L, 100))
    assert recommend([a, b]).explanation == "Route A: same risk as Route B; 12 min faster."


def test_explain_names_why_fastest_lost():
    a = make("A", 3600, (NT, 37.5), (L, 62.5))  # fastest, blocked
    b = make("B", 7800, (L, 100))
    c = make("C", 9300, (L, 100))
    assert recommend([a, b, c]).explanation == (
        "Route B: same risk as Route C; 25 min faster. "
        "Route A is 1 h 10 min faster but has 37.5 No Travel miles."
    )


def test_explain_fastest_lost_on_average_risk():
    a = make("A", 3600, (M, 80), (L, 20))
    b = make("B", 7800, (M, 10), (L, 90))
    c = make("C", 9000, (M, 10), (L, 90))
    assert recommend([a, b, c]).explanation.endswith(
        "Route A is 1 h 10 min faster but riskier overall (average 0.80 vs 0.10)."
    )


def test_explain_skips_extra_line_when_runner_up_is_fastest():
    a = make("A", 3600, (S, 10), (L, 90))
    b = make("B", 7200, (L, 100))
    c = make("C", 9000, (NT, 10), (L, 90))
    assert recommend([a, b, c]).explanation == (
        "Route B: 0 Severe miles vs 10 on Route A; 1 h 00 min longer."
    )


def test_single_route():
    rec = recommend([make("A", 100, (L, 100))])
    assert rec.explanation == "Route A is the only route found."
    assert rec.warnings == []


def test_no_travel_warning_when_best_route_blocked():
    a = make("A", 100, (NT, 5), (L, 95))
    b = make("B", 100, (NT, 10), (L, 90))
    assert recommend([a, b]).warnings == [NO_TRAVEL_WARNING]


def test_tiny_no_travel_stretch_still_warns():
    a = make("A", 100, (L, 99.99), (NT, 0.01))  # rounds to 0.0 No Travel miles
    assert recommend([a]).warnings == [NO_TRAVEL_WARNING]


@pytest.mark.parametrize(
    "diff, note",
    [
        (0, "same travel time"),
        (30, "slightly longer"),
        (-30, "slightly faster"),
        (720, "12 min longer"),
        (3900, "1 h 05 min longer"),
        (-7200, "2 h 00 min faster"),
    ],
)
def test_time_note(diff, note):
    assert time_note(diff) == note


def worked_example(load_lb):
    """Plan section 4.7: wind on Route A vs rain on Route B, at a given load."""

    def route(id, miles, secs, spans):
        cps = [Checkpoint(mile=0, lon=0, lat=0, eta=DEPART, covered_mi=mi) for _, mi in spans]
        wx = [Weather(wind, 0, rain, 0) for (wind, rain), _ in spans]
        r = Route(id, [(0, 0), (0, 1)], miles, secs, profile=[(0, 0), (miles, secs)])
        return score(r, assess(cps, wx, load_lb))

    a = route("A", 310, 5 * 3600 + 10 * 60, [((38, 0), 25), ((5, 0), 285)])
    b = route("B", 334, 5 * 3600 + 32 * 60, [((5, 0.30), 50), ((5, 0), 284)])
    return recommend([a, b])


def test_worked_example_heavy_load_picks_b():
    rec = worked_example(42_000)
    assert rec.best.route.id == "B"
    assert rec.explanation == "Route B: 0 Severe miles vs 25 on Route A; 22 min longer."


def test_worked_example_lighter_load_picks_a():
    rec = worked_example(30_000)
    assert rec.best.route.id == "A"
    assert rec.explanation == "Route A: 25 High miles vs 50 on Route B; 22 min faster."
