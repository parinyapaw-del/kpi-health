"""denom05 plugin — ตัวหารเด็กปฐมวัย 0–5 ปี: เทียบฐานประชากรที่ใช้เป็นตัวหารจากทุกแหล่งในระบบ

Not fetched from the API itself: it is assembled at build time from
  pop       (s_pop_sex_age)     -> ประชากรกลางปี HDC <1, 1-4, 0-4, 5-9 ปี (typearea 1+3)
  typearea  (s_persontype)      -> ประชากรกลางปีทุกอายุ (1c+3c)
  pyramid   (s_person_pyramid)  -> 0-4 ปี จากรายงานปิรามิด (home province only)
  dspm      (published dataset) -> เป้าหมาย DSPM 5 กลุ่มอายุ (9/18/30/42/60 เดือน) + คัดกรอง
  coverage  (published dataset) -> ตัวหาร Coverage: เด็กปฐมวัย 0-5 ปี (1) และคาดประมาณเด็กล่าช้า (3)
Every ratio is ×100 so the web's pct machinery (colour rules off: no target) can show it later.

NOT PUBLISHED on the web yet (2026-09-30) — see scripts/population.py.
"""
from __future__ import annotations

from .common import add, pct, ssum

ID = "denom05"
COUNT_KEYS = ["pop_lt1", "pop_1_4", "pop_0_4", "pop_5_9", "pyramid_0_4", "midyear_all",
              "dspm_target", "dspm_t9", "dspm_t18", "dspm_t30", "dspm_t42", "dspm_t60", "dspm_screened",
              "cov_population", "cov_expected"]
DERIVED = ["pop_0_5_est"]
PCT_KEYS = ["pct_dspm_target", "pct_screened_of_pop", "pct_cov_pop", "pct_cov_pop_05", "pct_pyramid",
            "pct_child_share"]
TABLE_KEYS = [
    ("pop_lt1", "ประชากรกลางปี HDC น้อยกว่า 1 ปี (คน)", "int"),
    ("pop_1_4", "ประชากรกลางปี HDC 1-4 ปี (คน)", "int"),
    ("pop_0_4", "ประชากรกลางปี HDC 0-4 ปี (คน) = <1 + 1-4", "int"),
    ("pop_5_9", "ประชากรกลางปี HDC 5-9 ปี (คน)", "int"),
    ("pop_0_5_est", "ประมาณการเด็ก 0-5 ปี = 0-4 + (5-9)/5 (คน) [INFERRED]", "int"),
    ("pyramid_0_4", "ปิรามิดประชากร 0-4 ปี (คน) เฉพาะจังหวัดหลัก", "int"),
    ("midyear_all", "ประชากรกลางปีทุกอายุ TYPEAREA 1c+3c (คน)", "int"),
    ("dspm_target", "เป้าหมาย DSPM รวม 5 กลุ่มอายุ (คน)", "int"),
    ("dspm_t9", "เป้าหมาย DSPM 9 เดือน", "int"), ("dspm_t18", "เป้าหมาย DSPM 18 เดือน", "int"),
    ("dspm_t30", "เป้าหมาย DSPM 30 เดือน", "int"), ("dspm_t42", "เป้าหมาย DSPM 42 เดือน", "int"),
    ("dspm_t60", "เป้าหมาย DSPM 60 เดือน", "int"),
    ("dspm_screened", "คัดกรอง DSPM รวม (คน)", "int"),
    ("cov_population", "ตัวหาร Coverage: เด็กปฐมวัย 0-5 ปี (1) (คน)", "int"),
    ("cov_expected", "Coverage: คาดประมาณเด็กพัฒนาการล่าช้า (3) (คน)", "int"),
    ("pct_dspm_target", "เป้าหมาย DSPM ÷ ประชากร 0-4 ปี (ร้อยละ)", "pct"),
    ("pct_screened_of_pop", "คัดกรอง DSPM ÷ ประชากร 0-4 ปี (ร้อยละ)", "pct"),
    ("pct_cov_pop", "ตัวหาร Coverage (1) ÷ ประชากร 0-4 ปี (ร้อยละ)", "pct"),
    ("pct_cov_pop_05", "ตัวหาร Coverage (1) ÷ ประมาณการ 0-5 ปี (ร้อยละ)", "pct"),
    ("pct_pyramid", "ปิรามิด 0-4 ÷ ประชากร 0-4 ปี (ร้อยละ)", "pct"),
    ("pct_child_share", "ประชากร 0-4 ปี ÷ ประชากรทุกอายุ (ร้อยละ)", "pct"),
]
ALL_KEYS = [k for k, _, _ in TABLE_KEYS]

META = {
    "id": ID,
    "name_th": "ตัวหารเด็กปฐมวัย 0–5 ปี: เทียบฐานประชากร HDC กับเป้าหมาย DSPM และตัวหาร Coverage",
    "short": "ตัวหาร 0–5",
    "source": {"table": None, "derivedFrom": ["pop", "typearea", "pyramid", "dspm", "coverage"], "needsProvince": False},
    "levels": ["country", "region", "province", "district"],
    "groups": None,
    "headline": {"metric": "pct_dspm_target", "num": "dspm_target", "den": "pop_0_4"},
    "cards": [
        {"metric": "pct_cov_pop", "label": "ตัวหาร Coverage (1) ต่อประชากร 0-4", "num": "cov_population", "den": "pop_0_4"},
        {"metric": "pct_child_share", "label": "สัดส่วนเด็ก 0-4 ในประชากรกลางปี", "num": "pop_0_4", "den": "midyear_all"},
        {"metric": "pct_pyramid", "label": "ปิรามิด 0-4 ต่อประชากร 0-4", "num": "pyramid_0_4", "den": "pop_0_4"},
    ],
    "table": [{"key": k, "label": l, "type": t} for k, l, t in TABLE_KEYS],
    "monthly": False,
    "targets_key": "denom05",
    "published": False,
    "notes": ["ประชากร 0-4 ปี HDC = typearea 1+3 หลัง cleansing ตามตาราง s_pop_sex_age",
              "เป้าหมาย DSPM = เด็กที่อายุครบ 9/18/30/42/60 เดือนในปีงบ (5 birth cohort) จึงไม่เท่ากับประชากร 0-4 ปีโดยนิยาม",
              "ตัวหาร Coverage (1) มาจากตาราง s_child0_5_pshyche_develop_coverage ซึ่งใช้ฐานประชากรต่างจาก HDC 0-4 [INFERRED]"],
}


def derive(c: dict) -> dict:
    d = dict(c)
    if d.get("pop_0_4") is None:
        d["pop_0_4"] = add(d.get("pop_lt1"), d.get("pop_1_4"))
    if d.get("pop_0_5_est") is None and d.get("pop_0_4") is not None and d.get("pop_5_9") is not None:
        d["pop_0_5_est"] = round(d["pop_0_4"] + d["pop_5_9"] / 5)
    if d.get("dspm_target") is None:
        d["dspm_target"] = ssum(d.get(k) for k in ("dspm_t9", "dspm_t18", "dspm_t30", "dspm_t42", "dspm_t60"))
    calc = {"pct_dspm_target": pct(d.get("dspm_target"), d.get("pop_0_4")),
            "pct_screened_of_pop": pct(d.get("dspm_screened"), d.get("pop_0_4")),
            "pct_cov_pop": pct(d.get("cov_population"), d.get("pop_0_4")),
            "pct_cov_pop_05": pct(d.get("cov_population"), d.get("pop_0_5_est")),
            "pct_pyramid": pct(d.get("pyramid_0_4"), d.get("pop_0_4")),
            "pct_child_share": pct(d.get("pop_0_4"), d.get("midyear_all"))}
    for k, v in calc.items():
        if d.get(k) is None:
            d[k] = v
    return {k: d.get(k) for k in ALL_KEYS}


def sum_values(items: list[dict]) -> dict:
    return derive({k: ssum(v[k] for v in items) for k in COUNT_KEYS})


def has_data(values: dict) -> bool:
    return (values.get("pop_0_4") or 0) != 0


def null_values(values: dict) -> dict:
    return {k: None for k in ALL_KEYS}


def zero_values() -> dict:
    return derive({k: 0 for k in COUNT_KEYS})


def assemble(rows_pop: dict, rows_ta: dict, pyramid04: dict, dspm_rows: dict | None, cov_rows: dict | None,
             codes: list[str]) -> list[dict]:
    """Build one denom05 row per child code from the other indicators' row maps (code -> values)."""
    out = []
    for c in codes:
        p = rows_pop.get(c)
        t = rows_ta.get(c)
        d = dspm_rows.get(c) if dspm_rows else None
        cv = cov_rows.get(c) if cov_rows else None
        vals = {
            "pop_lt1": p["lt1"]["pop"] if p else None, "pop_1_4": p["a1_4"]["pop"] if p else None,
            "pop_0_4": p["a0_4"]["pop"] if p else None, "pop_5_9": p["a5_9"]["pop"] if p else None,
            "pyramid_0_4": pyramid04.get(c), "midyear_all": t["midyear"] if t else None,
            "dspm_t9": d["m9"]["target"] if d else None, "dspm_t18": d["m18"]["target"] if d else None,
            "dspm_t30": d["m30"]["target"] if d else None, "dspm_t42": d["m42"]["target"] if d else None,
            "dspm_t60": d["m60"]["target"] if d else None, "dspm_target": d["total"]["target"] if d else None,
            "dspm_screened": d["total"]["screened"] if d else None,
            "cov_population": cv["population"] if cv else None, "cov_expected": cv["expected"] if cv else None,
        }
        out.append({"code": c, "values": derive(vals)})
    return out


def check_values(v: dict, where: str) -> list[tuple[str, str]]:
    issues = []
    if None not in (v.get("pop_lt1"), v.get("pop_1_4"), v.get("pop_0_4")) and \
            v["pop_0_4"] != v["pop_lt1"] + v["pop_1_4"]:
        issues.append(("hard", f"{where} pop_0_4 != lt1 + 1-4"))
    ts = [v.get(k) for k in ("dspm_t9", "dspm_t18", "dspm_t30", "dspm_t42", "dspm_t60")]
    if None not in ts and v.get("dspm_target") is not None and sum(ts) != v["dspm_target"]:
        issues.append(("hard", f"{where} dspm_target {v['dspm_target']} != sum of cohorts {sum(ts)}"))
    for k, n, d in (("pct_dspm_target", "dspm_target", "pop_0_4"), ("pct_cov_pop", "cov_population", "pop_0_4"),
                    ("pct_pyramid", "pyramid_0_4", "pop_0_4"), ("pct_child_share", "pop_0_4", "midyear_all")):
        if v.get(n) is None or v.get(d) in (None, 0):
            continue
        if v.get(k) is None or abs(v[k] - 100.0 * v[n] / v[d]) > 0.06:
            issues.append(("hard", f"{where} {k}={v.get(k)} != {n}/{d}"))
    return issues
