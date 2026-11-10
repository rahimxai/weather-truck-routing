from datetime import UTC, datetime

import pytest

from routing.domain.checkpoints import risk_segments, risk_spans, time_profile
from routing.domain.geometry import cumulative_miles, simplify, slice_line
from routing.domain.models import Checkpoint, Level, Risk, Route

from .fakes import line

L, M, H, S, NT = Level
DEPART = datetime(2026, 11, 12, 14, tzinfo=UTC)
NORTH = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]


def cp(level, covered):
    return Checkpoint(0, 0, 0, DEPART, covered, risk=Risk(level, "", level, L, L))


def test_profile_adds_start_and_arrival():
    assert time_profile([(10, 600)], 20, 1200) == [(0, 0), (10, 600), (20, 1200)]


def test_profile_without_instructions_is_linear():
    assert time_profile([], 100, 3600) == [(0, 0), (100, 3600)]


def test_profile_never_goes_back_in_time():
    profile = time_profile([(5, 400), (10, 300), (12, 5000)], 20, 1200)
    times = [t for _, t in profile]
    assert times == sorted(times)
    assert max(times) == 1200  # capped at arrival


def test_profile_clamps_offsets_past_the_end():
    assert time_profile([(20.0001, 1199)], 20, 1200)[-2][0] == 20


def test_spans_merge_same_levels():
    spans = risk_spans([cp(L, 12.5), cp(L, 25), cp(H, 25), cp(H, 12.5), cp(L, 5)])
    assert spans == [(L, 0, 37.5), (H, 37.5, 75), (L, 75, 80)]


def test_spans_skip_zero_length():
    assert risk_spans([cp(S, 0)]) == []


def test_slice_line_middle():
    cum = cumulative_miles(NORTH)
    part = slice_line(NORTH, cum, cum[1] / 2, cum[1] * 1.5)
    assert [lat for _, lat in part] == pytest.approx([0.5, 1.0, 1.5], abs=1e-6)


def test_slice_line_whole():
    cum = cumulative_miles(NORTH)
    assert slice_line(NORTH, cum, 0, cum[-1]) == NORTH


def test_segments_cover_the_route_end_to_end():
    pts = line((0.0, 0.0), (0.0, 2.0), 40)
    dist = cumulative_miles(pts)[-1]
    route = Route("A", pts, dist, 3600, [(0, 0), (dist, 3600)])
    third = dist / 3
    segs = risk_segments(route, [cp(L, third), cp(S, third), cp(L, third)])
    assert [lvl for lvl, _ in segs] == [L, S, L]
    assert segs[0][1][0] == pts[0]
    assert segs[-1][1][-1] == pytest.approx(pts[-1])
    assert segs[0][1][-1] == pytest.approx(segs[1][1][0])  # pieces join up


def test_simplify_drops_collinear_points():
    pts = line((0.0, 0.0), (1.0, 1.0), 100)
    assert simplify(pts, 0.001) == [(0.0, 0.0), (1.0, 1.0)]


def test_simplify_keeps_short_lines():
    assert simplify([(0.0, 0.0), (1.0, 1.0)], 0.1) == [(0.0, 0.0), (1.0, 1.0)]
