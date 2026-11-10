import logging
import time

import httpx

from ..errors import UpstreamError

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}


def make_client():
    return httpx.Client(timeout=httpx.Timeout(10.0))


def get_json(client, service, url, params, retries=2):
    """GET JSON, retrying timeouts, 429 and 5xx with backoff.

    Errors and logs never include the URL or params: the TomTom key travels in the query string.
    """
    status = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(0.5 * 2 ** (attempt - 1))
        start = time.perf_counter()
        try:
            resp = client.get(url, params=params)
        except httpx.HTTPError as e:
            log.warning("%s %s on attempt %d", service, type(e).__name__, attempt + 1)
            status = None
            continue

        status = resp.status_code
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
