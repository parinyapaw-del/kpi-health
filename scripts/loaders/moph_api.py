"""MOPH Open Data API loader (POST https://opendata.moph.go.th/api/report_data).

- requests only (python.org Python has no root certs -> urllib fails); certifi bundle is used.
- one request at a time, timeout 120 s, retry 3x with backoff 5/15/45 s (retry(), also used by the GIS registry)
- HTTP 429 (NestJS ThrottlerException): the server budget is 10 requests / 60 s (strict 5 / 60 s) and the counter is
  shared with other traffic reaching the API through the same path (measured 2026-10-10: our own ~11 requests per run,
  30-45 s apart, still saw random 429s from GitHub runners). A 429 is therefore retried on its own, longer budget
  (THROTTLE_BACKOFF) and each wait is at least `x-ratelimit-reset` + 1 s so a fresh window has opened.
- 0 rows -> EmptyResult (subclass of ApiError): callers treat it as 'not available yet', not as an outage
- default server limit is 1000 -> we send limit=20000 and loop over `offset` until `total` is reached
- raw responses are cached in data/raw_api/<table>/<year>/<provcode|all>.json (gitignored) and
  reused on later runs unless refresh=True
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import certifi
import requests

URL = "https://opendata.moph.go.th/api/report_data"
LIMIT = 20000
TIMEOUT = 120
BACKOFF = (5, 15, 45)
THROTTLE_BACKOFF = (61, 61, 61, 61, 61)  # HTTP 429 only: wait out the 60 s window, up to 6 attempts (~5 min)

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw_api"


class ApiError(RuntimeError):
    pass


class EmptyResult(ApiError):
    """The API answered with 0 rows (year / province not available yet) - nothing cached."""


class Retry(Exception):
    """Raised inside a retry() callable for a retryable failure (e.g. HTTP 5xx); the message is logged.
    throttled=True (HTTP 429) counts against the separate, longer throttle budget of retry(); wait = minimum seconds
    to sleep before the next attempt (the server's x-ratelimit-reset / Retry-After)."""

    def __init__(self, message: str, wait: float | None = None, throttled: bool = False):
        super().__init__(message)
        self.wait = wait
        self.throttled = throttled


class RetryExhausted(RuntimeError):
    pass


def retry(fn, delays=BACKOFF, what="request", log=print, throttle_delays=()):
    """Call fn() until it returns; network errors (requests.RequestException), bad JSON (ValueError) and Retry are
    retried after delays[0], delays[1], ... seconds (len(delays)+1 attempts in total). A Retry with throttled=True
    is retried on its own budget `throttle_delays` instead (len(throttle_delays) extra attempts), sleeping at least
    Retry.wait seconds. Any other exception propagates at once. Raises RetryExhausted with the last failure when the
    budget that applies to the failure is used up.
    Shared by the Open Data API (_post) and the GIS registry (build_lookup._gis)."""
    last = None
    used = {False: 0, True: 0}            # attempts spent per budget (normal / throttled)
    budget = {False: delays, True: throttle_delays}
    while True:
        try:
            return fn()
        except Retry as e:
            last, throttled, wait = str(e), e.throttled, e.wait
        except (requests.RequestException, ValueError) as e:  # timeouts, conn errors, bad json
            last, throttled, wait = f"{type(e).__name__}: {e}", False, None
        n = used[throttled]
        if n >= len(budget[throttled]):
            raise RetryExhausted(f"{what} failed after {used[False] + used[True] + 1} attempts: {last}")
        delay = max(budget[throttled][n], wait or 0)
        used[throttled] = n + 1
        kind = "throttled" if throttled else "failed"
        log(f"    ! {what} {kind} ({last}); retry {n + 1}/{len(budget[throttled])} in {delay:.0f}s")
        time.sleep(delay)


def _post(body: dict) -> dict:
    def once():
        r = requests.post(URL, json=body, timeout=TIMEOUT, verify=certifi.where(),
                          headers={"Content-Type": "application/json"})
        if r.status_code in (200, 201):  # API answers 201 on success
            return r.json()
        if r.status_code == 429:  # shared throttle budget (see module docstring): wait for the window to reset
            reset = r.headers.get("x-ratelimit-reset") or r.headers.get("Retry-After")
            try:
                wait = float(reset) + 1
            except (TypeError, ValueError):
                wait = None
            raise Retry(f"HTTP 429: {r.text[:120]}", wait=wait, throttled=True)
        raise Retry(f"HTTP {r.status_code}: {r.text[:200]}")
    try:
        return retry(once, BACKOFF, "request", throttle_delays=THROTTLE_BACKOFF)
    except RetryExhausted as e:
        raise ApiError(f"API {e} body={body}") from None


def fetch_rows(body: dict) -> tuple[list[dict], int]:
    """Fetch every row for `body` (offset loop until total reached). Returns (rows, total)."""
    rows: list[dict] = []
    offset = 0
    total = None
    while True:
        b = dict(body, limit=LIMIT)
        if offset:
            b["offset"] = offset
        resp = _post(b)
        data = resp.get("data") or []
        total = int(resp.get("total") or len(data))
        rows.extend(data)
        offset += len(data)
        if not data or offset >= total:
            break
    return rows, total


def probe(table: str, year: int, province: str | None = None) -> int:
    """Row count the API reports for (table, year[, province]) — one request with limit=1, nothing cached.
    Used by the auto-year check (spec §7.3). Returns 0 when the year is not available."""
    body = {"tableName": table, "year": str(year), "type": "json", "limit": 1}
    if province:
        body["province"] = str(province)
    resp = _post(body)
    return int(resp.get("total") or len(resp.get("data") or []))


def raw_path(table: str, year: int, scope: str) -> Path:
    return RAW_DIR / table / str(year) / f"{scope}.json"


def get_raw(table: str, year: int, province: str | None = None, refresh: bool = False,
            log=print) -> dict:
    """Return {"table","year","province","fetchedAt","total","data":[...]} using the raw cache."""
    scope = province or "all"
    p = raw_path(table, year, scope)
    if p.exists() and not refresh:
        log(f"  raw cache hit  {p.relative_to(ROOT)}")
        return json.loads(p.read_text(encoding="utf-8"))
    body = {"tableName": table, "year": str(year), "type": "json"}
    if province:
        body["province"] = str(province)
    log(f"  API fetch      {table} year={year} province={province or '-'} ...")
    t0 = time.time()
    rows, total = fetch_rows(body)
    log(f"    -> {len(rows)} rows (total={total}) in {time.time() - t0:.1f}s")
    if len(rows) != total:
        raise ApiError(f"row count {len(rows)} != total {total} for {body}")
    if not rows:
        raise EmptyResult(f"API returned 0 rows for {body} (year not available yet?) - nothing cached")
    out = {"table": table, "year": year, "province": province, "total": total,
           "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "data": rows}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out
