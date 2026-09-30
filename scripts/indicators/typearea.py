"""typearea plugin — ประชากรแยกตามหน่วยบริการและชนิดการอยู่อาศัย (MOPH table s_persontype).

API: 1 raw row = hospcode x areacode(8) x b_year with type1..type5 (ก่อน cleansing) and type1c..type5c (หลัง cleansing).
No `province` needed: ~12k rows / 1 s per year for the whole country (Bangkok present but type1c = 0).
TYPEAREA: 1 = มีชื่อในทะเบียนบ้านและอยู่จริง · 2 = มีชื่อในทะเบียนบ้านแต่ไม่อยู่จริง · 3 = อยู่จริงแต่ทะเบียนบ้านอยู่นอกเขต ·
4 = อาศัยนอกเขตและทะเบียนบ้านอยู่นอกเขต (มารับบริการ) · 5 = อื่น ๆ.  ประชากรกลางปี HDC = type1c + type3c.

NOT PUBLISHED on the web yet (2026-09-30) — see scripts/population.py.
"""
from __future__ import annotations

from pathlib import Path

from ..loaders import moph_api
from .common import add, fmt_asof, pct, ssum
from .popcommon import ROOT, aggregate, group_sums, load_json, scope_keyfns, write_cache

ID = "typearea"
TABLE = "s_persontype"
RAW_FIELDS = [f"type{i}" for i in range(1, 6)] + [f"type{i}c" for i in range(1, 6)]
TYPE_LABEL = {1: "มีชื่อในทะเบียนบ้าน อยู่จริง", 2: "มีชื่อในทะเบียนบ้าน ไม่อยู่จริง",
              3: "อยู่จริง ทะเบียนบ้านนอกเขต", 4: "อาศัยและทะเบียนบ้านนอกเขต", 5: "อื่น ๆ"}

COUNT_KEYS = RAW_FIELDS + ["raw_in_area", "midyear", "registered", "all_c"]
PCT_KEYS = ["pct_midyear_of_raw", "pct_type3", "pct_type2", "pct_type4"]
TABLE_KEYS = (
    [(f"type{i}", f"ก่อน cleansing TYPEAREA {i} ({TYPE_LABEL[i]})", "int") for i in range(1, 6)]
    + [(f"type{i}c", f"หลัง cleansing TYPEAREA {i} ({TYPE_LABEL[i]})", "int") for i in range(1, 6)]
    + [("raw_in_area", "ในเขตก่อน cleansing (1+3)", "int"),
       ("midyear", "ประชากรกลางปี HDC (1c+3c)", "int"),
       ("registered", "ทะเบียนบ้านในเขต หลัง cleansing (1c+2c)", "int"),
       ("all_c", "รวมทุกประเภท หลัง cleansing (1c–5c)", "int"),
       ("pct_midyear_of_raw", "ร้อยละประชากรกลางปีหลัง cleansing ต่อก่อน cleansing (1c+3c)/(1+3)", "pct"),
       ("pct_type3", "ร้อยละทะเบียนบ้านนอกเขตในประชากรกลางปี 3c/(1c+3c)", "pct"),
       ("pct_type2", "ร้อยละมีชื่อแต่ไม่อยู่จริง 2c/(1c+2c)", "pct"),
       ("pct_type4", "ร้อยละผู้มารับบริการจากนอกเขต 4c/(1c–5c)", "pct")]
)
ALL_KEYS = [k for k, _, _ in TABLE_KEYS]

META = {
    "id": ID,
    "name_th": "ประชากรแยกตามหน่วยบริการและชนิดการอยู่อาศัย (TYPEAREA)",
    "short": "TYPEAREA",
    "source": {"table": TABLE,
               "bodyTemplate": {"tableName": TABLE, "year": "{year}", "type": "json", "limit": 10000},
               "needsProvince": False},
    "levels": ["country", "region", "province", "district"],
    "groups": None,
    "headline": {"metric": "pct_midyear_of_raw", "num": "midyear", "den": "raw_in_area"},
    "cards": [
        {"metric": "pct_type3", "label": "ทะเบียนบ้านนอกเขต (3) ในประชากรกลางปี", "num": "type3c", "den": "midyear"},
        {"metric": "pct_type2", "label": "มีชื่อแต่ไม่อยู่จริง (2)", "num": "type2c", "den": "registered"},
        {"metric": "pct_type4", "label": "ผู้มารับบริการจากนอกเขต (4)", "num": "type4c", "den": "all_c"},
    ],
    "table": [{"key": k, "label": l, "type": t} for k, l, t in TABLE_KEYS],
    "monthly": False,
    "targets_key": "typearea",
    "published": False,
    "notes": ["ประชากรกลางปี HDC = TYPEAREA 1 + 3 หลัง cleansing ความซ้ำซ้อน",
              "กทม. (เขตสุขภาพที่ 13) มีข้อมูลก่อน cleansing แต่ type1c = 0 ทุกปี"],
}


# ------------------------------------------------------------------ values model
def derive(c: dict) -> dict:
    d = dict(c)
    if d.get("raw_in_area") is None:
        d["raw_in_area"] = add(d.get("type1"), d.get("type3"))
    if d.get("midyear") is None:
        d["midyear"] = add(d.get("type1c"), d.get("type3c"))
    if d.get("registered") is None:
        d["registered"] = add(d.get("type1c"), d.get("type2c"))
    if d.get("all_c") is None:
        d["all_c"] = add(*(d.get(f"type{i}c") for i in range(1, 6)))
    calc = {"pct_midyear_of_raw": pct(d.get("midyear"), d.get("raw_in_area")),
            "pct_type3": pct(d.get("type3c"), d.get("midyear")),
            "pct_type2": pct(d.get("type2c"), d.get("registered")),
            "pct_type4": pct(d.get("type4c"), d.get("all_c"))}
    for k, v in calc.items():
        if d.get(k) is None:
            d[k] = v
    return {k: d.get(k) for k in ALL_KEYS}


def values_from_sums(sums: dict) -> dict:
    return derive({f: sums.get(f) for f in RAW_FIELDS})


def sum_values(items: list[dict]) -> dict:
    return derive({k: ssum(v[k] for v in items) for k in RAW_FIELDS})


def has_data(values: dict) -> bool:
    return any((values.get(k) or 0) != 0 for k in RAW_FIELDS)


def null_values(values: dict) -> dict:
    return {k: None for k in ALL_KEYS}


# ------------------------------------------------------------------ fetch / cache
def cache_path(year: int) -> Path:
    return ROOT / "data" / "cache" / ID / str(year) / "all.json"


def fetch_cache(year: int, refresh: bool, log=print) -> dict:
    raw = moph_api.get_raw(TABLE, year, None, refresh=refresh, log=log)
    rows = raw["data"]
    weight = lambda r: (r.get("type1c") or 0) + (r.get("type3c") or 0)
    agg, units = aggregate(rows, RAW_FIELDS, weight)
    payload = {"schema": 1, "indicator": ID, "table": TABLE, "year": year, "province": None,
               "fetchedAt": raw["fetchedAt"], "asOf": fmt_asof(max(r["date_com"] for r in rows)),
               "rawRowCount": len(rows), "rowCount": len(agg),
               "provinces": sorted({r["areacode"][:2] for r in rows}),
               "units": units, "fields": RAW_FIELDS, "rowFormat": ["areacode6", "unit6", "<fields...>"], "rows": agg}
    write_cache(cache_path(year), payload, log)
    return payload


def load_cache(year: int):
    return load_json(cache_path(year))


# ------------------------------------------------------------------ views
def api_views(cache, ctx) -> list[dict]:
    home = ctx["home"]
    views = []
    for level, scope in (("country", "TH"), ("region", str(home["region"])), ("province", home["province"]),
                         ("district", home["district"])):
        sums = group_sums(cache, scope_keyfns(ctx, level, scope))
        views.append({"level": level, "scope": scope,
                      "rows": [{"code": c, "values": values_from_sums(s)} for c, s in sorted(sums.items())]})
    return views


# ------------------------------------------------------------------ validation
def check_values(v: dict, where: str) -> list[tuple[str, str]]:
    issues = []
    for i in range(1, 6):
        a, b = v.get(f"type{i}"), v.get(f"type{i}c")
        if None not in (a, b) and b > a:
            issues.append(("warn", f"{where} type{i}c {b} > type{i} {a} (cleansed > raw)"))
    for k, n, d in (("pct_midyear_of_raw", "midyear", "raw_in_area"), ("pct_type3", "type3c", "midyear"),
                    ("pct_type2", "type2c", "registered"), ("pct_type4", "type4c", "all_c")):
        if v.get(n) is None or v.get(d) in (None, 0):
            continue
        if v.get(k) is None or abs(v[k] - 100.0 * v[n] / v[d]) > 0.06:
            issues.append(("hard", f"{where} {k}={v.get(k)} != {n}/{d}"))
    return issues
