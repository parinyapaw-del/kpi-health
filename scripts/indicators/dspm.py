"""DSPM plugin — พัฒนาการเด็กสมวัย (MOPH table s_childdev_specialpp).

API: 1 raw row = hospcode x areacode(8) x monthly.  Cache = (areacode[:6], unit tambon, monthly), every raw
field summed (all 5 age suffixes).  district = areacode[:4], province = sum, group 'total' = sum of the 5 suffixes.

SUBDISTRICT RULE (differs from spec §3.4, see final report): the HDC "ตำบล" report groups by the tambon of the
reporting unit (hospcode), not by areacode[:6] of the child's village.  A hospcode's tambon ("unit6") is derived from
the API data only: the areacode[:6] where that hospcode has the largest target (ties -> lowest code).  Verified
against the Excel oracle by `kpi.py verify` (hard errors if it ever stops matching).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ..loaders import moph_api
from .common import PCT_TOL, THAI_MONTHS_SHORT, add, close, fmt_asof, pct, ssum

ID = "dspm"
TABLE = "s_childdev_specialpp"
ROOT = Path(__file__).resolve().parents[2]

GROUPS = ["total", "m9", "m18", "m30", "m42", "m60"]
SUFFIX = {"m9": "9", "m18": "18", "m30": "30", "m42": "42", "m60": "60"}
GROUP_LABEL = {"total": "รวมทั้ง 5 กลุ่มอายุ", "m9": "อายุ 9 เดือน", "m18": "อายุ 18 เดือน",
               "m30": "อายุ 30 เดือน", "m42": "อายุ 42 เดือน", "m60": "อายุ 60 เดือน"}

# key -> raw field prefix (field = <prefix>_<suffix>)
RAW = {
    "target": "target", "screened": "result", "normal_first": "1b260_1", "suspect_wait30": "1b261",
    "suspect_refer": "1b262", "followed": "follow", "normal_after": "1b260_2", "delay_after_total": "improper",
    "delay_1B202": "1b202", "delay_1B212": "1b212", "delay_1B222": "1b222", "delay_1B232": "1b232",
    "delay_1B242": "1b242", "pending_followup": "wait30", "lost_followup": "loss",
    "normal_female": "1b260_f", "normal_male": "1b260_m",
}
COUNT_KEYS = list(RAW)                       # summable
DERIVED_COUNT = ["suspect_total", "normal_total"]
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
    "name_th": "ร้อยละเด็กปฐมวัยพัฒนาการสมวัย (DSPM)",
    "short": "DSPM",
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
    "table": [{"key": k, "label": l, "type": t} for k, l, t in TABLE_KEYS],
    "monthly": True,
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
    """Sum child `values` (count keys) and recompute derived keys."""
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


def unit_tambon(rows: list[dict]) -> dict:
    """hospcode -> tambon (areacode[:6]) where the unit has its largest target (ties -> lowest code)."""
    w: dict = {}
    for r in rows:
        t = sum(r.get(f"target_{s}") or 0 for s in SUFFIX.values())
        k = w.setdefault(r["hospcode"], {})
        a6 = r["areacode"][:6]
        k[a6] = k.get(a6, 0) + t
    return {h: sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for h, v in w.items()}


def aggregate(rows: list[dict]) -> tuple[list[str], list[list], dict]:
    fields = sorted({k for r in rows for k, v in r.items()
                     if k.rsplit("_", 1)[-1] in SUFFIX.values() and isinstance(v, int)})
    units = unit_tambon(rows)
    agg: dict[tuple, list] = {}
    for r in rows:
        key = (r["areacode"][:6], units[r["hospcode"]], r["monthly"])
        a = agg.setdefault(key, [0] * len(fields))
        for i, f in enumerate(fields):
            a[i] += r.get(f) or 0
    out = [[a6, u6, m] + vals for (a6, u6, m), vals in sorted(agg.items())]
    return fields, out, units


def fetch_cache(year: int, province: str, refresh: bool, log=print) -> dict:
    raw = moph_api.get_raw(TABLE, year, province, refresh=refresh, log=log)
    rows = raw["data"]
    fields, agg, units = aggregate(rows)
    gender = any(v for r in rows for k, v in r.items() if k.startswith(("1b260_f_", "1b260_m_")))
    payload = {"schema": 1, "indicator": ID, "table": TABLE, "year": year, "province": province,
               "fetchedAt": raw["fetchedAt"], "asOf": max(r["date_com"] for r in rows),
               "rawRowCount": len(rows), "rowCount": len(agg), "genderPopulated": gender,
               "units": dict(sorted(units.items())),
               "fields": fields, "rowFormat": ["areacode6", "unit6", "monthly", "<fields...>"], "rows": agg}
    p = cache_path(year, province)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"  cache written  {p.relative_to(ROOT)}  ({len(agg)} rows, asOf {fmt_asof(payload['asOf'])})")
    return payload


def load_cache(year: int, province: str = "15"):
    p = cache_path(year, province)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ------------------------------------------------------------------ API-side views
def _sums(cache, keyfn, monthfn=None):
    """Group cache rows -> {key: {field: sum}}; keyfn(area6, unit6, month)->key|None."""
    fields = cache["fields"]
    out: dict = {}
    for row in cache["rows"]:
        a6, u6, m, vals = row[0], row[1], row[2], row[3:]
        k = keyfn(a6, u6, m)
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


def api_views(cache, ctx) -> list[dict]:
    """Datasets derivable from the API cache: province 15 (rows=districts) and district 1501 (rows=subdistricts)."""
    prov = cache["province"]
    views = []
    dsum = _sums(cache, lambda a6, u6, m: a6[:4])
    views.append({"level": "province", "scope": prov,
                  "rows": [{"code": c, "values": _values(cache, s)} for c, s in sorted(dsum.items())]})
    for d in ctx["drill_districts"]:
        ssums = _sums(cache, lambda a6, u6, m, d=d: u6 if a6[:4] == d else None)
        views.append({"level": "district", "scope": d,
                      "rows": [{"code": c, "values": _values(cache, s)} for c, s in sorted(ssums.items())]})
    return views


def monthly_view(cache, level: str, scope: str, child_len: int) -> dict:
    """{'months': [12 dicts], 'rows': [{code, months}]} for the scope.
    province scope: children = districts (areacode[:4]); district scope: children = subdistricts (unit tambon)."""
    by_unit = level == "district"
    code_of = (lambda a6, u6: u6) if by_unit else (lambda a6, u6: a6[:4])
    in_scope = lambda a6, u6: (a6[:4] == scope) if by_unit else a6.startswith(scope)

    def build(sumsmap):
        months = []
        cum = {"screened": 0, "target": 0, "normal_total": 0}
        for fy in range(1, 13):
            cal = ((fy + 8) % 12) + 1          # fyIndex 1 = Oct(10) ... 12 = Sep(9)
            s = sumsmap.get(f"{cal:02d}")
            if s is None:
                months.append({"fyIndex": fy, "calMonth": cal, "label": THAI_MONTHS_SHORT[cal],
                               "hasData": False, "screened": None, "target": None, "normal_total": None,
                               "cum": {"screened": None, "target": None, "normal_total": None}})
                continue
            tot = values_from_sums(s)["total"]
            m = {"screened": tot["screened"], "target": tot["target"], "normal_total": tot["normal_total"]}
            for k in cum:
                cum[k] += m[k]
            months.append({"fyIndex": fy, "calMonth": cal, "label": THAI_MONTHS_SHORT[cal], "hasData": True,
                           **m, "cum": dict(cum)})
        return months

    tot_by_month = _sums(cache, lambda a6, u6, m: m if in_scope(a6, u6) else None)
    codes = sorted({code_of(r[0], r[1]) for r in cache["rows"] if in_scope(r[0], r[1])})
    out_rows = []
    for c in codes:
        sm = _sums(cache, lambda a6, u6, m, c=c: m if in_scope(a6, u6) and code_of(a6, u6) == c else None)
        out_rows.append({"code": c, "months": build(sm)})
    return {"months": build(tot_by_month), "rows": out_rows}


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
