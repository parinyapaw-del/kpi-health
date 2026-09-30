#!/usr/bin/env python3
"""kpi.py — data pipeline CLI.

  python3 scripts/kpi.py update [--site angthong] [--indicator dspm] [--year 2569] [--refresh]   fetch -> build -> verify
  python3 scripts/kpi.py fetch  ...    API (raw cache reused unless --refresh) -> aggregate cache in data/cache/
  python3 scripts/kpi.py build  ...    cache + Excel -> site/data/<site>/*.json
  python3 scripts/kpi.py verify ...    API-built vs Excel oracle, formulas, identities (offline, from cache)
  python3 scripts/kpi.py lookup        (re)build data/lookup/areas.json
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_lookup, build_site as B, verify as V          # noqa: E402
from scripts.indicators import coverage, dspm                            # noqa: E402


def _years(site, cache_years, arg):
    ys = {int(y) for y in site["years"]} | set(cache_years)
    if arg:
        ys |= {int(y) for y in arg}
    return sorted(ys)


def _cache_years():
    ys = set()
    for ind in ("dspm", "coverage"):
        d = ROOT / "data" / "cache" / ind
        if d.exists():
            ys |= {int(p.name) for p in d.iterdir() if p.name.isdigit()}
    return ys


def _ensure_lookup(refresh=False):
    if refresh or not (ROOT / "data" / "lookup" / "areas.json").exists():
        print("lookup: building data/lookup/areas.json ...")
        build_lookup.build(refresh=refresh)


def do_fetch(site, ctx, indicators, years, refresh):
    for ind in indicators:
        for y in years:
            print(f"[fetch] {ind} {y}")
            try:
                if ind == "dspm":   # all 77 provinces (country/region levels); sequential, ~45 min/year uncached
                    dspm.fetch_all(y, sorted(ctx["prov_region"], key=int), refresh)
                else:
                    coverage.fetch_cache(y, refresh)
            except Exception as e:   # noqa: BLE001
                print(f"  !! fetch failed: {e}")
                return [f"fetch {ind} {y}: {e}"]
    return []


def do_build(site, ctx, indicators, years):
    built = B.build_datasets(site, ctx, indicators, years)
    res = B.write_site(site, ctx, built)
    print(f"[build] wrote {len(res['files'])} files to site/data/{site['site']}/")
    for f, n, asof, src in res["files"]:
        print(f"  {f:<38} rows={n:<4} asOf={asof or '-':<17} {src}")
    return built


def do_verify(site, ctx, indicators, years, built=None, check_written=True):
    print("[verify]")
    if built is None:
        built = B.build_datasets(site, ctx, indicators, years)
    rep = V.run(site, ctx, built, check_written=check_written)
    V.summarize(rep)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["update", "fetch", "build", "verify", "lookup"])
    ap.add_argument("--site", default="angthong")
    ap.add_argument("--indicator", action="append", help="dspm | coverage (repeatable); default = all of the site")
    ap.add_argument("--year", action="append", help="fiscal year BE, e.g. 2569 (repeatable); default = site years")
    ap.add_argument("--refresh", action="store_true", help="ignore raw/lookup caches and hit the network")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.command == "lookup":
        build_lookup.build(refresh=a.refresh)
        print("lookup written")
        return 0
    site = B.load_site(a.site)
    _ensure_lookup()
    ctx = B.make_context(site)
    inds = a.indicator or [i for i in site["indicators"] if i in B.PLUGINS]
    years = _years(site, _cache_years(), a.year) if a.command != "fetch" else \
        sorted({int(y) for y in (a.year or site["years"])})
    if a.command != "fetch" and a.year and a.command == "build":
        pass
    hard = []
    if a.command in ("update", "fetch"):
        hard += do_fetch(site, ctx, inds, years, a.refresh)
        if hard:
            return 2
    built = None
    if a.command in ("update", "build"):
        built = do_build(site, ctx, inds, years)
    if a.command in ("update", "verify"):
        rep = do_verify(site, ctx, inds, years, built)
        hard += rep.errors
    print(f"[done] {a.command}: {len(hard)} hard error(s) in {time.time() - t0:.1f}s")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
