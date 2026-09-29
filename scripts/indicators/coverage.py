"""Coverage plugin — เด็กปฐมวัยพัฒนาการล่าช้าเข้าถึงบริการ (MOPH table s_child0_5_pshyche_develop_coverage).

API: never send `province` (HTTP 400). 2567/2568 -> 77 rows (by province); 2569 -> 928 rows (by district).
c_1..c_7, c_9, c_11 = Excel columns (1)..(7),(9),(11); c_8 and c_10 are NOT returned -> computed.
Cache = the API rows as given (whole country, all.json) + fetchedAt/asOf/rowCount.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..loaders import moph_api
from .common import PCT_TOL, close, fmt_asof, pct, ssum

ID = "coverage"
TABLE = "s_child0_5_pshyche_develop_coverage"
ROOT = Path(__file__).resolve().parents[2]

RAWMAP = {"population": "c_1", "prevalence": "c_2", "expected": "c_3", "served_teda4i": "c_4",
          "served_icd9": "c_5", "diagnosed_icd10": "c_6", "reached_cum": "c_7", "reached_fy": "c_9",
          "out_of_province": "c_11"}
COUNT_KEYS = ["population", "expected", "served_teda4i", "served_icd9", "diagnosed_icd10",
              "reached_cum", "reached_fy", "out_of_province"]
PCT_KEYS = ["pct_reached_cum", "pct_reached_fy", "pct_teda4i", "pct_icd10"]
TABLE_KEYS = [
    ("population", "เด็กปฐมวัยอายุ 0–5 ปี (คน) (1)", "int"),
    ("prevalence", "ความชุก (ร้อยละ) (2)", "pct"),
    ("expected", "จำนวนเด็กปฐมวัยที่คำนวณได้จากอัตราความชุก (คน) (3)=(1)*(2)/100", "int"),
    ("served_teda4i", "เด็กพัฒนาการล่าช้าที่ได้รับบริการด้วยรหัส TEDA4I (สะสม) (4)", "int"),
    ("served_icd9", "เด็กพัฒนาการล่าช้าที่ได้รับบริการด้วยรหัสหัตถการ ICD9CM/ICD-10TM (สะสม) (5)", "int"),
    ("diagnosed_icd10", "เด็กที่ได้รับการวินิจฉัยตาม ICD-10 (สะสม) (6)", "int"),
    ("reached_cum", "เด็กพัฒนาการล่าช้าสะสมทั้งหมดที่มีทะเบียนบ้านในจังหวัด/AHB (7)=(4)+(5)+(6) ไม่นับซ้ำ", "int"),
    ("pct_reached_cum", "อัตราการเข้าถึงบริการ สะสม (ร้อยละ) (8)=(7)*100/(3)", "pct"),
    ("reached_fy", "เด็กพัฒนาการล่าช้าสะสมที่รับบริการปีงบปัจจุบัน (คน) (9)", "int"),
    ("pct_reached_fy", "อัตราการเข้าถึงบริการ ปีงบประมาณปัจจุบัน (ร้อยละ) (10)=(9)*100/(3)", "pct"),
    ("out_of_province", "เด็กพัฒนาการล่าช้าที่ทะเบียนบ้านไม่อยู่ในจังหวัด ปีงบประมาณปัจจุบัน (คน) (11)", "int"),
    ("pct_teda4i", "สัดส่วนเด็กที่ได้รับบริการด้วยรหัส TEDA4I ต่อคาดประมาณ (ร้อยละ) = (4)*100/(3)", "pct"),
    ("pct_icd10", "สัดส่วนเด็กที่ได้รับการวินิจฉัย ICD-10 ต่อคาดประมาณ (ร้อยละ) = (6)*100/(3)", "pct"),
]
ALL_KEYS = [k for k, _, _ in TABLE_KEYS]

META = {
    "id": ID,
    "name_th": "ร้อยละของเด็กปฐมวัยที่มีพัฒนาการล่าช้าเข้าถึงบริการพัฒนาการและสุขภาพจิตที่ได้มาตรฐาน (Coverage)",
    "short": "Coverage",
    "source": {"table": TABLE,
               "bodyTemplate": {"tableName": TABLE, "year": "{year}", "type": "json", "limit": 20000},
               "needsProvince": False},
    "levels": ["country", "region", "province"],
    "groups": None,
    "headline": {"metric": "pct_reached_fy", "num": "reached_fy", "den": "expected"},
    "cards": [
        {"metric": "pct_reached_cum", "label": "เข้าถึงบริการสะสม", "num": "reached_cum", "den": "expected"},
        {"metric": "pct_teda4i", "label": "บริการด้วยรหัส TEDA4I", "num": "served_teda4i", "den": "expected"},
        {"metric": "pct_icd10", "label": "วินิจฉัย ICD-10", "num": "diagnosed_icd10", "den": "expected"},
    ],
    "table": [{"key": k, "label": l, "type": t} for k, l, t in TABLE_KEYS],
    "monthly": False,
    "targets_key": "coverage",
}


# ------------------------------------------------------------------ values model
def derive(c: dict) -> dict:
    d = dict(c)
    calc = {"pct_reached_cum": pct(d.get("reached_cum"), d.get("expected")),
            "pct_reached_fy": pct(d.get("reached_fy"), d.get("expected")),
            "pct_teda4i": pct(d.get("served_teda4i"), d.get("expected")),
            "pct_icd10": pct(d.get("diagnosed_icd10"), d.get("expected"))}
    for k, v in calc.items():
        if d.get(k) is None:
            d[k] = v
    return {k: d.get(k) for k in ALL_KEYS}


def sum_values(items: list[dict]) -> dict:
    c = {k: ssum(v[k] for v in items) for k in COUNT_KEYS}
    prevs = {v["prevalence"] for v in items if v["prevalence"] is not None}
    c["prevalence"] = prevs.pop() if len(prevs) == 1 else None
    return derive(c)


def has_data(values: dict) -> bool:
    return any((values.get(k) or 0) != 0 for k in COUNT_KEYS)


def null_values(values: dict) -> dict:
    return {k: None for k in ALL_KEYS}


def from_excel(xl_values: dict) -> dict:
    return derive(dict(xl_values))


# ------------------------------------------------------------------ fetch / cache
def cache_path(year: int) -> Path:
    return ROOT / "data" / "cache" / ID / str(year) / "all.json"


def fetch_cache(year: int, refresh: bool, log=print) -> dict:
    raw = moph_api.get_raw(TABLE, year, None, refresh=refresh, log=log)
    rows = raw["data"]
    slim = [{k: r[k] for k in ("provcode", "areacode", "hospcode", "b_year", "c_1", "c_2", "c_3", "c_4", "c_5",
                                "c_6", "c_7", "c_9", "c_11", "date_com") if k in r} for r in rows]
    payload = {"schema": 1, "indicator": ID, "table": TABLE, "year": year, "province": None,
               "fetchedAt": raw["fetchedAt"], "asOf": max(r["date_com"] for r in rows),
               "rawRowCount": len(rows), "rowCount": len(slim), "rows": slim}
    p = cache_path(year)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"  cache written  {p.relative_to(ROOT)}  ({len(slim)} rows, asOf {fmt_asof(payload['asOf'])})")
    return payload


def load_cache(year: int):
    p = cache_path(year)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ------------------------------------------------------------------ API-side views
def _row_values(r: dict, c11_ok: bool) -> dict:
    c = {k: r.get(raw) for k, raw in RAWMAP.items()}
    if not c11_ok:
        c["out_of_province"] = None     # column not populated (2569: all zero; Excel has no (11))
    return derive(c)


def api_views(cache, ctx) -> list[dict]:
    """country (rows=13 regions), region N (rows=provinces), province P (rows=districts, when the table is by district)."""
    rows = cache["rows"]
    prov_region = ctx["prov_region"]                     # '15' -> 4
    c11_ok = any(r.get("c_11") for r in rows)
    by_prov: dict = {}
    for r in rows:
        by_prov.setdefault(r["provcode"], []).append(_row_values(r, c11_ok))
    prov_vals = {p: sum_values(v) for p, v in by_prov.items()}
    views = []
    reg_items: dict = {}
    for p, v in prov_vals.items():
        reg_items.setdefault(str(prov_region[p]), []).append(v)
    views.append({"level": "country", "scope": "TH",
                  "rows": [{"code": r, "values": sum_values(v)} for r, v in sorted(reg_items.items(), key=lambda x: int(x[0]))]})
    for reg in sorted(reg_items, key=int):
        if reg not in ctx["drill_regions"]:      # only the site's home region is published (single-site scope)
            continue
        views.append({"level": "region", "scope": reg,
                      "rows": [{"code": p, "values": prov_vals[p]} for p in sorted(prov_vals, key=int)
                               if str(prov_region[p]) == reg]})
    # district level: only when the table carries every district of the province (2569)
    for p in ctx["drill_provinces"]:
        rs = [r for r in rows if r["provcode"] == p]
        by_d: dict = {}
        for r in rs:
            by_d.setdefault(r["areacode"][:4], []).append(_row_values(r, c11_ok))
        if len(by_d) == ctx["n_districts"][p]:
            views.append({"level": "province", "scope": p,
                          "rows": [{"code": d, "values": sum_values(v)} for d, v in sorted(by_d.items())]})
    return views


# ------------------------------------------------------------------ validation
def check_values(values: dict, where: str) -> list[tuple[str, str]]:
    issues = []
    v = values
    for k, n, d in [("pct_reached_cum", "reached_cum", "expected"), ("pct_reached_fy", "reached_fy", "expected"),
                    ("pct_teda4i", "served_teda4i", "expected"), ("pct_icd10", "diagnosed_icd10", "expected")]:
        if v.get(n) is None or v.get(d) is None:
            continue
        if v[d] == 0:
            if v.get(k) not in (None, 0):
                issues.append(("hard", f"{where} {k}={v[k]} but expected=0"))
        elif v.get(k) is not None and not close(v[k], 100.0 * v[n] / v[d]):
            issues.append(("hard", f"{where} {k}={v[k]} != {v[n]}/{v[d]}*100"))
    if None not in (v.get("population"), v.get("prevalence"), v.get("expected")):
        exp = v["population"] * v["prevalence"] / 100
        if abs(exp - v["expected"]) > max(1.0, 0.001 * v["population"]):
            issues.append(("warn", f"{where} expected {v['expected']} != population*prevalence/100 = {exp:.1f}"))
    return issues


def compare(api: dict, xl: dict, xl_keys) -> list[str]:
    bad = []
    for k in xl_keys:
        a, x = api.get(k), xl.get(k)
        if x is None:
            continue
        if k in PCT_KEYS or k == "prevalence":
            if k in ("pct_reached_cum", "pct_reached_fy") and api.get("expected") == 0:
                if x not in (0, None):
                    bad.append(f"{k}: api den=0 vs excel {x}")
                continue
            if not close(a, x):
                bad.append(f"{k}: api {a} vs excel {x}")
        elif a != x:
            bad.append(f"{k}: api {a} vs excel {x}")
    return bad
