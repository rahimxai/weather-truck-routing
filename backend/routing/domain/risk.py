from dataclasses import replace

from .models import Level, Risk, Weather

# Lower bounds of Moderate, High, Severe and No Travel.
WIND_MPH = (25, 35, 45, 55)
RAIN_IN_HR = (0.10, 0.25, 0.50, 1.00)
SNOW_IN_HR = (0.5, 1.0, 2.0, 3.0)

# Load rules use strict "more than" per the spec, so exactly 30,000 lb is not escalated.
NO_TRAVEL_LOAD_LB = 30_000
SEVERE_LOAD_LB = 40_000


def band(value, cuts, strict_top=False):
    """Level for a value with half-open bands; strict_top makes No Travel `>` instead of `>=`."""
    top = value > cuts[3] if strict_top else value >= cuts[3]
    if top:
        return Level.NO_TRAVEL
    return Level(sum(value >= c for c in cuts[:3]))


def wind_risk(mph, load_lb):
    # Classify the value we display (0.1 mph) so the label never contradicts the number.
    mph = round(mph, 1)
    level = band(mph, WIND_MPH)
    text = f"Wind {mph:.1f} mph"

    if level == Level.SEVERE and load_lb > NO_TRAVEL_LOAD_LB:
        return Level.NO_TRAVEL, f"{text} with {load_lb:,.0f} lb load"
    if level == Level.HIGH and load_lb > SEVERE_LOAD_LB:
        return Level.SEVERE, f"{text} with {load_lb:,.0f} lb load"
    return level, text


def precip_risk(name, in_hr, cuts):
    # Rain and snow above the Severe range are only No Travel when strictly greater (> 1.00, > 3.0).
    in_hr = round(in_hr, 2)
    return band(in_hr, cuts, strict_top=True), f"{name} {in_hr:.2f} in/hr"


def classify(wx: Weather, load_lb: float) -> Risk:
    """Worst of wind (after load rules), rain and snow, with a reason naming what drove it."""
    wind = wind_risk(wx.wind_mph, load_lb)
    rain = precip_risk("Rain", wx.rain_in_hr, RAIN_IN_HR)
    snow = precip_risk("Snow", wx.snow_in_hr, SNOW_IN_HR)

    level = max(wind[0], rain[0], snow[0])
    if level == Level.LOW:
        reason = "Low risk"
    else:
        reason = "; ".join(text for lvl, text in (wind, rain, snow) if lvl == level)
    return Risk(level, reason, wind=wind[0], rain=rain[0], snow=snow[0])


def assess(cps, forecasts, load_lb):
    """Attach each checkpoint's forecast and its risk."""
    return [
        replace(cp, weather=wx, risk=classify(wx, load_lb))
        for cp, wx in zip(cps, forecasts, strict=True)
    ]
