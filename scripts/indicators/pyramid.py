"""pyramid helper — ปิรามิดประชากร (MOPH table s_person_pyramid), home province only.

Nationwide this table is 1.58 M rows (21 age groups x hospcode x village) so it is fetched per province and only
for the site's home province.  It is used for reconciliation with the HDC pyramid export and as a second
reading of the 0-4 population (same source population as s_pop_sex_age, but a separate HDC processing run, so
totals may differ by a few persons — e.g. Angthong 2569: pyramid 5,557 vs sex-age 5,572 for 0-4 ปี).
Not an indicator tab of its own.
"""
from __future__ import annotations

from pathlib import Path

from ..loaders import moph_api
from .common import fmt_asof
from .popcommon import ROOT, aggregate, load_json, write_cache

TABLE = "s_person_pyramid"
FIELDS = ["male", "female", "total"]
GROUPS = ["0-4 ปี", "5-9 ปี", "10-14 ปี", "15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-44 ปี",
          "45-49 ปี", "50-54 ปี", "55-59 ปี", "60-64 ปี", "65-69 ปี", "70-74 ปี", "75-79 ปี", "80-84 ปี",
          "85-89 ปี", "90-94 ปี", "95-99 ปี", "100 ปีขึ้นไป"]


def cache_path(year: int, province: str) -> Path:
    return ROOT / "data" / "cache" / "pyramid" / str(year) / f"{province}.json"


def fetch_cache(year: int, province: str, refresh: bool, log=print) -> dict:
    raw = moph_api.get_raw(TABLE, year, province, refresh=refresh, log=log)
    rows = raw["data"]
    weight = lambda r: r.get("total") or 0
    agg, units = aggregate(rows, FIELDS, weight, extra_key=lambda r: r["groupname"])
    payload = {"schema": 1, "indicator": "pyramid", "table": TABLE, "year": year, "province": province,
               "fetchedAt": raw["fetchedAt"], "asOf": fmt_asof(max(r["date_com"] for r in rows)),
               "rawRowCount": len(rows), "rowCount": len(agg), "units": units, "fields": FIELDS,
               "rowFormat": ["areacode6", "unit6", "groupname", "<fields...>"], "rows": agg}
    write_cache(cache_path(year, province), payload, log)
    return payload


def load_cache(year: int, province: str):
    return load_json(cache_path(year, province))


def group_totals(cache, keyfn, groupname: str) -> dict:
    """{key: total} for one age group; keyfn(a6, u6) -> key | None."""
    out: dict = {}
    for a6, u6, g, m, f, t in cache["rows"]:
        if g != groupname:
            continue
        k = keyfn(a6, u6)
        if k is None:
            continue
        out[k] = out.get(k, 0) + t
    return out
