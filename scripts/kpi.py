#!/usr/bin/env python3
"""kpi.py — data pipeline CLI (Phase 2: health region 4 -> 8 provinces -> districts -> subdistricts).

  python3 scripts/kpi.py update [--site angthong] [--indicator dspm] [--year 2569] [--refresh] [--national]
                                 auto-year check -> fetch -> units registry -> build -> verify
  python3 scripts/kpi.py fetch  ...    API -> aggregate cache in data/cache/ (raw cache reused unless --refresh)
                                       DSPM: the 8 drill provinces (+ patch of the national summary);
                                       --national = all 77 provinces -> data/cache/dspm/<year>/provinces.json
  python3 scripts/kpi.py units         update data/lookup/units.json from the MOPH GIS registry (incremental)
  python3 scripts/kpi.py build  ...    cache + Excel -> site/data/<site>/*.json      (offline)
  python3 scripts/kpi.py verify ...    API-built vs Excel oracle, formulas, identities (offline)
  python3 scripts/kpi.py lookup        (re)build data/lookup/areas.json

Exit code: 0 ok · 1 hard verify errors · 2 fetch failed · 3 --fail-test.
Writes data/cache/pipeline_status.json (read by the GitHub Actions workflow).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_lookup, build_site as B, verify as V          # noqa: E402
from scripts.indicators import coverage, dspm                            # noqa: E402
from scripts.loaders import moph_api                                     # noqa: E402

STATUS = ROOT / "data" / "cache" / "pipeline_status.json"


def _years(site, arg):
    ys = {int(y) for y in site["years"]}
    if arg:
        ys |= {int(y) for y in arg}
    return sorted(ys)


def _ensure_lookup():
    if not (ROOT / "data" / "lookup" / "areas.json").exists():
        print("lookup: building data/lookup/areas.json ...")
        build_lookup.build()


# ------------------------------------------------------------------ auto-year (spec §7.3)
def check_new_year(site, ctx, log=print) -> list[int]:
    """Probe the API for fiscal year max(years)+1; when either table has rows, add the year to the site config
    (currentYear = new year, no target -> the web shows 'ยังไม่กำหนด'). Returns the years added."""
    if not site.get("autoYear"):
        return []
    nxt = max(int(y) for y in site["years"]) + 1
    probe_prov = ctx["drill_provinces"][0] if ctx["drill_provinces"] else "15"
    found = {}
    for name, fn in (("coverage", lambda: moph_api.probe(coverage.TABLE, nxt)),
                     ("dspm", lambda: moph_api.probe(dspm.TABLE, nxt, probe_prov))):
        try:
            found[name] = fn()
        except moph_api.ApiError as e:
            log(f"  auto-year: probe {name} {nxt} failed ({str(e)[:120]}) - skipped")
            found[name] = 0
    log(f"  auto-year: {nxt} rows coverage={found['coverage']} dspm({probe_prov})={found['dspm']}")
    if not any(found.values()):
        return []
    site["years"] = sorted({int(y) for y in site["years"]} | {nxt})
    site["currentYear"] = nxt
    B.save_site(site)
    log(f"  auto-year: fiscal year {nxt} has data -> added to sites/{site['site']}.json (targets not set)")
    return [nxt]


# ------------------------------------------------------------------ steps
def do_fetch(site, ctx, indicators, years, refresh, national, log=print):
    for ind in indicators:
        for y in years:
            log(f"[fetch] {ind} {y}{' (national)' if national and ind == 'dspm' else ''}")
            try:
                if ind == "dspm":
                    drill = ctx["drill_provinces"]
                    if national:
                        # all 77 provinces, sequential (~45 min uncached), then the committed national summary
                        dspm.fetch_all(y, sorted(ctx["prov_region"], key=int), refresh, log=log)
                    else:
                        dspm.fetch_provinces(y, drill, refresh, log=log)
                        if dspm.update_summary(y, drill, log=log) is None:
                            log(f"  !! no national summary for {y}: run  kpi.py fetch --national --year {y}")
                            return [f"fetch dspm {y}: national summary missing (run --national)"]
                else:
                    coverage.fetch_cache(y, refresh, log=log)
            except Exception as e:   # noqa: BLE001
                log(f"  !! fetch failed: {e}")
                return [f"fetch {ind} {y}: {e}"]
    return []


def hospcodes_in_caches(ctx, years) -> dict:
    """Every DSPM hospcode of the drill provinces (all years) with its target by areacode6 (fallback info)."""
    out: dict = {}
    for y in years:
        for p in ctx["drill_provinces"]:
            c = dspm.load_cache(y, p)
            if c is None:
                continue
            for h, u in dspm.unit_areas(c).items():
                o = out.setdefault(h, {"target": 0, "areas": {}})
                o["target"] += u["target"]
                for a6, t in u["areas"].items():
                    o["areas"][a6] = o["areas"].get(a6, 0) + t
    return out


def do_units(ctx, years, refresh=False, log=print):
    codes = hospcodes_in_caches(ctx, years)
    log(f"[units] {len(codes)} hospcodes in the DSPM caches of {len(ctx['drill_provinces'])} provinces")
    return build_lookup.units(codes, refresh=refresh, log=log)


def do_build(site, ctx, indicators, years, log=print):
    built = B.build_datasets(site, ctx, indicators, years)
    res = B.write_site(site, ctx, built)
    log(f"[build] wrote {len(res['files'])} files to site/data/{site['site']}/")
    by_level: dict = {}
    for f, n, asof, src in res["files"]:
        parts = f.split("_")
        by_level.setdefault("_".join(parts[:3]) if len(parts) >= 4 else f, []).append((f, n, asof))
    for k, fs in by_level.items():
        if len(fs) <= 2:
            for f, n, asof in fs:
                log(f"  {f:<38} rows={n:<4} asOf={asof or '-'}")
        else:
            log(f"  {k}_*  x{len(fs)} files, rows {min(n for _, n, _ in fs)}-{max(n for _, n, _ in fs)}")
    return built, res


def do_verify(site, ctx, indicators, years, built=None, check_written=True, log=print):
    log("[verify]")
    if built is None:
        built = B.build_datasets(site, ctx, indicators, years)
    rep = V.run(site, ctx, built, check_written=check_written)
    V.summarize(rep)
    return rep


def write_status(**kw):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    kw["ranAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(kw, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["update", "fetch", "units", "build", "verify", "lookup"])
    ap.add_argument("--site", default="angthong")
    ap.add_argument("--indicator", action="append", help="dspm | coverage (repeatable); default = all of the site")
    ap.add_argument("--year", action="append", help="fiscal year BE, e.g. 2569 (repeatable); default = site years")
    ap.add_argument("--refresh", action="store_true", help="ignore raw/lookup caches and hit the network")
    ap.add_argument("--national", action="store_true",
                    help="DSPM: fetch all 77 provinces and rewrite the national summary (weekly job, ~45 min)")
    ap.add_argument("--no-auto-year", action="store_true", help="skip the fiscal-year probe (spec §7.3)")
    ap.add_argument("--fail-test", action="store_true", help="exit 3 immediately (tests the failure path of the workflow)")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.fail_test:
        print("--fail-test: simulated pipeline failure")
        write_status(command=a.command, ok=False, error="fail-test", newYears=[])
        return 3
    if a.command == "lookup":
        build_lookup.build(refresh=a.refresh)
        print("lookup written")
        return 0
    site = B.load_site(a.site)
    _ensure_lookup()
    ctx = B.make_context(site)
    inds = a.indicator or [i for i in site["indicators"] if i in B.PLUGINS]
    new_years: list[int] = []
    if a.command in ("update", "fetch") and not a.no_auto_year and not a.year:
        new_years = check_new_year(site, ctx)
        if new_years:
            ctx = B.make_context(site)
    years = _years(site, a.year)
    hard = []
    try:
        if a.command in ("update", "fetch"):
            hard += do_fetch(site, ctx, inds, years, a.refresh, a.national)
            if hard:
                write_status(command=a.command, ok=False, error=hard, newYears=new_years, years=years)
                return 2
        if a.command in ("update", "fetch", "units"):
            do_units(ctx, years, refresh=a.refresh and a.command == "units")
        built = None
        files = None
        if a.command in ("update", "build"):
            built, files = do_build(site, ctx, inds, years)
        rep = None
        if a.command in ("update", "verify"):
            rep = do_verify(site, ctx, inds, years, built)
            hard += rep.errors
    except (B.BuildError, RuntimeError) as e:
        print(f"  !! {e}")
        write_status(command=a.command, ok=False, error=str(e), newYears=new_years, years=years)
        return 1
    print(f"[done] {a.command}: {len(hard)} hard error(s) in {time.time() - t0:.1f}s")
    write_status(command=a.command, ok=not hard, years=years, newYears=new_years,
                 hardErrors=hard[:50], warnings=len(rep.warnings) if rep else None,
                 filesWritten=len(files["files"]) if files else None, national=a.national)
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
