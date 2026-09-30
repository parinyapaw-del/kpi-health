"""Shared helpers for the population plugins (pop / typearea / pyramid).

All three MOPH tables share the row shape hospcode x areacode(8) x b_year and the same subdistrict rule as DSPM:
the HDC "ตำบล" report groups by the tambon of the reporting unit (hospcode), which we derive as the areacode[:6]
where that hospcode carries the largest population ("unit6").  Verified against the user's HDC exports
(2569, อำเภอเมืองอ่างทอง: unit-tambon grouping == Excel, plain areacode[:6] != Excel for s_pop_sex_age).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def unit_tambon(rows: list[dict], weight) -> dict:
    """hospcode -> areacode[:6] with the largest weight(row) (ties -> lowest code)."""
    w: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        w[r["hospcode"]][r["areacode"][:6]] += weight(r)
    return {h: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for h, c in w.items()}


def aggregate(rows: list[dict], fields: list[str], weight, extra_key=None) -> tuple[list[list], dict]:
    """Sum `fields` by (areacode[:6], unit6[, extra_key(row)]).  Returns (rows, units)."""
    units = unit_tambon(rows, weight)
    agg: dict[tuple, list] = {}
    for r in rows:
        key = (r["areacode"][:6], units[r["hospcode"]]) + ((extra_key(r),) if extra_key else ())
        a = agg.setdefault(key, [0] * len(fields))
        for i, f in enumerate(fields):
            a[i] += r.get(f) or 0
    out = [list(k) + vals for k, vals in sorted(agg.items())]
    return out, dict(sorted(units.items()))


def write_cache(path: Path, payload: dict, log=print) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"  cache written  {path.relative_to(ROOT)}  ({payload['rowCount']} rows, asOf {payload['asOf']})")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def group_sums(cache: dict, keyfn, nkeys: int = 2) -> dict:
    """{key: {field: sum}} over cache rows; keyfn(a6, u6) -> key | None.  Rows are [a6, u6, <fields...>]."""
    fields = cache["fields"]
    out: dict = {}
    for row in cache["rows"]:
        k = keyfn(row[0], row[1])
        if k is None:
            continue
        s = out.setdefault(k, dict.fromkeys(fields, 0))
        for f, v in zip(fields, row[nkeys:]):
            s[f] += v
    return out


def scope_keyfns(ctx, level: str, scope: str):
    """keyfn for the 4 home-path views (same rules as dspm.api_views)."""
    prov_region = ctx["prov_region"]
    if level == "country":
        return lambda a6, u6: (str(prov_region[a6[:2]]) if a6[:2] in prov_region else None)
    if level == "region":
        return lambda a6, u6: (a6[:2] if str(prov_region.get(a6[:2])) == scope else None)
    if level == "province":
        return lambda a6, u6: (a6[:4] if a6[:2] == scope else None)
    return lambda a6, u6: (u6 if a6[:4] == scope else None)     # district: rows = unit tambons
