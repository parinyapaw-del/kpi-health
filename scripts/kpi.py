#!/usr/bin/env python3
"""kpi.py — data pipeline CLI (Phase 2: health region 4 -> 8 provinces -> districts -> subdistricts).

  python3 scripts/kpi.py update [--site angthong] [--indicator dspm] [--year 2569] [--refresh] [--national]
                                 auto-year probe -> fetch -> units registry -> build -> verify
  python3 scripts/kpi.py fetch  ...    API -> aggregate cache in data/cache/ (raw cache reused unless --refresh)
                                       which years / provinces are fetched: refresh_scope() (refresh policy)
  python3 scripts/kpi.py units         update data/lookup/units.json from the MOPH GIS registry (incremental)
  python3 scripts/kpi.py build  ...    cache + Excel -> site/data/<site>/*.json      (offline)
  python3 scripts/kpi.py verify ...    API-built vs Excel oracle, formulas, identities (offline)
  python3 scripts/kpi.py lookup        (re)build data/lookup/areas.json

--year Y (repeatable) restricts the FETCH to those years; build/verify still cover the site years + Y.

New fiscal year (sites/<site>.json "autoYear": true; spec §7.3):
  * update/fetch without --year probe the API for max(years)+1 (Coverage country-wide + DSPM one province).
    The probe never changes the config.
  * daily run (no --national): a year with DSPM rows is NOT fetched -> pipeline_status.json "pendingYears": [Y];
    the workflow then dispatches itself with national=true, year=Y.
  * national run (--national, or --national --year Y for a year not in the config): DSPM of Y for all 77 provinces
    (-> data/cache/dspm/Y/provinces.json), Coverage of Y (0 rows = warning), units; only once the DSPM national
    summary of Y exists is Y added to "years" (currentYear = Y); a missing target of Y is copied from the previous
    year ("inheritedFrom") and reported as "newYears": [Y] + "inheritedTargets" (workflow -> Issue "กรุณาตรวจเป้าหมาย"). A failed DSPM fetch of Y = hard error, config untouched; no DSPM rows at all = warning.

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
REFRESH_YEARS = 2          # default of sites/<site>.json "refreshYears": currentYear + the year before


def _ensure_lookup():
    if not (ROOT / "data" / "lookup" / "areas.json").exists():
        print("lookup: building data/lookup/areas.json ...")
        build_lookup.build()


def _probe_province(ctx) -> str:
    drill = ctx["drill_provinces"]
    return "15" if "15" in drill or not drill else drill[0]


# ------------------------------------------------------------------ auto-year (spec §7.3)
def check_new_year(site, ctx, log=print) -> list[int]:
    """Probe the API for fiscal year max(years)+1 (Coverage country-wide + DSPM of one drill province, "15" when it
    is a drill province). Returns [year] when DSPM has rows (the year can only be published once its DSPM national
    summary exists), else []. Never modifies the site config: adding the year is done by the national run after a
    successful fetch (main)."""
    if not site.get("autoYear"):
        return []
    nxt = max(int(y) for y in site["years"]) + 1
    probe_prov = _probe_province(ctx)
    found = {}
    for name, fn in (("coverage", lambda: moph_api.probe(coverage.TABLE, nxt)),
                     ("dspm", lambda: moph_api.probe(dspm.TABLE, nxt, probe_prov))):
        try:
            found[name] = fn()
        except moph_api.ApiError as e:
            log(f"  auto-year: probe {name} {nxt} failed ({str(e)[:120]}) - skipped")
            found[name] = 0
    log(f"  auto-year: {nxt} rows coverage={found['coverage']} dspm({probe_prov})={found['dspm']}")
    if found["dspm"]:
        return [nxt]
    if found["coverage"]:
        log(f"  auto-year: {nxt} has Coverage rows but no DSPM rows yet -> wait (a year is added with its DSPM)")
    return []


# ------------------------------------------------------------------ refresh policy
def refresh_scope(site, years, national, explicit=()) -> dict[int, str]:
    """Fetch mode of each year in `years` (all of them already in the config, or given with --year):

      "national"  DSPM all 77 provinces (rewrites data/cache/dspm/<y>/provinces.json) + Coverage
      "drill"     DSPM the drill provinces (+ patch of provinces.json) + Coverage
      "cached"    closed year: nothing is fetched while its committed caches exist; a missing cache is fetched
                  (never refreshed)

    Default years: the newest `refreshYears` years ending at currentYear (sites/<site>.json, default 2 =
    currentYear and currentYear-1) are "drill" — currentYear is "national" on a --national run (weekly) —
    older years are "cached" (their data no longer changes; the CI checkout has their committed caches).
    Years given with --year (`explicit`) are fetched as asked: "national" with --national, else "drill".
    main() passes national=False when the same run fetches a new fiscal year nationally (see there)."""
    cur = int(site["currentYear"])
    window = {cur - i for i in range(int(site.get("refreshYears", REFRESH_YEARS)))}
    plan = {}
    for y in years:
        if y in explicit:
            plan[y] = "national" if national else "drill"
        elif y in window:
            plan[y] = "national" if national and y == cur else "drill"
        else:
            plan[y] = "cached"
    return plan


# ------------------------------------------------------------------ steps
def do_fetch(ctx, indicators, plan, refresh, log=print) -> tuple[list[str], list[str]]:
    """Fetch every (indicator, year) of `plan` (refresh_scope). Errors are collected per (indicator, year):
    returns (hard, warnings). Hard = a DSPM fetch failure; Coverage with 0 rows (year not published yet) is a
    warning, any other Coverage failure is hard."""
    hard, warns = [], []
    drill = ctx["drill_provinces"]
    all_provs = sorted(ctx["prov_region"], key=int)

    def warn(msg):
        log(f"  WARN {msg}")
        warns.append(msg)

    for ind in indicators:
        for y, mode in sorted(plan.items()):
            log(f"[fetch] {ind} {y} ({mode})")
            try:
                if ind == "dspm":
                    if mode == "national":
                        if dspm.fetch_all(y, all_provs, refresh, log=log) is None:
                            warn(f"dspm {y}: no province has data - national summary not written")
                        continue
                    provs = drill
                    if mode == "cached":
                        provs = [p for p in drill if not dspm.cache_path(y, p).exists()]
                        if not provs:
                            log(f"  closed year: committed caches of {len(drill)} provinces kept (not refetched)")
                            continue
                    dspm.fetch_provinces(y, provs, refresh and mode != "cached", log=log)
                    if dspm.update_summary(y, provs, log=log) is None:
                        warn(f"dspm {y}: no national summary {dspm.summary_path(y).relative_to(ROOT)} - "
                             f"country/region levels missing (run kpi.py update --national --year {y})")
                else:
                    if mode == "cached" and coverage.cache_path(y).exists():
                        log("  closed year: committed cache kept (not refetched)")
                        continue
                    coverage.fetch_cache(y, refresh and mode != "cached", log=log)
            except moph_api.EmptyResult as e:
                if ind == "dspm":
                    hard.append(f"fetch dspm {y}: {e}")
                    log(f"  !! fetch failed: {e}")
                else:
                    warn(f"coverage {y}: API has 0 rows (not published yet?) - cache unchanged")
            except Exception as e:   # noqa: BLE001
                log(f"  !! fetch failed: {e}")
                hard.append(f"fetch {ind} {y}: {e}")
    return hard, warns


def fetch_new_year(ctx, indicators, year, refresh, log=print) -> tuple[bool, list[str], list[str]]:
    """National fetch of a fiscal year that is not in the config yet. Returns (available, hard, warnings):
    available = the DSPM national summary of `year` was written. DSPM failure -> hard; DSPM without any row,
    Coverage failure / 0 rows -> warnings."""
    hard, warns = [], []

    def warn(msg):
        log(f"  WARN {msg}")
        warns.append(msg)

    if "dspm" not in indicators:
        warn(f"new year {year}: needs the dspm indicator - skipped")
        return False, hard, warns
    log(f"[fetch] dspm {year} (new year, national: {len(ctx['prov_region'])} provinces)")
    try:
        summ = dspm.fetch_all(year, sorted(ctx["prov_region"], key=int), refresh, log=log)
    except Exception as e:   # noqa: BLE001
        log(f"  !! fetch failed: {e}")
        hard.append(f"fetch dspm {year} (new year): {e}")
        return False, hard, warns
    if summ is None:
        warn(f"new year {year}: DSPM has no rows in any province - year not added")
        return False, hard, warns
    if "coverage" in indicators:
        log(f"[fetch] coverage {year} (new year)")
        try:
            coverage.fetch_cache(year, refresh, log=log)
        except moph_api.EmptyResult:
            warn(f"coverage {year}: API has 0 rows yet - the year is published without Coverage for now")
        except Exception as e:   # noqa: BLE001
            warn(f"coverage {year} (new year): fetch failed ({e}) - retried by the next run")
    return True, hard, warns


def inherit_targets(site, years) -> dict:
    """For every indicator and new year without a target, copy the newest earlier year's target
    (targets[ind][y] = {"value": v, "inheritedFrom": prev}). Returns {year: {ind: value}} of what was copied."""
    out: dict = {}
    targets = site.setdefault("targets", {})
    for ind in site["indicators"]:
        t = targets.setdefault(ind, {})
        for y in years:
            if isinstance(t.get(str(y)), dict) and t[str(y)].get("value") is not None:
                continue
            prev = [int(k) for k, v in t.items() if k.isdigit() and int(k) < y
                    and isinstance(v, dict) and v.get("value") is not None]
            if not prev:
                continue
            src = max(prev)
            t[str(y)] = {"value": t[str(src)]["value"], "inheritedFrom": src}
            out.setdefault(str(y), {})[ind] = t[str(y)]["value"]
    return out


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


def do_verify(site, ctx, indicators, years, built=None, log=print):
    log("[verify]")
    if built is None:
        built = B.build_datasets(site, ctx, indicators, years)
    rep = V.run(site, ctx, built)
    V.summarize(rep, log=log)
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
    ap.add_argument("--year", action="append",
                    help="fiscal year BE, e.g. 2569 (repeatable): fetch ONLY these years (build/verify: site years + "
                         "these); with --national a year not in the config is added after a successful fetch")
    ap.add_argument("--refresh", action="store_true", help="ignore raw/lookup caches and hit the network")
    ap.add_argument("--national", action="store_true",
                    help="DSPM: fetch all 77 provinces of currentYear (+ a new year) and rewrite the national "
                         "summary (weekly job, ~85 min per year)")
    ap.add_argument("--no-auto-year", action="store_true", help="skip the fiscal-year probe (spec §7.3)")
    ap.add_argument("--fail-test", action="store_true", help="exit 3 immediately (tests the failure path of the workflow)")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.fail_test:
        print("--fail-test: simulated pipeline failure")
        write_status(command=a.command, ok=False, error="fail-test", newYears=[], pendingYears=[])
        return 3
    if a.command == "lookup":
        build_lookup.build(refresh=a.refresh)
        print("lookup written")
        return 0
    site = B.load_site(a.site)
    _ensure_lookup()
    ctx = B.make_context(site)
    inds = a.indicator or [i for i in site["indicators"] if i in B.PLUGINS]
    explicit = sorted({int(y) for y in a.year or []})
    years = sorted({int(y) for y in site["years"]} | set(explicit))          # build / verify / units scope
    fetching = a.command in ("update", "fetch")
    candidates = check_new_year(site, ctx) if fetching and not a.no_auto_year and not explicit else []
    new_targets: list[int] = []      # years fetched nationally now and added to the config on success
    pending: list[int] = []          # years left to a national run (workflow dispatch)
    if fetching:
        extra = [y for y in explicit if y not in {int(c) for c in site["years"]}]
        if a.national:
            new_targets = sorted(set(candidates) | set(extra))
        elif candidates:
            pending = candidates
            print(f"  auto-year: pendingYears={pending} - not fetched by a daily run; the workflow dispatches "
                  f"a national run (national=true, year={pending[0]}); this run continues with {years}")
    new_years: list[int] = []
    inherited_targets: dict = {}
    hard: list[str] = []
    fetch_warnings: list[str] = []
    plan: dict = {}
    available: list[int] = []        # new years whose DSPM national summary was written by this run

    def status(ok, **kw):
        write_status(command=a.command, ok=ok, years=years, newYears=new_years, pendingYears=pending,
                     inheritedTargets=inherited_targets,
                     national=a.national, fetchPlan={str(y): m for y, m in plan.items()},
                     fetchWarnings=fetch_warnings, **kw)

    try:
        if fetching:
            # a run that fetches a NEW year nationally (~60 min) keeps the configured years on the drill refresh
            # (their weekly national refresh waits for the next Monday) so one job stays inside timeout-minutes
            plan = refresh_scope(site, [y for y in (explicit or years) if y not in new_targets],
                                 a.national and not new_targets, explicit)
            h, w = do_fetch(ctx, inds, plan, a.refresh)
            hard += h
            fetch_warnings += w
            for y in new_targets:
                ok, h, w = fetch_new_year(ctx, inds, y, a.refresh)
                hard += h
                fetch_warnings += w
                if ok:
                    available.append(y)
            if hard:
                status(False, error=hard)
                return 2
            years = sorted(set(years) | set(available))
        if a.command in ("update", "fetch", "units"):
            do_units(ctx, years, refresh=a.refresh and a.command == "units")
        if available:
            # the DSPM national summary of each available new year exists -> publish it; a year without a target
            # inherits the previous year's target (Save 2026-10-06) so the web keeps its colours; the Issue asks
            # to confirm/correct it on /admin/
            site["years"] = sorted({int(y) for y in site["years"]} | set(available))
            site["currentYear"] = max(int(site["currentYear"]), *available)
            inherited_targets.update(inherit_targets(site, available))
            B.save_site(site)
            ctx = B.make_context(site)
            new_years = available
            print(f"  auto-year: fiscal year(s) {available} added to sites/{site['site']}.json "
                  f"(currentYear = {site['currentYear']}, inherited targets {inherited_targets}) -> newYears={available}")
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
        status(False, error=str(e))
        return 1
    for w in fetch_warnings:
        print(f"  fetch warning: {w}")
    print(f"[done] {a.command}: {len(hard)} hard error(s), {len(fetch_warnings)} fetch warning(s) "
          f"in {time.time() - t0:.1f}s")
    status(not hard, hardErrors=hard[:50], warnings=len(rep.warnings) if rep else None,
           filesWritten=len(files["files"]) if files else None)
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
