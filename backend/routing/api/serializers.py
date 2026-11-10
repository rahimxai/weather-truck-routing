from datetime import UTC, timedelta

from django.utils import timezone
from rest_framework import serializers

from ..domain.checkpoints import risk_segments
from ..domain.geometry import haversine_mi, simplify
from ..domain.heatmap import HOURS
from ..domain.scenarios import SCENARIOS

MAX_LOAD_LB = 80_000
MAX_DAYS_AHEAD = 7
# Clients and servers disagree on "now" by a little; don't reject a departure for that.
PAST_GRACE = timedelta(minutes=10)

# Degrees for Douglas-Peucker: ~50 m keeps risk segments faithful on screen,
# ~500 m is plenty for the overview line the heatmap request uses.
SEGMENT_TOL = 0.0005
LINE_TOL = 0.005
MAX_LINE_POINTS = 5000


def check_departure(value):
    now = timezone.now()
    if value < now - PAST_GRACE:
        raise serializers.ValidationError("Departure is in the past. Pick a time from now on.")
    if value > now + timedelta(days=MAX_DAYS_AHEAD):
        raise serializers.ValidationError(
            f"Forecasts only go {MAX_DAYS_AHEAD} days out. Pick an earlier departure."
        )
    return value.astimezone(UTC)


class PlaceSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(max_length=200, required=False, allow_blank=True)


class PlanRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50], default=25)
    scenario = serializers.ChoiceField(choices=list(SCENARIOS), allow_null=True, default=None)

    def validate_departure(self, value):
        # The router rejects past departures, so a few minutes ago becomes now.
        return max(check_departure(value), timezone.now())

    def validate(self, data):
        a, b = data["origin"], data["destination"]
        if haversine_mi((a["lon"], a["lat"]), (b["lon"], b["lat"])) < 0.5:
            raise serializers.ValidationError("Origin and destination are the same place.")
        return data


class LineField(serializers.Field):
    """A [[lon, lat], ...] line. Checked in plain Python: nested DRF fields are slow per point."""

    def to_internal_value(self, data):
        try:
            pts = [(float(lon), float(lat)) for lon, lat in data]
        except (TypeError, ValueError):
            raise serializers.ValidationError("Each point must be [lon, lat].") from None
        if not 2 <= len(pts) <= MAX_LINE_POINTS:
            raise serializers.ValidationError(f"A route needs 2 to {MAX_LINE_POINTS} points.")
        if not all(-180 <= x <= 180 and -90 <= y <= 90 for x, y in pts):
            raise serializers.ValidationError("Coordinates are out of range.")
        return pts


class HeatmapRequestSerializer(serializers.Serializer):
    routes = serializers.ListField(child=LineField(), min_length=1, max_length=3)
    departure = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)
    scenario = serializers.ChoiceField(choices=list(SCENARIOS), allow_null=True, default=None)

    def validate_departure(self, value):
        # Not clamped to now: frame 0 must line up with the plan's own departure.
        return check_departure(value)


def iso(dt):
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def path(pts, tolerance):
    return [[round(x, 5), round(y, 5)] for x, y in simplify(pts, tolerance)]


def checkpoint_payload(cp):
    wx, risk = cp.weather, cp.risk
    return {
        "mile": round(cp.mile, 1),
        "lat": round(cp.lat, 5),
        "lon": round(cp.lon, 5),
        "eta": iso(cp.eta),
        "covered_mi": round(cp.covered_mi, 2),
        "weather": {
            "wind_mph": round(wx.wind_mph, 1),
            "gust_mph": round(wx.gust_mph, 1),
            "rain_in_hr": round(wx.rain_in_hr, 2),
            "snow_in_hr": round(wx.snow_in_hr, 2),
        },
        "level": risk.level.name,
        "reason": risk.reason,
        "levels": {"wind": risk.wind.name, "rain": risk.rain.name, "snow": risk.snow.name},
    }


def route_payload(sr, rank):
    route, cps = sr.route, sr.checkpoints
    return {
        "id": route.id,
        "rank": rank,
        "distance_mi": round(route.distance_mi, 1),
        "duration_s": round(route.duration_s),
        "departure": iso(cps[0].eta),
        "arrival": iso(cps[-1].eta),
        "geometry": path(route.geometry, LINE_TOL),
        "segments": [
            {"level": level.name, "path": path(pts, SEGMENT_TOL)}
            for level, pts in risk_segments(route, cps)
        ],
        "checkpoints": [checkpoint_payload(cp) for cp in cps],
        "summary": {
            "miles_by_level": {
                level.name: round(mi, 1) for level, mi in sr.summary.miles_by_level.items()
            },
            "avg_risk": round(sr.summary.avg_risk, 2),
        },
    }


def plan_payload(rec, warnings, scenario=None):
    rank = {sr.route.id: i + 1 for i, sr in enumerate(rec.ranked)}
    routes = sorted(rec.ranked, key=lambda sr: sr.route.id)
    return {
        "routes": [route_payload(sr, rank[sr.route.id]) for sr in routes],
        "recommended_id": rec.best.route.id,
        "explanation": rec.explanation,
        "warnings": warnings,
        "scenario": scenario,
    }


def heatmap_payload(cells, cell_deg, departure, frames, scenario=None):
    return {
        "points": [list(c) for c in cells],
        "cell_deg": cell_deg,
        "hours": HOURS,
        "start": iso(departure),
        "frames": frames,
        "scenario": scenario,
    }
