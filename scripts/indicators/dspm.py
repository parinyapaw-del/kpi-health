"""DSPM plugin — พัฒนาการเด็กสมวัย (MOPH table s_childdev_specialpp).

API: 1 raw row = hospcode x areacode(8) x monthly.  Cache = (areacode[:6], hospcode, monthly), every raw field summed
(all 5 age suffixes).  province = sum of the cache, group 'total' = sum of the 5 suffixes.

UNIT-LOCATION RULE (Phase 2 spec §4.3, extended 2026-09-30): the HDC reports group BOTH the district ("อำเภอ") and the
subdistrict ("ตำบล") levels by where the reporting unit (hospcode) is LOCATED according to the MOPH GIS registry
(data/lookup/units.json) — not by the areacode of the child.  Evidence: สระบุรี 2569 Excel gives หนองโดน 296 /
พระพุทธบาท 1123 = the unit-location totals (รพ.สต.นายาว 01758 is located in พระพุทธบาท but reports 4 children with
หนองโดน areacodes); the areacode grouping (300 / 1119) does not match.  Units the registry does not know fall back
to the Phase 1 rule (the areacode[:6] where the unit has its largest target, ties -> lowest code) and are counted as
`inferredUnits` of the district.  Units whose rows carry areacodes of other districts are listed as `crossDistrict`
(information only; every unit of the 8 provinces is located inside its API province, so province totals are exact).
OVERRIDES: `overrides` in units.json ({hospcode: {"tambon": areacode6, "source", "note"}}) pin a unit to the tambon
the HDC ตำบล Excel puts it in; they win over the GIS registry and the fallback (source "override", not inferred) and
are listed as `overriddenUnits` of the district.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..loaders import moph_api
from .common import add, close, fmt_asof, pct, ssum

ID = "dspm"
TABLE = "s_childdev_specialpp"
ROOT = Path(__file__).resolve().parents[2]

GROUPS = ["total", "m9", "m18", "m30", "m42", "m60"]
SUFFIX = {"m9": "9", "m18": "18", "m30": "30", "m42": "42", "m60": "60"}
GROUP_LABEL = {"total": "รวมทั้ง 5 กลุ่มอายุ", "m9": "อายุ 9 เดือน", "m18": "อายุ 18 เดือน",
               "m30": "อายุ 30 เดือน", "m42": "อายุ 42 เดือน", "m60": "อายุ 60 เดือน"}
HEAT_LABEL = {"total": "รวม", "m9": "9 เดือน", "m18": "18 เดือน", "m30": "30 เดือน", "m42": "42 เดือน", "m60": "60 เดือน"}

# key -> raw field prefix (field = <prefix>_<suffix>)
RAW = {
    "target": "target", "screened": "result", "normal_first": "1b260_1", "suspect_wait30": "1b261",
    "suspect_refer": "1b262", "followed": "follow", "normal_after": "1b260_2", "delay_after_total": "improper",
    "delay_1B202": "1b202", "delay_1B212": "1b212", "delay_1B222": "1b222", "delay_1B232": "1b232",
    "delay_1B242": "1b242", "pending_followup": "wait30", "lost_followup": "loss",
    "normal_female": "1b260_f", "normal_male": "1b260_m",
}
COUNT_KEYS = list(RAW)                       # summable
PCT_KEYS = ["pct_screened", "pct_normal_first", "pct_suspect", "pct_followed", "pct_normal"]

# display order (spec §3.2 order) + Thai labels taken from the HDC Excel headers
TABLE_KEYS = [
    ("target", "เป้าหมาย (1)", "int"), ("screened", "คัดกรอง (2)", "int"),
    ("pct_screened", "ร้อยละคัดกรอง", "pct"), ("normal_first", "สมวัยครั้งแรก (2.1)", "int"),
    ("pct_normal_first", "ร้อยละสมวัยครั้งแรก", "pct"),
    ("suspect_wait30", "สงสัยล่าช้า รอกระตุ้น 30 วัน (2.2)", "int"),
    ("suspect_refer", "สงสัยล่าช้า ส่งต่อทันที (2.3)", "int"),
    ("suspect_total", "รวมสงสัยล่าช้าทั้งหมด (2.4)", "int"), ("pct_suspect", "ร้อยละสงสัยล่าช้า", "pct"),
    ("followed", "ติดตามได้ (3)", "int"), ("pct_followed", "ร้อยละติดตามได้", "pct"),
    ("normal_after", "สมวัยหลังได้รับการส่งเสริม/กระตุ้น (3.1)", "int"),
    ("delay_after_total", "ไม่สมวัยหลังได้รับการส่งเสริม/กระตุ้น รวม (3.2)", "int"),
    ("delay_1B202", "1B202 (3.2.1)", "int"), ("delay_1B212", "1B212 (3.2.2)", "int"),
    ("delay_1B222", "1B222 (3.2.3)", "int"), ("delay_1B232", "1B232 (3.2.4)", "int"),
    ("delay_1B242", "1B242 (3.2.5)", "int"),
    ("pending_followup", "รอการติดตาม (4)", "int"), ("lost_followup", "ติดตามไม่ได้ใน 30 วัน (5)", "int"),
    ("normal_female", "สมวัยเพศหญิง", "int"), ("normal_male", "สมวัยเพศชาย", "int"),
    ("normal_total", "รวมสมวัย", "int"), ("pct_normal", "ร้อยละสมวัย", "pct"),
]
ALL_KEYS = [k for k, _, _ in TABLE_KEYS]

META = {
    "id": ID,
    "name_th": "ร้อยละของเด็กอายุ 0-5 ปี มีพัฒนาการสมวัย 5 ช่วงอายุ (DSPM)",
    "short": "สมวัย",
    "source": {"table": TABLE,
               "bodyTemplate": {"tableName": TABLE, "year": "{year}", "province": "{province}",
                                "type": "json", "limit": 20000},
               "needsProvince": True},
    "levels": ["country", "region", "province", "district"],
    "groups": [{"key": g, "label": GROUP_LABEL[g]} for g in GROUPS],
    "headline": {"metric": "pct_normal", "num": "normal_total", "den": "target"},
    "cards": [
        {"metric": "pct_screened", "label": "คัดกรองพัฒนาการ", "num": "screened", "den": "target"},
        {"metric": "pct_suspect", "label": "สงสัยพัฒนาการล่าช้า", "num": "suspect_total", "den": "screened"},
        {"metric": "pct_followed", "label": "ติดตามได้ภายใน 30 วัน", "num": "followed", "den": "suspect_wait30"},
    ],
    "heatmap": {"columns": [{"key": g, "label": HEAT_LABEL[g], "group": g, "metric": "pct_normal",
                             "num": "normal_total", "den": "target", "useTarget": True} for g in GROUPS]},
    "chart": {"style": "status"},
    "table": [{"key": k, "label": l, "type": t} for k, l, t in TABLE_KEYS],
    "monthly": False,
    "targets_key": "dspm",
}


# ------------------------------------------------------------------ values model
def raw_fields():
    return [f"{p}_{s}" for p in RAW.values() for s in SUFFIX.values()]


def values_from_sums(sums: dict) -> dict:
    """sums: raw field -> int  ->  {group: {key: value}} with derived keys/percents."""
    out = {}
    for g in GROUPS:
        c = {}
        for k, prefix in RAW.items():
            if g == "total":
                parts = [sums.get(f"{prefix}_{s}") for s in SUFFIX.values()]
                c[k] = ssum(parts)
            else:
                c[k] = sums.get(f"{prefix}_{SUFFIX[g]}")
        out[g] = derive(c)
    return out


def derive(c: dict) -> dict:
    """Fill derived keys (suspect_total, normal_total, percents) from counts; keeps existing provided pcts."""
    d = dict(c)
    if d.get("suspect_total") is None:
        d["suspect_total"] = add(d.get("suspect_wait30"), d.get("suspect_refer"))
    if d.get("normal_total") is None:
        d["normal_total"] = add(d.get("normal_first"), d.get("normal_after"))
    calc = {
        "pct_screened": pct(d.get("screened"), d.get("target")),
        "pct_normal_first": pct(d.get("normal_first"), d.get("target")),
        "pct_suspect": pct(d.get("suspect_total"), d.get("screened")),
        "pct_followed": pct(d.get("followed"), d.get("suspect_wait30")),
        "pct_normal": pct(d.get("normal_total"), d.get("target")),
    }
    for k, v in calc.items():
        if d.get(k) is None:
            d[k] = v
    return {k: d.get(k) for k in ALL_KEYS}


def sum_values(items: list[dict]) -> dict:
    """Sum child `values` (count keys) and recompute derived keys. Zero-filled children (no data, e.g. Bangkok) are
    skipped so their 0 gender counts don't turn a not-populated (None) key into 0."""
    items = [v for v in items if has_data(v)] or items
    out = {}
    for g in GROUPS:
        c = {k: ssum(v[g][k] for v in items) for k in COUNT_KEYS}
        out[g] = derive(c)
    return out


def has_data(values: dict) -> bool:
    return any((v or 0) != 0 for g in values.values() for k, v in g.items() if k in COUNT_KEYS)


def null_values(values: dict) -> dict:
    return {g: {k: None for k in ALL_KEYS} for g in values}


def from_excel(xl_values: dict) -> dict:
    """Normalise Excel {group:{key:v}} to the full key set (derive the keys Excel lacks)."""
    return {g: derive({k: v for k, v in kv.items()}) for g, kv in xl_values.items()}


# ------------------------------------------------------------------ fetch / cache
def cache_path(year: int, province: str = "15") -> Path:
    return ROOT / "data" / "cache" / ID / str(year) / f"{province}.json"


def aggregate(rows: list[dict]) -> tuple[list[str], list[list]]:
    """raw rows -> (fields, [[areacode6, hospcode, monthly, <field sums...>], ...]).
    hospcode is kept as the string the API gives (e.g. '14O3F' with a letter O exists)."""
    fields = sorted({k for r in rows for k, v in r.items()
                     if k.rsplit("_", 1)[-1] in SUFFIX.values() and isinstance(v, int)})
    agg: dict[tuple, list] = {}
    for r in rows:
        key = (r["areacode"][:6], str(r["hospcode"]), r["monthly"])
        a = agg.setdefault(key, [0] * len(fields))
        for i, f in enumerate(fields):
            a[i] += r.get(f) or 0
    out = [[a6, h, m] + vals for (a6, h, m), vals in sorted(agg.items())]
    return fields, out


def cache_from_raw(raw: dict, log=print) -> dict:
    rows = raw["data"]
    year, province = int(raw["year"]), str(raw["province"])
    fields, agg = aggregate(rows)
    gender = any(v for r in rows for k, v in r.items() if k.startswith(("1b260_f_", "1b260_m_")))
    payload = {"schema": 2, "indicator": ID, "table": TABLE, "year": year, "province": province,
               "fetchedAt": raw["fetchedAt"], "asOf": max(r["date_com"] for r in rows),
               "rawRowCount": len(rows), "rowCount": len(agg), "genderPopulated": gender,
               "fields": fields, "rowFormat": ["areacode6", "hospcode", "monthly", "<fields...>"], "rows": agg}
    p = cache_path(year, province)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"  cache written  {p.relative_to(ROOT)}  ({len(agg)} rows, asOf {fmt_asof(payload['asOf'])})")
    return payload


def fetch_cache(year: int, province: str, refresh: bool, log=print) -> dict:
    raw = moph_api.get_raw(TABLE, year, province, refresh=refresh, log=log)
    return cache_from_raw(raw, log=log)


def load_cache(year: int, province: str = "15"):
    p = cache_path(year, province)
    if not p.exists():
        return None
    c = json.loads(p.read_text(encoding="utf-8"))
    if c.get("schema", 1) < 2 or c.get("rowFormat", [None])[1] != "hospcode":
        raise RuntimeError(f"{p.relative_to(ROOT)} is a Phase 1 cache (no hospcode column) - rebuild it: "
                           f"python3 scripts/kpi.py fetch --year {year} (raw cache) or --refresh")
    return c


def fetch_provinces(year: int, provinces: list[str], refresh: bool, log=print) -> list[str]:
    """Fetch (or rebuild from raw) the caches of `provinces`; returns provinces the API answered with 0 rows."""
    empty = []
    for i, p in enumerate(provinces, 1):
        if not refresh and cache_path(year, p).exists():
            try:
                load_cache(year, p)
                continue
            except RuntimeError:
                pass                     # Phase 1 cache -> rebuild from raw (or API)
        log(f"  [{i}/{len(provinces)}] province {p}")
        try:
            fetch_cache(year, p, refresh, log=log)
        except moph_api.ApiError as e:
            if "0 rows" not in str(e):
                raise
            log(f"    province {p}: API returned 0 rows -> empty")
            empty.append(p)
    return empty


# ------------------------------------------------------------------ national summary (country / region levels)
# The per-province caches of all 77 provinces stay local (~53 MB) except the drill provinces; only this summary
# (1 row of raw-field sums per province) is committed, and the country/region levels are built from it.
def summary_path(year: int) -> Path:
    return ROOT / "data" / "cache" / ID / str(year) / "provinces.json"


def fetch_all(year: int, provinces: list[str], refresh: bool, log=print) -> dict:
    """Fetch every province cache (sequential: parallel requests get HTTP 429), then write the summary.
    A province the API answers with 0 rows (Bangkok: not reported to HDC) is recorded as empty, not an error."""
    fetch_provinces(year, provinces, refresh, log=log)
    return write_summary(year, provinces, log=log)


def _province_sums(c: dict, fields: list[str]) -> list[int]:
    s = _sums(c, lambda a6, h, m: "all").get("all", {})
    return [s.get(f, 0) for f in fields]


def write_summary(year: int, provinces: list[str], log=print) -> dict:
    prov, missing, asofs, fetched, gender = {}, [], [], [], False
    fields = raw_fields()
    for p in provinces:
        c = load_cache(year, p)
        if c is None:
            missing.append(p)
            continue
        prov[p] = _province_sums(c, fields)
        asofs.append(c["asOf"])
        fetched.append(c["fetchedAt"])
        gender = gender or c.get("genderPopulated", False)
    payload = {"schema": 1, "indicator": ID, "table": TABLE, "year": year,
               "asOf": max(asofs), "fetchedAt": max(fetched), "genderPopulated": gender,
               "empty": sorted(missing, key=int), "fields": fields, "provinces": prov}
    p = summary_path(year)
    p.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"  summary written {p.relative_to(ROOT)}  ({len(prov)} provinces, empty {payload['empty']})")
    return payload


def update_summary(year: int, provinces: list[str], log=print):
    """Patch the committed national summary with fresh caches of `provinces` only (daily run: the other provinces
    keep their weekly values). Returns None when no summary exists yet (then country/region need --national)."""
    summ = load_summary(year)
    if summ is None:
        return None
    fields = summ["fields"]
    changed = []
    for p in provinces:
        c = load_cache(year, p)
        if c is None:
            continue
        vals = _province_sums(c, fields)
        if summ["provinces"].get(p) != vals:
            changed.append(p)
        summ["provinces"][p] = vals
        summ["asOf"] = max(summ["asOf"], c["asOf"])
        summ["fetchedAt"] = max(summ["fetchedAt"], c["fetchedAt"])
        summ["genderPopulated"] = summ.get("genderPopulated", False) or c.get("genderPopulated", False)
        if p in summ["empty"]:
            summ["empty"].remove(p)
    summ["provinces"] = dict(sorted(summ["provinces"].items(), key=lambda kv: int(kv[0])))
    summary_path(year).write_text(json.dumps(summ, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"  summary patched {summary_path(year).relative_to(ROOT)}  (provinces {provinces}, changed {changed})")
    return summ


def load_summary(year: int):
    p = summary_path(year)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def national_views(summary, ctx) -> list[dict]:
    """country (rows = 13 regions) + home region (rows = provinces) from the province summary.
    Empty provinces are simply absent -> build_site fills them as zero rows (hasData false)."""
    pv = {p: _values(summary, dict(zip(summary["fields"], vals))) for p, vals in summary["provinces"].items()}
    by_reg: dict = {}
    for p, v in pv.items():
        by_reg.setdefault(str(ctx["prov_region"][p]), []).append(v)
    views = [{"level": "country", "scope": "TH",
              "rows": [{"code": r, "values": sum_values(v)} for r, v in sorted(by_reg.items(), key=lambda x: int(x[0]))]}]
    for reg in ctx["drill_regions"]:
        views.append({"level": "region", "scope": reg,
                      "rows": [{"code": p, "values": v} for p, v in sorted(pv.items(), key=lambda x: int(x[0]))
                               if str(ctx["prov_region"][p]) == reg]})
    return views


# ------------------------------------------------------------------ API-side views
def _sums(cache, keyfn):
    """Group cache rows -> {key: {field: sum}}; keyfn(area6, hospcode, month)->key|None."""
    fields = cache["fields"]
    out: dict = {}
    for row in cache["rows"]:
        a6, h, m, vals = row[0], row[1], row[2], row[3:]
        k = keyfn(a6, h, m)
        if k is None:
            continue
        s = out.setdefault(k, dict.fromkeys(fields, 0))
        for f, v in zip(fields, vals):
            s[f] += v
    return out


def _values(cache, sums):
    v = values_from_sums(sums)
    if not cache.get("genderPopulated", True):      # raw 1b260_f/m are all 0 in that year -> not populated
        for g in v.values():
            g["normal_female"] = g["normal_male"] = None
    return v


def unit_areas(cache) -> dict:
    """{hospcode: {"target": total target, "areas": {areacode6: target}}} from the cache (all months)."""
    fields = cache["fields"]
    tidx = [i for i, f in enumerate(fields) if f.startswith("target_")]
    out: dict = {}
    for row in cache["rows"]:
        a6, h, vals = row[0], row[1], row[3:]
        t = sum(vals[i] for i in tidx)
        u = out.setdefault(h, {"target": 0, "areas": {}})
        u["target"] += t
        u["areas"][a6] = u["areas"].get(a6, 0) + t
    return out


def resolve_tambons(cache, registry: dict) -> dict:
    """hospcode -> {"tambon": areacode6, "inferred": bool, "name": str, "source": "override"|"registry"|"fallback"}.
    Override (HDC-confirmed) > registry (§4.3 rule 1-2) > Phase 1 fallback: areacode[:6] with the unit's largest
    target (ties -> lowest code). Only the fallback is `inferred`."""
    units = (registry or {}).get("units", {})
    overrides = (registry or {}).get("overrides", {})
    out = {}
    for h, u in unit_areas(cache).items():
        reg = units.get(h)
        if h in overrides:
            out[h] = {"tambon": overrides[h]["tambon"], "inferred": False, "source": "override",
                      "name": reg.get("name", "") if reg else ""}
        elif reg:
            out[h] = {"tambon": reg["tambon"], "inferred": False, "name": reg.get("name", ""), "source": "registry"}
        else:
            top = sorted(u["areas"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            out[h] = {"tambon": top, "inferred": True, "name": "", "source": "fallback"}
    return out


def api_views(cache, ctx, registry=None) -> list[dict]:
    """province P (rows = districts by the district of the reporting unit; unknown district codes -> pseudo rows)
    and, for every drill district of P, district D (rows = subdistricts by the tambon of the reporting unit, §4.3)."""
    prov = cache["province"]
    lk = ctx["lookup"]
    views = []
    tam = resolve_tambons(cache, registry)
    dsum = _sums(cache, lambda a6, h, m: tam[h]["tambon"][:4])
    rows = []
    for c, s in sorted(dsum.items()):
        r = {"code": c, "values": _values(cache, s)}
        if c not in lk["districts"]:
            r["pseudo"] = True
            r["name"] = f"ไม่ระบุพื้นที่ (รหัส {c})"
        rows.append(r)
    views.append({"level": "province", "scope": prov, "rows": rows})

    # rows of each unit by areacode district (for the cross-district report)
    by_unit_dist: dict = {}
    for h, u in unit_areas(cache).items():
        for a6, t in u["areas"].items():
            by_unit_dist.setdefault(h, {})
            by_unit_dist[h][a6[:4]] = by_unit_dist[h].get(a6[:4], 0) + t
    for d in ctx["drill_districts"]:
        if d[:2] != prov:
            continue
        ssums = _sums(cache, lambda a6, h, m, d=d: tam[h]["tambon"] if tam[h]["tambon"][:4] == d else None)
        units_in = sorted(h for h, t in tam.items() if t["tambon"][:4] == d)
        inferred = [h for h in units_in if tam[h]["inferred"]]
        overridden = [h for h in units_in if tam[h]["source"] == "override"]     # units_in is sorted
        cross = []
        for h in units_in:                                   # located in d, rows (also) elsewhere
            other = {k: v for k, v in by_unit_dist[h].items() if k != d}
            if other:
                cross.append({"hospcode": h, "name": tam[h]["name"], "tambon": tam[h]["tambon"], "locatedIn": d})
        for h, t in tam.items():                             # rows in d, located elsewhere
            if t["tambon"][:4] != d and d in by_unit_dist[h]:
                cross.append({"hospcode": h, "name": t["name"], "tambon": t["tambon"],
                              "locatedIn": t["tambon"][:4]})
        views.append({"level": "district", "scope": d, "fill": False,
                      "rows": [{"code": c, "values": _values(cache, s)} for c, s in sorted(ssums.items())],
                      "extra": {"inferredUnits": len(inferred), "overriddenUnits": overridden,
                                "units": len(units_in), "crossDistrict": cross}})
    return views


# ------------------------------------------------------------------ validation
def check_values(values: dict, where: str) -> list[tuple[str, str]]:
    """Return [(severity, message)]. hard = spec §3.5 formulas/identities; warn = HDC quirks."""
    issues = []
    for g, v in values.items():
        w = f"{where} [{g}]"
        def num(k):
            return v.get(k)
        formulas = [("pct_screened", num("screened"), num("target")),
                    ("pct_normal_first", num("normal_first"), num("target")),
                    ("pct_suspect", num("suspect_total"), num("screened")),
                    ("pct_followed", num("followed"), num("suspect_wait30")),
                    ("pct_normal", num("normal_total"), num("target"))]
        for k, n, d in formulas:
            if n is None or d is None:
                continue
            if d == 0:
                if v.get(k) not in (None, 0):
                    issues.append(("hard", f"{w} {k}={v.get(k)} but denominator is 0"))
            elif v.get(k) is not None and not close(v[k], 100.0 * n / d):
                issues.append(("hard", f"{w} {k}={v[k]} != {n}/{d}*100={100.0 * n / d:.2f}"))
        if None not in (num("suspect_wait30"), num("suspect_refer"), num("suspect_total")) and \
                num("suspect_total") != num("suspect_wait30") + num("suspect_refer"):
            issues.append(("hard", f"{w} suspect_total {num('suspect_total')} != wait30+refer"))
        if None not in (num("normal_first"), num("normal_after"), num("normal_total")) and \
                num("normal_total") != num("normal_first") + num("normal_after"):
            issues.append(("hard", f"{w} normal_total {num('normal_total')} != normal_first+normal_after"))
        if None not in (num("suspect_wait30"), num("followed"), num("pending_followup"), num("lost_followup")) and \
                num("suspect_wait30") != num("followed") + num("pending_followup") + num("lost_followup"):
            issues.append(("hard", f"{w} suspect_wait30 {num('suspect_wait30')} != followed+pending+lost "
                                   f"({num('followed')}+{num('pending_followup')}+{num('lost_followup')})"))
        if None not in (num("followed"), num("normal_after"), num("delay_after_total")) and \
                num("followed") != num("normal_after") + num("delay_after_total"):
            issues.append(("warn", f"{w} followed {num('followed')} != normal_after+delay_after_total "
                                   f"({num('normal_after')}+{num('delay_after_total')})"))
        if None not in (num("normal_female"), num("normal_male"), num("normal_total")) and \
                num("normal_total") != num("normal_female") + num("normal_male"):
            issues.append(("warn", f"{w} normal_total {num('normal_total')} != female+male "
                                   f"({num('normal_female')}+{num('normal_male')})"))
    return issues


def compare(api: dict, xl: dict, xl_keys: dict) -> list[str]:
    """Compare API-built vs Excel values. xl_keys: {group: [keys present in the Excel file]}."""
    bad = []
    for g, keys in xl_keys.items():
        for k in keys:
            a, x = api[g][k], xl[g][k]
            if x is None:
                continue
            if k in PCT_KEYS:
                den_zero = _pct_den_zero(api[g], k)
                if den_zero:
                    if x not in (0, None):
                        bad.append(f"{g}.{k}: api den=0 (None) vs excel {x}")
                    continue
                if not close(a, x):
                    bad.append(f"{g}.{k}: api {a} vs excel {x}")
            elif a != x:
                bad.append(f"{g}.{k}: api {a} vs excel {x}")
    return bad


def _pct_den_zero(gvals, k):
    den = {"pct_screened": "target", "pct_normal_first": "target", "pct_suspect": "screened",
           "pct_followed": "suspect_wait30", "pct_normal": "target"}[k]
    return gvals.get(den) == 0
