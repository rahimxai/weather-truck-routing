from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, timedelta

from ..domain.forecast import parse_series
from ..errors import ForecastUnavailable, UpstreamError
from .http import get_json, make_client

URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
BATCH = 50


def _hour(dt):
    return dt.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def forecasts(points, start, end):
    """Hourly forecast Series for each (lon, lat), covering start..end, in parallel batches."""
    if not points:
        return []
    # One spare hour each side so interpolation always has both neighbours.
    params = {
        "hourly": HOURLY,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timeformat": "unixtime",
        "timezone": "GMT",
        "start_hour": (_hour(start) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        "end_hour": (_hour(end) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
    }

    def fetch(batch):
        query = {
            **params,
            "latitude": ",".join(f"{lat:.4f}" for _, lat in batch),
            "longitude": ",".join(f"{lon:.4f}" for lon, _ in batch),
        }
        try:
            with make_client() as client:
                data = get_json(client, "Open-Meteo", URL, query)
        except UpstreamError as e:
            if e.upstream_status == 400:  # e.g. the trip runs past the forecast range
                raise ForecastUnavailable() from None
            raise
        data = data if isinstance(data, list) else [data]  # one location comes back bare
        if len(data) != len(batch):
            raise UpstreamError("Open-Meteo")
        return data

    batches = [points[i : i + BATCH] for i in range(0, len(points), BATCH)]
    with ThreadPoolExecutor(min(4, len(batches))) as pool:
        payloads = [p for chunk in pool.map(fetch, batches) for p in chunk]
    try:
        return [parse_series(p) for p in payloads]
    except (KeyError, TypeError, ValueError) as e:
        raise UpstreamError("Open-Meteo") from e
