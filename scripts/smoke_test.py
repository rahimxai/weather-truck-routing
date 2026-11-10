"""Check a deployed copy end to end: python scripts/smoke_test.py https://your-app.vercel.app

Uses the real TomTom and Open-Meteo through your deployment, so it spends a few API calls.
"""

import base64
import sys
import time
from datetime import UTC, datetime, timedelta

import httpx

CHICAGO = {"lat": 41.8781, "lon": -87.6298, "label": "Chicago, IL"}
DENVER = {"lat": 39.7392, "lon": -104.9903, "label": "Denver, CO"}

failures = []


def check(ok, what, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {what}{f' ({detail})' if detail else ''}")
    if not ok:
        failures.append(what)
    return ok


def call(client, method, path, **kw):
    started = time.perf_counter()
    resp = client.request(method, path, **kw)
    return resp, (time.perf_counter() - started) * 1000


def plan_body(load_lb, scenario=None):
    departure = (datetime.now(UTC) + timedelta(minutes=30)).isoformat(timespec="seconds")
    return {
        "origin": CHICAGO,
        "destination": DENVER,
        "departure": departure,
        "load_lb": load_lb,
        "interval_mi": 25,
        "scenario": scenario,
    }


def check_plan(data):
    routes = data.get("routes", [])
    check(1 <= len(routes) <= 3, "plan has routes", f"{len(routes)} routes")
    check(len(routes) == 3 or bool(data["warnings"]), "fewer than 3 routes comes with a warning")
    for r in routes:
        cps = r["checkpoints"]
        covered = sum(cp["covered_mi"] for cp in cps)
        check(
            abs(covered - r["distance_mi"]) < 0.5,
            f"route {r['id']}: coverage adds up",
            f"{covered:.1f} of {r['distance_mi']} mi, {len(cps)} checkpoints",
        )
        check(cps[0]["mile"] == 0 and cps[-1]["mile"] == r["distance_mi"], f"route {r['id']}: ends")
    check(bool(data.get("explanation")), "explanation", data.get("explanation", ""))


def main(base):
    with httpx.Client(base_url=base.rstrip("/"), timeout=120, follow_redirects=True) as client:
        print(f"Checking {base}\n")

        resp, ms = call(client, "GET", "/")
        check(
            resp.status_code == 200 and 'id="root"' in resp.text, "app page loads", f"{ms:.0f} ms"
        )

        resp, ms = call(client, "GET", "/api/health")
        health = resp.json() if resp.status_code == 200 else {}
        check(health.get("status") == "ok", "api health", f"{ms:.0f} ms")
        check(health.get("tomtom_key") is True, "TomTom key is set on the server")

        resp, ms = call(client, "GET", "/api/geocode", params={"q": "Denver"})
        found = resp.json() if resp.status_code == 200 else []
        check(
            bool(found), "geocode finds Denver", f"{found[0]['label'] if found else resp.text[:80]}"
        )

        resp, ms = call(client, "GET", "/api/nope")
        check(resp.status_code == 404 and "error" in resp.json(), "unknown API path is a JSON 404")

        print("\nLive plan, Chicago to Denver at 42,000 lb")
        resp, ms = call(client, "POST", "/api/plan", json=plan_body(42_000))
        if not check(resp.status_code == 200, "plan", f"{resp.status_code} in {ms:.0f} ms"):
            print("   ", resp.text[:300])
            return
        data = resp.json()
        check_plan(data)
        check(data["scenario"] is None, "live plan is not labelled as demo")

        resp, ms = call(
            client,
            "POST",
            "/api/heatmap",
            json={
                "routes": [r["geometry"] for r in data["routes"]],
                "departure": data["routes"][0]["departure"],
                "load_lb": 42_000,
                "scenario": None,
            },
        )
        if check(resp.status_code == 200, "heatmap", f"{resp.status_code} in {ms:.0f} ms"):
            heat = resp.json()
            n = len(heat["points"])
            sizes = {m: len(base64.b64decode(f)) for m, f in heat["frames"].items()}
            check(all(s == 49 * n for s in sizes.values()), "heatmap has 49 frames", f"{n} cells")

        print("\nDemo weather: the same trip at 25,000 and 45,000 lb")
        picks = {}
        for load in (25_000, 45_000):
            resp, ms = call(client, "POST", "/api/plan", json=plan_body(load, "winter_storm"))
            if check(resp.status_code == 200, f"demo plan at {load:,} lb", f"{ms:.0f} ms"):
                demo = resp.json()
                picks[load] = demo["recommended_id"]
                check(demo["scenario"] == "winter_storm", "demo plan is labelled")
                print(f"       {demo['explanation']}")
        if len(picks) == 2:
            check(
                picks[25_000] != picks[45_000],
                "recommendation changes with load",
                f"{picks[25_000]} at 25,000 lb, {picks[45_000]} at 45,000 lb",
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/smoke_test.py https://your-app.vercel.app")
    main(sys.argv[1])
    print(f"\n{'All checks passed.' if not failures else f'{len(failures)} failed: {failures}'}")
    sys.exit(1 if failures else 0)
