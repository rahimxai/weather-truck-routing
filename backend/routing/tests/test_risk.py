import pytest

from routing.domain.models import Level, Weather
from routing.domain.risk import RAIN_IN_HR, SNOW_IN_HR, classify, precip_risk, wind_risk

L, M, H, S, NT = Level


def wx(wind=0.0, rain=0.0, snow=0.0, gust=0.0):
    return Weather(wind_mph=wind, gust_mph=gust, rain_in_hr=rain, snow_in_hr=snow)


@pytest.mark.parametrize(
    "mph, level",
    [
        (0, L), (24.9, L), (25.0, M), (34.9, M), (35.0, H), (44.9, H),
        (45.0, S), (54.9, S), (55.0, NT), (90, NT),
    ],
)  # fmt: skip
def test_wind_bands(mph, level):
    assert wind_risk(mph, load_lb=0)[0] == level


@pytest.mark.parametrize(
    "in_hr, level",
    [
        (0, L), (0.09, L), (0.10, M), (0.24, M), (0.25, H), (0.49, H),
        (0.50, S), (1.00, S), (1.01, NT),
    ],
)  # fmt: skip
def test_rain_bands(in_hr, level):
    assert precip_risk("Rain", in_hr, RAIN_IN_HR)[0] == level


@pytest.mark.parametrize(
    "in_hr, level",
    [
        (0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H),
        (2.0, S), (3.0, S), (3.01, NT),
    ],
)  # fmt: skip
def test_snow_bands(in_hr, level):
    assert precip_risk("Snow", in_hr, SNOW_IN_HR)[0] == level


@pytest.mark.parametrize(
    "mph, load, level",
    [
        (40, 40_000, H),  # exactly 40,000 is not "more than"
        (40, 40_001, S),
        (35, 40_001, S),
        (34.9, 80_000, M),  # load rules start at 35 mph
        (44.9, 40_001, S),
        (50, 30_000, S),
        (50, 30_001, NT),
        (45, 30_001, NT),
        (54.9, 80_000, NT),
        (55, 0, NT),
        (40, 35_000, H),  # heavy, but not over 40,000
    ],
)
def test_load_rules(mph, load, level):
    assert wind_risk(mph, load)[0] == level


def test_heavy_load_reason_names_load():
    assert wind_risk(38, 42_000)[1] == "Wind 38.0 mph with 42,000 lb load"


def test_light_load_reason_is_just_wind():
    assert wind_risk(38, 20_000)[1] == "Wind 38.0 mph"


def test_float_noise_does_not_lower_level():
    assert precip_risk("Rain", 0.7 - 0.45, RAIN_IN_HR)[0] == H  # 0.24999999999999994


def test_wind_classified_as_displayed():
    level, text = wind_risk(34.96, 0)
    assert (level, text) == (H, "Wind 35.0 mph")


def test_worst_of_wins():
    risk = classify(wx(wind=38, snow=2.5), load_lb=10_000)
    assert risk.level == S
    assert risk.reason == "Snow 2.50 in/hr"
    assert (risk.wind, risk.rain, risk.snow) == (H, L, S)


def test_tied_conditions_both_named():
    risk = classify(wx(wind=38, rain=0.30), load_lb=10_000)
    assert risk.level == H
    assert risk.reason == "Wind 38.0 mph; Rain 0.30 in/hr"


def test_load_rule_applies_before_combining():
    risk = classify(wx(wind=38, rain=0.30), load_lb=42_000)
    assert risk.level == S
    assert risk.reason == "Wind 38.0 mph with 42,000 lb load"


def test_calm_is_low():
    risk = classify(wx(wind=12, gust=30), load_lb=80_000)
    assert risk.level == L
    assert risk.reason == "Low risk"


def test_gusts_are_info_only():
    assert classify(wx(wind=10, gust=70), load_lb=80_000).level == L


@pytest.mark.parametrize("load", [0, 30_000, 30_001, 40_000, 40_001, 80_000])
def test_level_never_drops_as_wind_rises(load):
    levels = [wind_risk(i / 10, load)[0] for i in range(800)]
    assert levels == sorted(levels)


def test_level_never_drops_as_load_rises():
    loads = [0, 30_000, 30_001, 40_000, 40_001, 80_000]
    for i in range(800):
        levels = [wind_risk(i / 10, load)[0] for load in loads]
        assert levels == sorted(levels), f"wind {i / 10}"


@pytest.mark.parametrize("field", ["rain_in_hr", "snow_in_hr"])
def test_level_never_drops_as_precip_rises(field):
    levels = [classify(wx(**{field[:4]: i / 100}), 0).level for i in range(400)]
    assert levels == sorted(levels)


def test_level_labels():
    assert [lvl.label for lvl in Level] == ["Low", "Moderate", "High", "Severe", "No Travel"]
