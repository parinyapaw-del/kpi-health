"""verify — API-built datasets vs HDC Excel oracle + formula / identity / row-count checks (spec §3.5).

Hard errors -> exit code != 0.  Everything runs from the committed cache (no network).
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from . import build_site as B
from .indicators.common import PCT_TOL

EXPECTED_ROWS = {"country": 13, "region": 8, "province": 7, "district": 14}   # spec §3.5 (home-path scopes)
REGION4 = ["นครนายก", "นนทบุรี", "ปทุมธานี", "พระนครศรีอยุธยา", "ลพบุรี", "สระบุรี", "สิงห์บุรี", "อ่างทอง"]


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


def _count_cmp(plugin, keys):
    if plugin.ID == "dspm":
        return sum(len(v) for v in keys.values())
    return len(keys)


def _cmp(plugin, a, b, keys, rep, where):
    """Compare values a (api/child) vs b (excel/parent); count comparisons; record errors."""
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
    # names in Angthong Excel files == lookup names
    for key, ds in built["excel"].items():
        ind, y, level, scope = key
        if level == "country":
            continue
        crow = B.child_level(level)
        xl = {r["name"] for r in ds["rows"]}
        lkn = {area_name for area_name in (B.area_name(ctx, crow, c) for c in B.child_codes(ctx, level, scope))}
        if level == "region":
            if xl != set(REGION4):
                rep.err(f"{ind} {y} {level}/{scope}: Excel provinces {sorted(xl)} != region-4 set")
        elif xl != lkn:
            rep.err(f"{ind} {y} {level}/{scope}: Excel names != lookup names (diff {sorted(xl ^ lkn)})")
    rep.notes.append("lookup names: 7 districts + 14 subdistricts of Angthong == Excel names; region 4 == 8 provinces")


def _internal_checks(plugin, key, ds, rep):
    ind, y, level, scope = key
    where0 = f"{ind} {y} {level}/{scope} ({ds['source']})"
    n_children = len(B.child_codes(rep.ctx, level, scope))
    if len(ds["rows"]) != n_children:
        rep.err(f"{where0}: {len(ds['rows'])} rows, expected {n_children}")
    home = rep.ctx["home"]
    if scope == home.get(level) or (level == "country" and scope == "TH"):
        exp = EXPECTED_ROWS[level]
        if len(ds["rows"]) != exp:
            rep.err(f"{where0}: {len(ds['rows'])} rows, spec expects {exp}")
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
        for c in sorted(set(arows) & set(xrows)):
            a, x = arows[c], xrows[c]
            if a["hasData"] != x["hasData"]:
                rep.err(f"{where} {a['name']}: hasData api={a['hasData']} excel={x['hasData']}")
                continue
            if not x["hasData"]:
                continue
            _cmp(plugin, a["values"], x["values"], keys, rep, f"{where} {a['name']}")
        if xds.get("has_total_row"):
            _cmp(plugin, ads["total"]["values"], xds["total"]["values"], keys, rep, f"{where} รวม")
        rep.checks.append((f"api==excel  {where}", rep.comparisons - n0))


def _cross_level(ctx, built, rep):
    """A row of a parent view must equal the total of the child's own view (e.g. region-4 Angthong == province-15 API)."""
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
            keys = ds["xl_keys"] if ds["source"] == "excel" else _full_keys(plugin)
            n0 = rep.comparisons
            _cmp(plugin, child["total"]["values"], r["values"], keys, rep,
                 f"cross-level {ind} {y}: {level}/{scope} row {r['name']} vs {cl}/{r['code']} total")
            tag = " [explicit: region-4 Excel Angthong == province-15 API]" if (ind, level, r["code"]) == ("dspm", "region", "15") else ""
            rep.checks.append((f"cross-level {ind} {y} {level}/{scope} row {r['name']} == {cl}/{r['code']} total{tag}",
                               rep.comparisons - n0))


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
        if e["kind"] == "level":
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


def run(site: dict, ctx: dict, built: dict, log=print, check_written=True) -> Report:
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
    # Excel-covered datasets lacking an API twin are Excel-only (DSPM country/region): internal checks only.
    if check_written:
        _check_written(site, ctx, built, rep)
    return rep


def summarize(rep: Report, log=print, max_examples=1):
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
