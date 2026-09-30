#!/usr/bin/env python3
"""Fetch the DSPM aggregate cache for every province (one-off backfill; resumable).

  python3 scripts/fetch_all_dspm.py [--year 2569 ...] [--workers 3] [--refresh]

Writes data/cache/dspm/<year>/<provcode>.json via dspm.fetch_cache (same format as the pipeline).
A province whose cache already exists is skipped unless --refresh. Failures are listed at the end
(re-run to retry just those). Region 4 provinces are fetched first.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.indicators import dspm  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", action="append", type=int)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    site = json.loads((ROOT / "sites" / "angthong.json").read_text(encoding="utf-8"))
    years = a.year or [int(y) for y in site["years"]]
    provs = json.loads((ROOT / "data" / "lookup" / "areas.json").read_text(encoding="utf-8"))["provinces"]
    order = sorted(provs, key=lambda c: (provs[c]["region"] != 4, int(c)))
    jobs = [(y, p) for y in sorted(years, reverse=True) for p in order
            if a.refresh or not dspm.cache_path(y, p).exists()]
    print(f"{len(jobs)} province-years to fetch ({len(years)} years x {len(order)} provinces, "
          f"workers={a.workers})", flush=True)

    def run(y, p):
        lines = []
        dspm.fetch_cache(y, p, a.refresh, log=lines.append)
        return lines

    t0, done, failed = time.time(), 0, []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run, y, p): (y, p) for y, p in jobs}
        for f in as_completed(futs):
            y, p = futs[f]
            done += 1
            try:
                f.result()
                print(f"[{done}/{len(jobs)}] ok   {y} {p} {provs[p]['name']}  ({time.time() - t0:.0f}s)", flush=True)
            except Exception as e:  # noqa: BLE001
                failed.append((y, p, str(e)[:200]))
                print(f"[{done}/{len(jobs)}] FAIL {y} {p} {provs[p]['name']}: {str(e)[:200]}", flush=True)
    print(f"done in {time.time() - t0:.0f}s; {len(failed)} failed", flush=True)
    for y, p, e in failed:
        print(f"  FAIL {y} {p}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
