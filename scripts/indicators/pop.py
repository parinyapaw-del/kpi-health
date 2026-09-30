"""pop plugin — ประชากรกลางปี HDC จำแนกเพศ กลุ่มอายุ (MOPH table s_pop_sex_age).

API: 1 raw row = hospcode x areacode(8) x b_year with male_g1..female_g22 (22 age bands, typearea 1+3 population).
No `province` needed: the whole country is ~84k rows / ~12 s per year (Bangkok = 0 rows every year).
Cache = (areacode[:6], unit tambon) with all 44 fields summed.  Groups (age bands) are sums of raw bands.

NOT PUBLISHED on the web yet (2026-09-30): data + metadata are prepared under data/prepared/ by
scripts/population.py so the tab can be switched on later without re-fetching.
"""
from __future__ import annotations

from pathlib import Path

from ..loaders import moph_api
from .common import add, fmt_asof, pct, ssum
from .popcommon import ROOT, aggregate, group_sums, load_json, scope_keyfns, write_cache

ID = "pop"
TABLE = "s_pop_sex_age"

# raw band suffix -> HDC header (row 2 of the "ประชากรจำแนกเพศ กลุ่มอายุรายปี" export)
BANDS = [("g1", "น้อยกว่า 1 ปี"), ("g2", "1-4 ปี"), ("g3", "5-9 ปี"), ("g4", "10-14 ปี"), ("g5", "15-19 ปี"),
         ("g6", "20-24 ปี"), ("g7", "25-29 ปี"), ("g8", "30-34 ปี"), ("g9", "35-39 ปี"), ("g10", "40-44 ปี"),
         ("g11", "45-49 ปี"), ("g12", "50-54 ปี"), ("g13", "55-59 ปี"), ("g14", "60-64 ปี"), ("g15", "65-69 ปี"),
         ("g16", "70-74 ปี"), ("g17", "75-79 ปี"), ("g18", "80-84 ปี"), ("g19", "85-89 ปี"), ("g20", "90-94 ปี"),
         ("g21", "95-99 ปี"), ("g22", "ตั้งแต่ 100 ปีขึ้นไป")]
BAND_LABEL = dict(BANDS)
RAW_FIELDS = [f"{s}_{g}" for g, _ in BANDS for s in ("male", "female")]

# group key -> (label, raw bands)
GROUP_DEF = {
    "total": ("รวมทุกอายุ", [g for g, _ in BANDS]),
    "a0_4": ("0-4 ปี (เด็กปฐมวัย)", ["g1", "g2"]),
    "lt1": ("น้อยกว่า 1 ปี", ["g1"]),
    "a1_4": ("1-4 ปี", ["g2"]),
    "a5_9": ("5-9 ปี", ["g3"]),
    "a10_14": ("10-14 ปี", ["g4"]),
    "a15_59": ("15-59 ปี (วัยทำงาน)", [f"g{i}" for i in range(5, 14)]),
    "a60p": ("60 ปีขึ้นไป (ผู้สูงอายุ)", [f"g{i}" for i in range(14, 23)]),
}
GROUPS = list(GROUP_DEF)

COUNT_KEYS = ["pop", "male", "female"]
BAND_KEYS = [f"band_{g}" for g, _ in BANDS]           # populated in group 'total' only
PCT_KEYS = ["pct_share", "pct_female"]
TABLE_KEYS = [
    ("pop", "ประชากร (คน)", "int"), ("male", "ชาย", "int"), ("female", "หญิง", "int"),
    ("pct_share", "ร้อยละต่อประชากรกลางปีทุกอายุ", "pct"), ("pct_female", "ร้อยละเพศหญิง", "pct"),
    ("pop_total", "ประชากรกลางปีทุกอายุ (คน)", "int"),
] + [(f"band_{g}", f"{lab} (รวม)", "int") for g, lab in BANDS]
ALL_KEYS = [k for k, _, _ in TABLE_KEYS]

META = {
    "id": ID,
    "name_th": "ประชากรกลางปี HDC จำแนกเพศ กลุ่มอายุ (typearea 1+3)",
    "short": "ประชากร",
    "source": {"table": TABLE,
               "bodyTemplate": {"tableName": TABLE, "year": "{year}", "type": "json", "limit": 10000},
               "needsProvince": False},
    "levels": ["country", "region", "province", "district"],
    "groups": [{"key": g, "label": GROUP_DEF[g][0]} for g in GROUPS],
    "headline": {"metric": "pct_share", "num": "pop", "den": "pop_total"},
    "cards": [{"metric": "pct_female", "label": "สัดส่วนเพศหญิง", "num": "female", "den": "pop"}],
    "table": [{"key": k, "label": l, "type": t} for k, l, t in TABLE_KEYS],
    "monthly": False,
    "targets_key": "pop",
    "published": False,
    "notes": ["ประชากรกลางปี HDC = ผู้ที่มีสถานะ typearea 1 หรือ 3 (หลัง cleansing) ในปีงบนั้น",
              "กทม. (เขตสุขภาพที่ 13) ไม่มีข้อมูลในตารางนี้ทุกปี",
              "ระดับตำบล = ตำบลของหน่วยบริการ (hospcode) ตามรายงาน HDC ไม่ใช่ตำบลตามรหัสบ้าน"],
}


# ------------------------------------------------------------------ values model
def values_from_sums(sums: dict) -> dict:
    tot = ssum(sums.get(f) for f in RAW_FIELDS)
    out = {}
    for g, (_, bands) in GROUP_DEF.items():
        m = ssum(sums.get(f"male_{b}") for b in bands)
        f = ssum(sums.get(f"female_{b}") for b in bands)
        c = {"male": m, "female": f, "pop": add(m, f), "pop_total": tot}
        if g == "total":
            for b, _ in BANDS:
                c[f"band_{b}"] = add(sums.get(f"male_{b}"), sums.get(f"female_{b}"))
        out[g] = derive(c)
    return out


def derive(c: dict) -> dict:
    d = dict(c)
    if d.get("pct_share") is None:
        d["pct_share"] = pct(d.get("pop"), d.get("pop_total"))
    if d.get("pct_female") is None:
        d["pct_female"] = pct(d.get("female"), d.get("pop"))
    return {k: d.get(k) for k in ALL_KEYS}


def sum_values(items: list[dict]) -> dict:
    out = {}
    for g in GROUPS:
        c = {k: ssum(v[g][k] for v in items) for k in COUNT_KEYS + ["pop_total"] + BAND_KEYS}
        out[g] = derive(c)
    return out


def has_data(values: dict) -> bool:
    return any((v[k] or 0) != 0 for v in values.values() for k in COUNT_KEYS)


def null_values(values: dict) -> dict:
    return {g: {k: None for k in ALL_KEYS} for g in values}


# ------------------------------------------------------------------ fetch / cache
def cache_path(year: int) -> Path:
    return ROOT / "data" / "cache" / ID / str(year) / "all.json"


def fetch_cache(year: int, refresh: bool, log=print) -> dict:
    raw = moph_api.get_raw(TABLE, year, None, refresh=refresh, log=log)
    rows = raw["data"]
    weight = lambda r: sum(r.get(f) or 0 for f in RAW_FIELDS)
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
    """Home-path views: country/TH (regions), region/<home> (provinces), province/<home> (districts),
    district/<home> (unit tambons)."""
    home = ctx["home"]
    views = []
    for level, scope in (("country", "TH"), ("region", str(home["region"])), ("province", home["province"]),
                         ("district", home["district"])):
        sums = group_sums(cache, scope_keyfns(ctx, level, scope))
        views.append({"level": level, "scope": scope,
                      "rows": [{"code": c, "values": values_from_sums(s)} for c, s in sorted(sums.items())]})
    return views


# ------------------------------------------------------------------ validation
def check_values(values: dict, where: str) -> list[tuple[str, str]]:
    issues = []
    for g, v in values.items():
        w = f"{where} [{g}]"
        if None not in (v.get("male"), v.get("female"), v.get("pop")) and v["pop"] != v["male"] + v["female"]:
            issues.append(("hard", f"{w} pop {v['pop']} != male+female"))
        for k, n, d in (("pct_share", "pop", "pop_total"), ("pct_female", "female", "pop")):
            if v.get(n) is None or v.get(d) in (None, 0):
                continue
            if v.get(k) is None or abs(v[k] - 100.0 * v[n] / v[d]) > 0.06:
                issues.append(("hard", f"{w} {k}={v.get(k)} != {n}/{d}"))
    t, a04, l1, a14 = values["total"], values["a0_4"], values["lt1"], values["a1_4"]
    if None not in (a04.get("pop"), l1.get("pop"), a14.get("pop")) and a04["pop"] != l1["pop"] + a14["pop"]:
        issues.append(("hard", f"{where} a0_4 {a04['pop']} != lt1+a1_4"))
    if t.get("pop") is not None and t.get("pop_total") is not None and t["pop"] != t["pop_total"]:
        issues.append(("hard", f"{where} total pop {t['pop']} != pop_total {t['pop_total']}"))
    if all(t.get(k) is not None for k in BAND_KEYS) and t.get("pop") is not None and \
            sum(t[k] for k in BAND_KEYS) != t["pop"]:
        issues.append(("hard", f"{where} sum of 22 bands != total pop"))
    return issues
