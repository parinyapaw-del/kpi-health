"""Build the web data layer  site/data/<site>/  from the aggregate cache (API) + HDC Excel (oracle).

`build_datasets()` is shared with verify.py: it returns every dataset the API cache can produce (`api`), every
dataset read from Excel (`excel`), and the `published` selection per the source matrix (all levels = api since
2026-09-30, Excel is the oracle only).

Phase 2 (web_spec_phase2.md §4): scope = health region 4 -> its 8 provinces -> every district -> every subdistrict
(DSPM; Coverage stops at district rows because its API table is one row per district).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import build_lookup
from .indicators import coverage, dspm
from .indicators.common import fmt_asof
from .loaders import xlsx_hdc

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = {"dspm": dspm, "coverage": coverage}
# source matrix: which source publishes which level (Excel is verify-only)
SOURCE_LEVELS = {
    "dspm": {"country": "api", "region": "api", "province": "api", "district": "api"},
    "coverage": {"country": "api", "region": "api", "province": "api", "district": "api"},
}
LEVEL_ORDER = ["country", "region", "province", "district"]
INDEX_SCHEMA = 2


class BuildError(RuntimeError):
    pass


# ------------------------------------------------------------------ context / lookup
def load_site(site_id: str) -> dict:
    return json.loads((ROOT / "sites" / f"{site_id}.json").read_text(encoding="utf-8"))


def save_site(site: dict) -> None:
    (ROOT / "sites" / f"{site['site']}.json").write_text(json.dumps(site, ensure_ascii=False, indent=2) + "\n",
                                                          encoding="utf-8")


def make_context(site: dict) -> dict:
    lk_path = ROOT / "data" / "lookup" / "areas.json"
    if not lk_path.exists():
        raise BuildError("data/lookup/areas.json missing — run: python3 scripts/kpi.py lookup")
    lk = json.loads(lk_path.read_text(encoding="utf-8"))
    home = site["home"]
    if home.get("level") != "region":
        raise BuildError("sites/<site>.json home.level must be 'region' (Phase 2)")
    drill = site.get("drill", {})
    provinces = [str(p) for p in drill.get("provinces", [])]
    for p in provinces:
        if p not in lk["provinces"]:
            raise BuildError(f"drill.provinces: {p} not in lookup")
        if str(lk["provinces"][p]["region"]) != str(home["code"]):
            raise BuildError(f"drill.provinces: {p} is not in health region {home['code']}")
    if drill.get("districts", "all") == "all":
        districts = sorted(d for d in lk["districts"] if d[:2] in provinces)
    else:
        districts = [str(d) for d in drill["districts"]]
    n_districts: dict = {}
    for d in lk["districts"]:
        n_districts[d[:2]] = n_districts.get(d[:2], 0) + 1
    return {"site": site, "lookup": lk, "home": home,
            "prov_region": {pc: v["region"] for pc, v in lk["provinces"].items()},
            "drill_regions": [str(home["code"])], "drill_provinces": provinces, "drill_districts": districts,
            "n_districts": n_districts}


def area_name(ctx, level: str, code: str) -> str:
    lk = ctx["lookup"]
    try:
        if level == "country":
            return "ประเทศ"
        if level == "region":
            return lk["regions"][code]
        if level == "province":
            return lk["provinces"][code]["name"]
        if level == "district":
            return lk["districts"][code]
        if level == "subdistrict":
            return lk["subdistricts"][code]
    except KeyError:
        raise BuildError(f"area code {code!r} ({level}) not in data/lookup/areas.json")
    raise BuildError(f"bad level {level}")


def child_level(level: str) -> str:
    return {"country": "region", "region": "province", "province": "district", "district": "subdistrict"}[level]


def child_codes(ctx, level: str, scope: str) -> list[str]:
    lk = ctx["lookup"]
    if level == "country":
        return sorted(lk["regions"], key=int)
    if level == "region":
        return sorted((p for p, v in lk["provinces"].items() if str(v["region"]) == scope), key=int)
    if level == "province":
        return sorted(d for d in lk["districts"] if d[:2] == scope)
    return sorted(s for s in lk["subdistricts"] if s[:4] == scope)


def scope_parent(ctx, level: str, scope: str):
    if level == "country":
        return None
    if level == "region":
        return {"level": "country", "code": "TH"}
    if level == "province":
        return {"level": "region", "code": str(ctx["prov_region"][scope])}
    return {"level": "province", "code": scope[:2]}


# ------------------------------------------------------------------ dataset construction
def _row_name(ctx, crow, r):
    if r.get("name"):
        return r["name"]
    return area_name(ctx, crow, r["code"])


def _mk_dataset(plugin, ctx, year, level, scope, rows, total_vals, asof, source, extra=None):
    crow = child_level(level)
    out_rows = []
    for r in sorted(rows, key=lambda r: (bool(r.get("pseudo")), r["code"])):
        row = {"code": r["code"], "name": _row_name(ctx, crow, r),
               "values": r["values"], "hasData": plugin.has_data(r["values"])}
        if r.get("pseudo"):
            row["pseudo"] = True
        out_rows.append(row)
    ds = {"indicator": plugin.ID, "year": year, "level": level, "scope": scope,
          "scopeName": area_name(ctx, level, scope), "parent": scope_parent(ctx, level, scope),
          "asOf": asof, "source": source, "rows": out_rows,
          "total": {"values": total_vals, "hasData": plugin.has_data(total_vals)}}
    if extra:
        ds.update(extra)
    return ds


def api_datasets(plugin, ctx, year, cache, warnings, views):
    out = {}
    for v in views:
        expected = child_codes(ctx, v["level"], v["scope"])
        rows = []
        for r in v["rows"]:
            if r["code"] in expected:
                rows.append(r)
            elif v["level"] == "province":
                rows.append(dict(r, pseudo=True, name=r.get("name") or f"ไม่ระบุพื้นที่ (รหัส {r['code']})"))
                warnings.append(f"{plugin.ID} {year} {v['level']}/{v['scope']}: district code {r['code']} not in "
                                f"lookup -> pseudo row (counted in the province total, not ranked)")
            elif v["level"] == "district":
                rows.append(dict(r, pseudo=True, name=f"ไม่ระบุตำบล (รหัส {r['code']})"))
                warnings.append(f"{plugin.ID} {year} {v['level']}/{v['scope']}: subdistrict code {r['code']} not in "
                                f"lookup -> pseudo row")
            else:
                raise BuildError(f"{plugin.ID} {year} {v['level']}/{v['scope']}: unexpected child code {r['code']}")
        if v.get("fill", True):
            have = {r["code"] for r in rows}
            for c in expected:
                if c not in have:
                    warnings.append(f"{plugin.ID} {year} {v['level']}/{v['scope']}: child {c} "
                                    f"({area_name(ctx, child_level(v['level']), c)}) absent from API -> zero row")
                    rows.append({"code": c, "values": _zero(plugin)})
        total = plugin.sum_values([r["values"] for r in rows])
        out[(plugin.ID, year, v["level"], v["scope"])] = _mk_dataset(
            plugin, ctx, year, v["level"], v["scope"], rows, total, fmt_asof(cache["asOf"]), "api", v.get("extra"))
    return out


def _zero(plugin):
    if plugin.ID == "dspm":
        return plugin.values_from_sums(dict.fromkeys(plugin.raw_fields(), 0))
    return plugin.derive({k: 0 for k in plugin.COUNT_KEYS} | {"prevalence": None})


# ------------------------------------------------------------------ Excel oracle (scope detected from the row names)
def _detect_scope(ctx, level: str, labels: list[str], path: str) -> str:
    """Which area is this workbook about? country -> TH; region -> the region of its provinces; province -> the
    province whose district-name set equals the labels; district -> the (unique) district whose subdistrict names
    contain every label (HDC lists only subdistricts with units). Ambiguity = hard error."""
    lk = ctx["lookup"]
    names = set(labels)
    if level == "country":
        return "TH"
    if level == "region":
        pm = {v["name"]: k for k, v in lk["provinces"].items()}
        miss = names - set(pm)
        if miss:
            raise BuildError(f"{path}: province names not in lookup: {sorted(miss)}")
        regs = {str(ctx["prov_region"][pm[n]]) for n in names}
        if len(regs) != 1:
            raise BuildError(f"{path}: provinces span several regions {sorted(regs)}")
        return regs.pop()
    if level == "province":
        cands = [p for p in lk["provinces"] if {lk["districts"][d] for d in child_codes(ctx, "province", p)} == names]
        if len(cands) != 1:
            raise BuildError(f"{path}: cannot identify the province from its district names (candidates {cands})")
        return cands[0]
    # district: prefer the drill districts, then any district in the country
    def match(dists):
        return [d for d in dists if names <= {lk["subdistricts"][s] for s in child_codes(ctx, "district", d)}]
    cands = match(ctx["drill_districts"]) or match(list(lk["districts"]))
    if len(cands) != 1:
        raise BuildError(f"{path}: cannot identify the district from its subdistrict names (candidates {cands})")
    return cands[0]


def _resolve_codes(ctx, level: str, scope: str, labels: list[str], path: str):
    lk = ctx["lookup"]
    if level == "country":
        m = {v: k for k, v in lk["regions"].items()}
    elif level == "region":
        m = {v["name"]: k for k, v in lk["provinces"].items() if str(v["region"]) == scope}
    elif level == "province":
        m = {n: c for c, n in lk["districts"].items() if c[:2] == scope}
    else:
        m = {n: c for c, n in lk["subdistricts"].items() if c[:4] == scope}
    codes = []
    for lab in labels:
        if lab not in m:
            raise BuildError(f"{path}: row name {lab!r} not found in lookup for level {level} scope {scope}")
        codes.append(m[lab])
    if len(set(codes)) != len(codes):
        raise BuildError(f"{path}: duplicate area names")
    return codes


def excel_datasets(plugin, ctx, workbooks, snapshots):
    out = {}
    for w in workbooks:
        level = w["level"]
        labels = [r["label"] for r in w["rows"]]
        scope = _detect_scope(ctx, level, labels, w["path"])
        codes = _resolve_codes(ctx, level, scope, labels, w["path"])
        rows = [{"code": c, "values": plugin.from_excel(r["values"])} for c, r in zip(codes, w["rows"])]
        total = plugin.from_excel(w["total"]["values"]) if w["total"] else \
            plugin.sum_values([r["values"] for r in rows])
        key = (plugin.ID, w["year"], level, scope)
        if key in out:
            raise BuildError(f"two Excel files for {key}: {w['path']} and {out[key]['excel_path']}")
        if plugin.ID == "dspm":
            xl_keys = {g: list(kv) for g, kv in w["rows"][0]["values"].items()}
        else:
            xl_keys = list(w["columns"])
        out[key] = _mk_dataset(plugin, ctx, w["year"], level, scope, rows, total,
                               (snapshots or {}).get(str(w["year"])), "excel",
                               {"excel_path": w["path"], "xl_keys": xl_keys,
                                "has_total_row": w["total"] is not None})
    return out


# ------------------------------------------------------------------ build
def build_datasets(site: dict, ctx: dict, indicators: list[str], years: list[int], log=print) -> dict:
    api, excel, warnings = {}, {}, []
    excel_dir = ROOT / site["excel"]["dir"]
    snapshots = site["excel"].get("snapshots") or {}     # year -> date the HDC Excel files were exported
    registry = build_lookup.load_units()
    for ind in indicators:
        plugin = PLUGINS[ind]
        wbs = [w for w in xlsx_hdc.discover(excel_dir, ind) if w["year"] in years]
        excel.update(excel_datasets(plugin, ctx, wbs, snapshots))
        for y in years:
            if ind == "dspm":
                summ = dspm.load_summary(y)
                if summ is None:
                    warnings.append(f"dspm {y}: no province summary {dspm.summary_path(y).relative_to(ROOT)} "
                                    f"(run kpi.py update --national) - country/region levels missing")
                else:
                    api.update(api_datasets(dspm, ctx, y, summ, warnings, dspm.national_views(summ, ctx)))
                for prov in ctx["drill_provinces"]:
                    cache = dspm.load_cache(y, prov)
                    if cache is None:
                        warnings.append(f"dspm {y}: no cache for province {prov} (run fetch)")
                        continue
                    api.update(api_datasets(dspm, ctx, y, cache, warnings, dspm.api_views(cache, ctx, registry)))
            else:
                cache = coverage.load_cache(y)
                if cache is None:
                    warnings.append(f"coverage {y}: no cache (run fetch)")
                    continue
                api.update(api_datasets(coverage, ctx, y, cache, warnings, coverage.api_views(cache, ctx)))
    published = {}
    for key, ds in list(api.items()) + list(excel.items()):
        ind, y, level, scope = key
        want = SOURCE_LEVELS[ind][level]
        src = api if want == "api" else excel
        if key in src and key not in published:
            published[key] = src[key]
    # district datasets that have an Excel oracle -> verified (the pipeline fails hard if they ever differ)
    verified: dict = {}
    for (ind, y, level, scope) in excel:
        if level == "district" and (ind, y, level, scope) in published:
            verified.setdefault(ind, {}).setdefault(str(y), []).append(scope)
            published[(ind, y, level, scope)]["verified"] = True
    for k in verified:
        for y in verified[k]:
            verified[k][y].sort()
    return {"api": api, "excel": excel, "published": published, "warnings": warnings, "verified": verified,
            "registry": registry}


# ------------------------------------------------------------------ JSON writing
def _jsonify(plugin, values, has):
    if not has:
        values = plugin.null_values(values)
    key = "groups" if plugin.ID == "dspm" else "metrics"
    return {key: values}


def dataset_json(site_id: str, plugin, ds: dict) -> dict:
    rows = []
    for r in ds["rows"]:
        row = {"code": r["code"], "name": r["name"], "hasData": r["hasData"]}
        if r.get("pseudo"):
            row["pseudo"] = True
        row.update(_jsonify(plugin, r["values"], r["hasData"]))
        rows.append(row)
    out = {"schema": INDEX_SCHEMA, "site": site_id, "indicator": ds["indicator"], "year": ds["year"],
           "level": ds["level"],
           "scope": {"code": ds["scope"], "name": ds["scopeName"], "parent": ds["parent"]},
           "asOf": ds["asOf"], "source": ds["source"]}
    if ds["level"] == "district":
        out["inferredUnits"] = ds.get("inferredUnits", 0)
        out["units"] = ds.get("units", 0)
        out["verified"] = bool(ds.get("verified", False))
        out["crossDistrict"] = [{"hospcode": c["hospcode"], "name": c["name"], "tambon": c["tambon"],
                                 "locatedIn": c["locatedIn"]} for c in ds.get("crossDistrict", [])]
    out["rows"] = rows
    out["total"] = {"code": ds["scope"], "name": "รวม", "hasData": ds["total"]["hasData"],
                    **_jsonify(plugin, ds["total"]["values"], ds["total"]["hasData"])}
    return out


def dataset_file(ds_key) -> str:
    ind, y, level, scope = ds_key
    return f"{ind}_{y}_{level}_{scope}.json"


def build_tree(ctx, published) -> dict:
    """region -> provinces -> districts (inferredUnits) -> subdistricts that have a row in any published district
    dataset (spec §4.2)."""
    home = ctx["home"]
    sub_rows: dict = {}
    inferred: dict = {}
    for (ind, y, level, scope), ds in published.items():
        if level == "district":
            sub_rows.setdefault(scope, set()).update(r["code"] for r in ds["rows"] if not r.get("pseudo"))
            inferred[scope] = max(inferred.get(scope, 0), ds.get("inferredUnits", 0))
    tree = {"code": str(home["code"]), "level": "region", "name": area_name(ctx, "region", str(home["code"])),
            "children": []}
    for p in ctx["drill_provinces"]:
        pn = {"code": p, "level": "province", "name": area_name(ctx, "province", p), "children": []}
        for d in child_codes(ctx, "province", p):
            if d not in ctx["drill_districts"]:
                continue
            dn = {"code": d, "level": "district", "name": area_name(ctx, "district", d),
                  "inferredUnits": inferred.get(d, 0)}
            subs = sorted(sub_rows.get(d, ()))
            if subs:
                dn["children"] = [{"code": s, "level": "subdistrict", "name": area_name(ctx, "subdistrict", s)}
                                  for s in subs]
            pn["children"].append(dn)
        tree["children"].append(pn)
    return tree


def write_site(site: dict, ctx: dict, built: dict, log=print) -> dict:
    site_id = site["site"]
    out_dir = ROOT / "site" / "data" / site_id
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.json"):
        f.unlink()
    index_ds = []
    written = []
    for key in sorted(built["published"], key=lambda k: (k[0], k[1], LEVEL_ORDER.index(k[2]), k[3])):
        ds = built["published"][key]
        plugin = PLUGINS[key[0]]
        fname = dataset_file(key)
        (out_dir / fname).write_text(json.dumps(dataset_json(site_id, plugin, ds), ensure_ascii=False,
                                                separators=(",", ":")), encoding="utf-8")
        index_ds.append({"indicator": key[0], "year": key[1], "level": key[2], "scope": key[3],
                         "kind": "level", "file": fname, "asOf": ds["asOf"], "source": ds["source"]})
        written.append((fname, len(ds["rows"]), ds["asOf"], ds["source"]))
    inds = [i for i in site["indicators"] if i in PLUGINS]
    years = sorted({k[1] for k in built["published"]})
    index = {"schema": INDEX_SCHEMA, "site": site_id, "name": site["name"], "org": site["org"],
             "logo": site["logo"], "orgLogo": site.get("orgLogo"), "repo": site.get("repo"),
             "home": {"level": site["home"]["level"], "code": str(site["home"]["code"]),
                      "name": area_name(ctx, site["home"]["level"], str(site["home"]["code"]))},
             "years": years, "currentYear": site["currentYear"],
             "colorRules": site["colorRules"],
             "sourceLabels": {"api": "MOPH Open Data API", "excel": site["excel"]["sourceLabel"]},
             "indicators": {i: PLUGINS[i].META for i in inds},
             "targets": site["targets"], "tree": build_tree(ctx, built["published"]),
             "verified": built.get("verified", {}),
             "datasets": index_ds}
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    written.append(("index.json", len(index_ds), "", ""))
    return {"files": written}
