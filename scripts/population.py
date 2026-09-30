#!/usr/bin/env python3
"""population.py — ข้อมูลประชากร HDC (3 แท็บที่ยังไม่ขึ้นเว็บ): pop · typearea · denom05

  python3 scripts/population.py fetch  [--year 2569 ...] [--refresh]   API -> data/cache/{pop,typearea,pyramid}/
  python3 scripts/population.py build  [--year ...]                     cache (+ DSPM/Coverage datasets) -> data/prepared/<site>/
  python3 scripts/population.py report                                  reconciliation vs "manual data by user" + 0-5 denominators
                                                                        -> docs/POPULATION_DENOMINATORS_ANGTHONG.md + xlsx
  python3 scripts/population.py all                                     fetch -> build -> report

Nothing here touches site/ or sites/<site>.json: the prepared JSON has the same shape as site/data/<site>/*.json so the
three tabs can be published later by adding the plugins to build_site.PLUGINS / SOURCE_LEVELS and the site's
`indicators` list.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_site as B                                       # noqa: E402
from scripts.indicators import denom05, pop, pyramid, typearea            # noqa: E402

PLUGINS = {"pop": pop, "typearea": typearea, "denom05": denom05}
PREPARED = ROOT / "data" / "prepared"


def _years(site, arg):
    return sorted({int(y) for y in (arg or site["years"])})


# ------------------------------------------------------------------ fetch
def do_fetch(site, ctx, years, refresh, log=print):
    for y in years:
        for plugin in (pop, typearea):
            log(f"[fetch] {plugin.ID} {y}")
            plugin.fetch_cache(y, refresh, log)
        for prov in ctx["drill_provinces"]:
            log(f"[fetch] pyramid {y} province {prov}")
            pyramid.fetch_cache(y, prov, refresh, log)


# ------------------------------------------------------------------ build
def _zero(plugin):
    if plugin.ID == "pop":
        return plugin.values_from_sums(dict.fromkeys(plugin.RAW_FIELDS, 0))
    if plugin.ID == "typearea":
        return plugin.values_from_sums(dict.fromkeys(plugin.RAW_FIELDS, 0))
    return plugin.zero_values()


def _dataset(plugin, ctx, year, level, scope, rows, asof, warnings, source="api"):
    have = {r["code"] for r in rows}
    want = B.child_codes(ctx, level, scope)
    rows = list(rows)
    for c in want:
        if c not in have:
            warnings.append(f"{plugin.ID} {year} {level}/{scope}: child {c} ({B.area_name(ctx, B.child_level(level), c)}) "
                            f"absent from API -> zero row")
            rows.append({"code": c, "values": _zero(plugin)})
    extra = have - set(want)
    if extra:
        raise B.BuildError(f"{plugin.ID} {year} {level}/{scope}: unexpected child codes {sorted(extra)}")
    total = plugin.sum_values([r["values"] for r in rows])
    return B._mk_dataset(plugin, ctx, year, level, scope, rows, total, asof, source)


def build_population(site, ctx, years, log=print):
    """Return {"datasets": {(ind, year, level, scope): ds}, "warnings": [...]}."""
    out, warnings = {}, []
    home = ctx["home"]
    scopes = [("country", "TH"), ("region", str(home["region"])), ("province", home["province"]),
              ("district", home["district"])]
    # DSPM / Coverage as published on the web (Excel for DSPM country/region, API elsewhere)
    base = B.build_datasets(site, ctx, ["dspm", "coverage"], years, log=log)
    for y in years:
        caches = {}
        for plugin in (pop, typearea):
            c = plugin.load_cache(y)
            if c is None:
                warnings.append(f"{plugin.ID} {y}: no cache (run fetch)")
                continue
            caches[plugin.ID] = c
            for v in plugin.api_views(c, ctx):
                out[(plugin.ID, y, v["level"], v["scope"])] = _dataset(plugin, ctx, y, v["level"], v["scope"],
                                                                        v["rows"], c["asOf"], warnings)
        if "pop" not in caches or "typearea" not in caches:
            continue
        pyr = {p: pyramid.load_cache(y, p) for p in ctx["drill_provinces"]}
        for level, scope in scopes:
            dp = out[("pop", y, level, scope)]
            dt = out[("typearea", y, level, scope)]
            rows_pop = {r["code"]: r["values"] for r in dp["rows"] if r["hasData"]}
            rows_ta = {r["code"]: r["values"] for r in dt["rows"] if r["hasData"]}
            pyr04: dict = {}
            for p, c in pyr.items():
                if c is None:
                    continue
                keyfn = B_scope_keyfn(ctx, level, scope, p)
                pyr04.update(pyramid.group_totals(c, keyfn, "0-4 ปี"))
            dspm_ds = base["published"].get(("dspm", y, level, scope))
            cov_ds = base["published"].get(("coverage", y, level, scope))
            dspm_rows = {r["code"]: r["values"] for r in dspm_ds["rows"] if r["hasData"]} if dspm_ds else None
            cov_rows = {r["code"]: r["values"] for r in cov_ds["rows"] if r["hasData"]} if cov_ds else None
            codes = B.child_codes(ctx, level, scope)
            rows = denom05.assemble(rows_pop, rows_ta, pyr04, dspm_rows, cov_rows, codes)
            asof = max(dp["asOf"], dt["asOf"])
            out[("denom05", y, level, scope)] = _dataset(denom05, ctx, y, level, scope, rows, asof, warnings,
                                                         source="derived")
    return {"datasets": out, "warnings": warnings, "base": base}


def B_scope_keyfn(ctx, level, scope, province):
    """Pyramid cache holds one province: map its rows onto the view's child codes (others stay None)."""
    from scripts.indicators.popcommon import scope_keyfns
    kf = scope_keyfns(ctx, level, scope)
    return lambda a6, u6: (kf(a6, u6) if a6[:2] == province else None)


def write_prepared(site, ctx, built, log=print):
    out_dir = PREPARED / site["site"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.json"):
        f.unlink()
    index_ds, written = [], []
    for key in sorted(built["datasets"], key=lambda k: (k[0], k[1], B.LEVEL_ORDER.index(k[2]), k[3])):
        ds = built["datasets"][key]
        plugin = PLUGINS[key[0]]
        fname = B.dataset_file(key)
        body = B.dataset_json(site["site"], plugin, ds)
        body["published"] = False
        (out_dir / fname).write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index_ds.append({"indicator": key[0], "year": key[1], "level": key[2], "scope": key[3], "kind": "level",
                         "file": fname, "asOf": ds["asOf"], "source": ds["source"]})
        written.append((fname, len(ds["rows"]), ds["asOf"], ds["source"]))
    index = {"schema": 1, "site": site["site"], "published": False,
             "note": "prepared offline by scripts/population.py — not referenced by site/data/<site>/index.json",
             "years": sorted({k[1] for k in built["datasets"]}),
             "sourceLabels": {"api": "MOPH Open Data API", "derived": "คำนวณจาก API + Excel HDC (DSPM ประเทศ/เขต)"},
             "indicators": {i: PLUGINS[i].META for i in PLUGINS},
             "datasets": index_ds}
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[build] wrote {len(written)} datasets to {out_dir.relative_to(ROOT)}/")
    for f, n, asof, src in written:
        log(f"  {f:<36} rows={n:<3} asOf={asof:<17} {src}")
    return written


def verify_population(ctx, built, log=print) -> list[str]:
    errors, warns = [], []
    for key, ds in sorted(built["datasets"].items()):
        ind, y, level, scope = key
        plugin = PLUGINS[ind]
        where0 = f"{ind} {y} {level}/{scope}"
        n = len(B.child_codes(ctx, level, scope))
        if len(ds["rows"]) != n:
            errors.append(f"{where0}: {len(ds['rows'])} rows, expected {n}")
        for r in ds["rows"] + [{"code": scope, "name": "รวม", **ds["total"]}]:
            if not r["hasData"]:
                continue
            for sev, msg in plugin.check_values(r["values"], f"{where0} {r['name']}"):
                (errors if sev == "hard" else warns).append(msg)
        # sum of children == total (by construction) and cross-level: parent row == child total
        cl = B.child_level(level)
        for r in ds["rows"]:
            child = built["datasets"].get((ind, y, cl, r["code"]))
            if child is None or not r["hasData"]:
                continue
            a, b = child["total"]["values"], r["values"]
            keys = plugin.COUNT_KEYS if ind != "pop" else None
            # a child total of None means the child level has no such source (e.g. Coverage below province)
            if ind == "pop":
                diffs = [(g, k) for g in plugin.GROUPS for k in plugin.COUNT_KEYS
                         if a[g][k] is not None and a[g][k] != b[g][k]]
            else:
                diffs = [k for k in keys if a[k] is not None and a[k] != b[k]]
            if diffs:
                errors.append(f"cross-level {where0} row {r['name']} != {cl}/{r['code']} total: {diffs[:3]}")
    for w in built["warnings"]:
        warns.append(w)
    log(f"[verify] hard errors: {len(errors)}  warnings: {len(warns)}")
    for e in errors[:20]:
        log(f"  ERROR {e}")
    seen = set()
    for w in warns:
        k = w.split(":")[0]
        if k in seen:
            continue
        seen.add(k)
        log(f"  WARN  {w}")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["fetch", "build", "report", "all"])
    ap.add_argument("--site", default="angthong")
    ap.add_argument("--year", action="append")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    site = B.load_site(a.site)
    ctx = B.make_context(site)
    years = _years(site, a.year)
    errors = []
    if a.command in ("fetch", "all"):
        do_fetch(site, ctx, years, a.refresh)
    if a.command in ("build", "all"):
        built = build_population(site, ctx, years)
        write_prepared(site, ctx, built)
        errors += verify_population(ctx, built)
    if a.command in ("report", "all"):
        from scripts import population_report
        errors += population_report.run(site, ctx, years)
    print(f"[done] {a.command}: {len(errors)} hard error(s) in {time.time() - t0:.1f}s")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
