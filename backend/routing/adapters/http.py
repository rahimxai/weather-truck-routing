import logging
import time

import httpx

from ..errors import UpstreamError

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_WAIT_S = 5.0


def make_client():
    return httpx.Client(timeout=httpx.Timeout(10.0))


def backoff(attempt, status=None, retry_after=None):
    """Seconds to wait before retry number `attempt` (1, 2, ...)."""
    if status == 429:
        # Open-Meteo counts calls per minute per IP, and Vercel shares IPs between apps,
        # so a rate limit needs a real pause. Honour Retry-After when it's given in seconds.
        try:
            return min(max(float(retry_after), 1.0), MAX_WAIT_S)
        except (TypeError, ValueError):
            return min(2.0 * attempt, MAX_WAIT_S)
    return 0.5 * 2 ** (attempt - 1)


def get_json(client, service, url, params, retries=2):
    """GET JSON, retrying timeouts, 429 and 5xx with backoff.

    Errors and logs never include the URL or params: the TomTom key travels in the query string.
    """
    status = retry_after = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(backoff(attempt, status, retry_after))
        start = time.perf_counter()
        try:
            resp = client.get(url, params=params)
        except httpx.HTTPError as e:
            log.warning("%s %s on attempt %d", service, type(e).__name__, attempt + 1)
            status = retry_after = None
            continue

        status = resp.status_code
        retry_after = resp.headers.get("Retry-After")
        log.info("%s %d in %.0f ms", service, status, (time.perf_counter() - start) * 1000)
        if status < 400:
            try:
                return resp.json()
            except ValueError:
                raise UpstreamError(service) from None
        if status not in RETRY_STATUS:
            log.warning("%s error body: %s", service, resp.text[:300])
            break
    raise UpstreamError(service, status)
