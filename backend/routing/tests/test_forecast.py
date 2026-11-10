from datetime import UTC, datetime

import pytest

from routing.domain.forecast import Series, parse_series, weather_at

T0 = int(datetime(2026, 11, 12, 14, tzinfo=UTC).timestamp())


def payload(units=None, **hourly):
    base = {
        "time": [T0, T0 + 3600],
        "wind_speed_10m": [20.0, 30.0],
        "wind_gusts_10m": [30.0, 40.0],
        "rain": [0.10, 0.20],
        "showers": [0.05, 0.0],
        "snowfall": [0.0, 1.0],
    }
    u = {
        "wind_speed_10m": "mp/h",
        "wind_gusts_10m": "mp/h",
        "rain": "inch",
        "showers": "inch",
        "snowfall": "inch",
    }
    return {"hourly": base | hourly, "hourly_units": u | (units or {})}


def at(h, m=0):
    return datetime(2026, 11, 12, h, m, tzinfo=UTC)


def test_parse_mph_and_inches_pass_through():
    s = parse_series(payload())
    assert s.wind == [20.0, 30.0]
    assert s.snow == [0.0, 1.0]


def test_rain_includes_showers():
    assert parse_series(payload()).rain == pytest.approx([0.15, 0.20])


def test_metric_units_are_converted():
    s = parse_series(
        payload(
            units={"wind_speed_10m": "km/h", "rain": "mm", "showers": "mm", "snowfall": "cm"},
            wind_speed_10m=[100.0, 0.0],
            rain=[25.4, 0.0],
            showers=[0.0, 0.0],
            snowfall=[2.54, 0.0],
        )
    )
    assert s.wind[0] == pytest.approx(62.137, abs=0.001)
    assert s.rain[0] == pytest.approx(1.0)
    assert s.snow[0] == pytest.approx(1.0)  # snowfall cm, not mm


def test_unknown_unit_is_rejected():
    with pytest.raises(ValueError, match="snowfall"):
        parse_series(payload(units={"snowfall": "ft"}))


def test_wind_interpolates_between_hours():
    assert weather_at(parse_series(payload()), at(14, 30)).wind_mph == pytest.approx(25.0)


def test_precip_is_centred_on_its_hour():
    s = parse_series(payload())
    # The 15:00 value covers 14:00-15:00, so at 14:30 it applies in full.
    assert weather_at(s, at(14, 30)).snow_in_hr == pytest.approx(1.0)
    assert weather_at(s, at(14, 0)).snow_in_hr == pytest.approx(0.5)
    assert weather_at(s, at(13, 30)).snow_in_hr == pytest.approx(0.0)


def test_outside_range_clamps():
    s = parse_series(payload())
    assert weather_at(s, at(9)).wind_mph == 20.0
    assert weather_at(s, at(20)).wind_mph == 30.0


def test_missing_value_raises():
    s = Series([T0, T0 + 3600], [10.0, None], [0, 0], [0, 0], [0, 0])
    with pytest.raises(ValueError):
        weather_at(s, at(14, 30))


def test_missing_rain_or_showers_stays_missing():
    s = parse_series(payload(showers=[None, 0.0]))
    assert s.rain[0] is None
