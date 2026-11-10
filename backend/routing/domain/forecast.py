from bisect import bisect_left
from dataclasses import dataclass

from .models import Weather
from .units import cm_to_in, kmh_to_mph, mm_to_in

# Convert whatever unit the payload reports, so a changed default can't skew the bands.
SPEED = {"mp/h": float, "mph": float, "km/h": kmh_to_mph}
RAIN = {"inch": float, "mm": mm_to_in}
SNOW = {"inch": float, "cm": cm_to_in}


@dataclass(frozen=True)
class Series:
    """One location's hourly forecast, already in mph and in/hr."""

    times: list[int]  # unix seconds, UTC
    wind: list[float]
    gust: list[float]
    rain: list[float]
    snow: list[float]


def _convert(values, unit, table, name):
    if unit not in table:
        raise ValueError(f"Unexpected unit {unit!r} for {name}")
    fn = table[unit]
    return [None if v is None else fn(v) for v in values]


def parse_series(payload):
    """Open-Meteo location payload (timeformat=unixtime) to a Series."""
    hourly, units = payload["hourly"], payload["hourly_units"]
    rain = _convert(hourly["rain"], units["rain"], RAIN, "rain")
    showers = _convert(hourly["showers"], units["showers"], RAIN, "showers")
    return Series(
        times=hourly["time"],
        wind=_convert(hourly["wind_speed_10m"], units["wind_speed_10m"], SPEED, "wind"),
        gust=_convert(hourly["wind_gusts_10m"], units["wind_gusts_10m"], SPEED, "gusts"),
        # Liquid only: "rain" is large-scale rain, "showers" is convective. Snow stays separate.
        rain=[
            None if r is None or s is None else r + s for r, s in zip(rain, showers, strict=True)
        ],
        snow=_convert(hourly["snowfall"], units["snowfall"], SNOW, "snowfall"),
    )


def _lerp(times, values, t):
    if t <= times[0]:
        i = j = 0
    elif t >= times[-1]:
        i = j = len(times) - 1
    else:
        j = bisect_left(times, t)
        i = j - 1
    if values[i] is None or values[j] is None:
        raise ValueError("Forecast is missing values for this time")
    if i == j:
        return values[i]
    return values[i] + (values[j] - values[i]) * (t - times[i]) / (times[j] - times[i])


def weather_at(series: Series, when) -> Weather:
    """Forecast at an exact time, interpolated between hours."""
    t = when.timestamp()
    # Wind speed is instantaneous at each hour. Gusts, rain and snow describe the
    # preceding hour, so treat them as centred half an hour earlier.
    mid = [s - 1800 for s in series.times]
    return Weather(
        wind_mph=_lerp(series.times, series.wind, t),
        gust_mph=_lerp(mid, series.gust, t),
        rain_in_hr=_lerp(mid, series.rain, t),
        snow_in_hr=_lerp(mid, series.snow, t),
    )
