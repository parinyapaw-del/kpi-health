"""verify — API-built datasets vs HDC Excel oracle + formula / identity / row-count checks (spec §3.5).

Hard errors -> exit code != 0.  Everything runs from the committed cache (no network).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

from . import build_lookup, build_site as B

EXPECTED_ROWS = {"country": 13, "region": 8}   # fixed row counts (Phase 2 §4.5); province/district follow the lookup
REGION4 = build_lookup.REGIONS[4].split()       # the MOPH table areas.json was built from


class Report:
    def __init__(self):
        self.errors, self.warnings, self.notes = [], [], []
        self.comparisons = 0
        self.checks = []           # (name, compared, ok)

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def _full_keys(plugin):
    if plugin.ID == "dspm":
        return {g: list(plugin.ALL_KEYS) for g in plugin.GROUPS}
    return list(plugin.ALL_KEYS)


# API-built DSPM country/region differ 0.1-3% from the HDC Excel for some provinces even in closed years
# (HDC report vs Open Data API data versions, docs/API_NOTES.md §3) -> reported as one warning per dataset.
SOFT_EXCEL = {("dspm", "country"), ("dspm", "region")}


def _day(asof):
    return (asof or "")[:10]


def _stale(ads, xds):
    """The Excel oracle is a snapshot (its dated folder <year>/<YYYY-MM-DD>/); once the API data is newer than
    that day the numbers legitimately move (open fiscal year, daily refresh) -> value differences become warnings.
    Structural checks (row sets, names, hasData, cross-level sums) stay hard regardless."""
    snap = _day(xds.get("asOf"))
    return bool(snap) and _day(ads.get("asOf")) > snap


def _cmp(plugin, a, b, keys, rep, where, soft=None):
    """Compare values a (api/child) vs b (excel/parent); count comparisons; record errors
    (or append them to the `soft` list instead)."""
    n = 0
    if plugin.ID == "dspm":
        for g, ks in keys.items():
            for k in ks:
                if b[g][k] is not None:
                    n += 1
    else:
        for k in keys:
            if b.get(k) is not None:
                n += 1
    rep.comparisons += n
    for m in plugin.compare(a, b, keys):
        if soft is not None:
            soft.append(f"{where}: {m}")
        else:
            rep.err(f"{where}: {m}")
    return n


def _lookup_checks(ctx, built, rep):
    lk = ctx["lookup"]
    if len(lk["provinces"]) != 77:
        rep.err(f"lookup: {len(lk['provinces'])} provinces (expected 77)")
    r4 = sorted(v["name"] for v in lk["provinces"].values() if v["region"] == 4)
    if r4 != sorted(REGION4):
        rep.err(f"lookup: region 4 = {r4}")
    if sorted(lk["regions"], key=int) != [str(i) for i in range(1, 14)]:
        rep.err("lookup: regions are not 1..13")
    # names in the Excel files == lookup names of the detected scope (district files: subset = subdistricts with units)
    n_xl = 0
    for key, ds in built["excel"].items():
        ind, y, level, scope = key
        if level == "country":
            continue
        crow = B.child_level(level)
        xl = {r["name"] for r in ds["rows"]}
        lkn = {B.area_name(ctx, crow, c) for c in B.child_codes(ctx, level, scope)}
        if level == "region":
            if xl != set(REGION4):
                rep.err(f"{ind} {y} {level}/{scope}: Excel provinces {sorted(xl)} != region-4 set")
        elif level == "province" and xl != lkn:
            rep.err(f"{ind} {y} {level}/{scope}: Excel names != lookup names (diff {sorted(xl ^ lkn)})")
        elif not xl <= lkn:
            rep.err(f"{ind} {y} {level}/{scope}: Excel names not in lookup (diff {sorted(xl - lkn)})")
        n_xl += 1
    rep.notes.append(f"lookup names: {n_xl} Excel files matched to their scope by row names; region 4 == 8 provinces")


def _internal_checks(plugin, key, ds, rep):
    ind, y, level, scope = key
    where0 = f"{ind} {y} {level}/{scope} ({ds['source']})"
    children = B.child_codes(rep.ctx, level, scope)
    real = [r for r in ds["rows"] if not r.get("pseudo")]
    pseudo = [r for r in ds["rows"] if r.get("pseudo")]
    if level == "district":
        # HDC lists only the subdistricts that have a reporting unit -> rows must be a non-empty subset
        bad = [r["code"] for r in real if r["code"] not in children]
        if bad:
            rep.err(f"{where0}: subdistrict codes not in {scope}: {bad}")
        if not real:
            rep.err(f"{where0}: no subdistrict rows")
        if ds["source"] == "excel" and pseudo:
            rep.err(f"{where0}: pseudo rows in an Excel file")
    else:
        if len(real) != len(children):
            rep.err(f"{where0}: {len(real)} rows, expected {len(children)}")
        if pseudo and (ds["source"] == "excel" or level != "province"):
            rep.err(f"{where0}: unexpected pseudo rows {[r['code'] for r in pseudo]}")
    if level in EXPECTED_ROWS and (level == "country" or scope in rep.ctx["drill_regions"]):
        exp = EXPECTED_ROWS[level]
        if len(real) != exp:
            rep.err(f"{where0}: {len(real)} rows, spec expects {exp}")
    for r in ds["rows"] + [{"code": scope, "name": "รวม", **ds["total"]}]:
        if not r["hasData"]:
            continue
        for sev, msg in plugin.check_values(r["values"], f"{where0} {r['name']}"):
            (rep.err if sev == "hard" else rep.warn)(msg)
    # sum of children vs total row (Excel: file's รวม row; API total is the sum by construction)
    if ds["source"] == "excel" and ds.get("has_total_row"):
        s = plugin.sum_values([r["values"] for r in ds["rows"]])
        if plugin.ID == "dspm":
            diffs = [(g, k, s[g][k], ds["total"]["values"][g][k]) for g in plugin.GROUPS for k in plugin.COUNT_KEYS
                     if s[g][k] is not None and ds["total"]["values"][g][k] is not None
                     and s[g][k] != ds["total"]["values"][g][k]]
        else:
            diffs = [(None, k, s[k], ds["total"]["values"][k]) for k in plugin.COUNT_KEYS
                     if s[k] is not None and ds["total"]["values"][k] is not None
                     and s[k] != ds["total"]["values"][k]]
        if diffs:
            rep.warn(f"{where0}: Excel รวม row != sum of rows in {len(diffs)} keys, e.g. {diffs[0]}")


def _api_vs_excel(ctx, built, rep):
    for key, xds in sorted(built["excel"].items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        ads = built["api"].get(key)
        if ads is None:
            continue
        plugin = B.PLUGINS[key[0]]
        keys = xds["xl_keys"]
        where = f"{key[0]} {key[1]} {key[2]}/{key[3]}"
        arows = {r["code"]: r for r in ads["rows"]}
        xrows = {r["code"]: r for r in xds["rows"]}
        if set(arows) != set(xrows):
            rep.err(f"{where}: row sets differ api-only={sorted(set(arows) - set(xrows))} "
                    f"excel-only={sorted(set(xrows) - set(arows))}")
        n0 = rep.comparisons
        stale = _stale(ads, xds)
        soft = [] if (key[0], key[2]) in SOFT_EXCEL or stale else None
        for c in sorted(set(arows) & set(xrows)):
            a, x = arows[c], xrows[c]
            if a["hasData"] != x["hasData"]:
                rep.err(f"{where} {a['name']}: hasData api={a['hasData']} excel={x['hasData']}")
                continue
            if not x["hasData"]:
                continue
            _cmp(plugin, a["values"], x["values"], keys, rep, f"{where} {a['name']}", soft)
        if xds.get("has_total_row"):
            _cmp(plugin, ads["total"]["values"], xds["total"]["values"], keys, rep, f"{where} รวม", soft)
        if soft:
            rows = sorted({m.split(": ", 1)[0].removeprefix(where + " ") for m in soft})
            why = (f"Excel snapshot {_day(xds.get('asOf'))} is older than the API data {_day(ads.get('asOf'))} "
                   f"(open year moves daily; export new HDC files into a new dated folder to re-verify exactly)"
                   if stale else "known HDC-vs-API difference")
            rep.warn(f"{where}: API != HDC Excel in {len(soft)} values / {len(rows)} rows ({', '.join(rows)}) "
                     f"- {why}, e.g. {soft[0]}")
        tag = " (soft: stale snapshot)" if stale else (" (soft)" if soft is not None else "")
        rep.checks.append((f"api==excel  {where}{tag}", rep.comparisons - n0))


def _cross_level(ctx, built, rep):
    """A row of a parent view must equal the total of the child's own view (region row == province total,
    district row == subdistrict total; both by unit location, so they must match exactly). Kept as a soft check
    (warning with the numbers) only for districts that have cross-district units, per spec §4.3 rule 3."""
    pub = built["published"]
    for key, ds in sorted(pub.items(), key=lambda kv: (kv[0][0], kv[0][1], B.LEVEL_ORDER.index(kv[0][2]))):
        ind, y, level, scope = key
        cl = B.child_level(level)
        plugin = B.PLUGINS[ind]
        for r in ds["rows"]:
            ck = (ind, y, cl, r["code"])
            child = pub.get(ck)
            if child is None or not r["hasData"]:
                continue
            keys = _full_keys(plugin)
            n0 = rep.comparisons
            cross = child.get("crossDistrict") or []
            soft = [] if cross else None
            _cmp(plugin, child["total"]["values"], r["values"], keys, rep,
                 f"cross-level {ind} {y}: {level}/{scope} row {r['name']} vs {cl}/{r['code']} total", soft)
            if soft:
                t_row = r["values"]["total"]["target"] if ind == "dspm" else None
                t_child = child["total"]["values"]["total"]["target"] if ind == "dspm" else None
                units = ", ".join(f"{c['hospcode']} {c['name'] or '(นอกทะเบียน)'} -> {c['tambon']}" for c in cross)
                rep.warn(f"cross-level {ind} {y}: {level}/{scope} row {r['name']} (by areacode, target {t_row}) != "
                         f"{cl}/{r['code']} total (by unit location, target {t_child}) in {len(soft)} values - "
                         f"units located across districts: {units}")
            rep.checks.append((f"cross-level {ind} {y} {level}/{scope} row {r['name']} == {cl}/{r['code']} total"
                               f"{' (soft: cross-district units)' if cross else ''}", rep.comparisons - n0))


def _check_written(site, ctx, built, rep):
    d = B.ROOT / "site" / "data" / site["site"]
    idx = d / "index.json"
    if not idx.exists():
        rep.warn("site/data index.json missing — run `kpi.py build`")
        return
    index = json.loads(idx.read_text(encoding="utf-8"))
    n_files = 0
    for e in index["datasets"]:
        p = d / e["file"]
        if not p.exists():
            rep.err(f"index lists missing file {e['file']}")
            continue
        n_files += 1
        j = json.loads(p.read_text(encoding="utf-8"))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?", j["asOf"]):
            rep.err(f"{e['file']}: bad asOf {j['asOf']}")
        if e.get("kind", "level") == "level":
            if j["level"] not in B.LEVEL_ORDER:
                rep.err(f"{e['file']}: bad level {j['level']}")
            for r in j["rows"] + [j["total"]]:
                blob = r.get("groups") or r.get("metrics")
                leaves = [v for g in blob.values() for v in (g.values() if isinstance(g, dict) else [g])] \
                    if j["indicator"] == "dspm" else list(blob.values())
                bad = [v for v in leaves if v is not None and (isinstance(v, (str, bool)) or not isinstance(v, (int, float)))]
                if bad:
                    rep.err(f"{e['file']}: non-numeric values in row {r['code']}: {bad[:3]}")
                if not r["hasData"] and any(v is not None for v in leaves):
                    rep.err(f"{e['file']}: hasData=false row {r['code']} carries values")
    rep.notes.append(f"written JSON: index.json + {n_files} dataset files checked (numbers/null only, asOf format)")


def run(site: dict, ctx: dict, built: dict) -> Report:
    rep = Report()
    rep.ctx = ctx
    _lookup_checks(ctx, built, rep)
    for w in built["warnings"]:
        rep.warn(w)
    for src in ("api", "excel"):
        for key, ds in sorted(built[src].items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][3])):
            _internal_checks(B.PLUGINS[key[0]], key, ds, rep)
    _api_vs_excel(ctx, built, rep)
    _cross_level(ctx, built, rep)
    _check_written(site, ctx, built, rep)
    return rep


def summarize(rep: Report, log=print):
    def group(msgs):
        c = defaultdict(list)
        for m in msgs:
            cat = re.sub(r"[\d.]+", "#", m.split("] ", 1)[-1] if "] " in m else m)[:110]
            c[cat].append(m)
        return c
    log(f"  comparisons made: {rep.comparisons:,}   hard errors: {len(rep.errors)}   warnings: {len(rep.warnings)}")
    for n in rep.notes:
        log(f"  note: {n}")
    for name, cnt in rep.checks:
        log(f"  check  {cnt:>6,}  {name}")
    for label, msgs in (("ERROR", rep.errors), ("WARN", rep.warnings)):
        for cat, ms in group(msgs).items():
            log(f"  {label} x{len(ms)}: {ms[0]}")
