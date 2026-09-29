"""Build the web data layer  site/data/<site>/  from the aggregate cache (API) + HDC Excel (oracle / Excel-sourced levels).

`build_datasets()` is shared with verify.py: it returns every dataset that the API cache can produce (`api`), every
dataset read from Excel (`excel`), and the `published` selection per the source matrix (spec §3.4).
"""
from __future__ import annotations

import json
from pathlib import Path

from .indicators import coverage, dspm
from .indicators.common import fmt_asof
from .loaders import xlsx_hdc

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = {"dspm": dspm, "coverage": coverage}
# source matrix (spec §3.4): which source publishes which level
SOURCE_LEVELS = {
    "dspm": {"country": "excel", "region": "excel", "province": "api", "district": "api"},
    "coverage": {"country": "api", "region": "api", "province": "api", "district": "api"},
}
LEVEL_ORDER = ["country", "region", "province", "district"]


class BuildError(RuntimeError):
    pass


# ------------------------------------------------------------------ context / lookup
def load_site(site_id: str) -> dict:
    return json.loads((ROOT / "sites" / f"{site_id}.json").read_text(encoding="utf-8"))


def make_context(site: dict) -> dict:
    lk_path = ROOT / "data" / "lookup" / "areas.json"
    if not lk_path.exists():
        raise BuildError("data/lookup/areas.json missing — run: python3 scripts/kpi.py lookup")
    lk = json.loads(lk_path.read_text(encoding="utf-8"))
    home = {p["level"]: p["code"] for p in site["home"]["path"]}
    n_districts: dict = {}
    for d in lk["districts"]:
        n_districts[d[:2]] = n_districts.get(d[:2], 0) + 1
    return {"site": site, "lookup": lk, "home": home,
            "prov_region": {pc: v["region"] for pc, v in lk["provinces"].items()},
            "drill_regions": [str(home["region"])], "drill_provinces": [home["province"]], "drill_districts": [home["district"]],
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
def _mk_dataset(plugin, ctx, year, level, scope, rows, total_vals, asof, source, extra=None):
    crow = child_level(level)
    out_rows = []
    for r in sorted(rows, key=lambda r: int(r["code"])):
        out_rows.append({"code": r["code"], "name": area_name(ctx, crow, r["code"]),
                         "values": r["values"], "hasData": plugin.has_data(r["values"])})
    ds = {"indicator": plugin.ID, "year": year, "level": level, "scope": scope,
          "scopeName": area_name(ctx, level, scope), "parent": scope_parent(ctx, level, scope),
          "asOf": asof, "source": source, "rows": out_rows,
          "total": {"values": total_vals, "hasData": plugin.has_data(total_vals)}}
    if extra:
        ds.update(extra)
    return ds


def api_datasets(plugin, ctx, year, cache, warnings):
    out = {}
    views = plugin.api_views(cache, ctx)
    for v in views:
        have = {r["code"] for r in v["rows"]}
        rows = list(v["rows"])
        for c in child_codes(ctx, v["level"], v["scope"]):
            if c not in have:
                warnings.append(f"{plugin.ID} {year} {v['level']}/{v['scope']}: child {c} "
                                f"({area_name(ctx, child_level(v['level']), c)}) absent from API -> zero row")
                rows.append({"code": c, "values": _zero(plugin)})
        extra_codes = have - set(child_codes(ctx, v["level"], v["scope"]))
        if extra_codes:
            raise BuildError(f"{plugin.ID} {year} {v['level']}/{v['scope']}: unexpected child codes {sorted(extra_codes)}")
        total = plugin.sum_values([r["values"] for r in rows])
        out[(plugin.ID, year, v["level"], v["scope"])] = _mk_dataset(
            plugin, ctx, year, v["level"], v["scope"], rows, total, fmt_asof(cache["asOf"]), "api")
    return out


def _zero(plugin):
    if plugin.ID == "dspm":
        return plugin.values_from_sums(dict.fromkeys(plugin.raw_fields(), 0))
    return plugin.derive({k: 0 for k in plugin.COUNT_KEYS} | {"prevalence": None})


def _resolve_codes(ctx, level: str, labels: list[str], path: str):
    lk = ctx["lookup"]
    if level == "country":
        m = {v: k for k, v in lk["regions"].items()}
    elif level == "region":
        m = {v["name"]: k for k, v in lk["provinces"].items()}
    elif level == "province":
        m = {n: c for c, n in lk["districts"].items() if c[:2] == ctx["home"]["province"]}
    else:
        m = {n: c for c, n in lk["subdistricts"].items() if c[:4] == ctx["home"]["district"]}
    codes = []
    for lab in labels:
        if lab not in m:
            raise BuildError(f"{path}: row name {lab!r} not found in lookup for level {level}")
        codes.append(m[lab])
    if len(set(codes)) != len(codes):
        raise BuildError(f"{path}: duplicate area names")
    return codes


def excel_datasets(plugin, ctx, workbooks, excel_export_date):
    out = {}
    for w in workbooks:
        level = w["level"]
        codes = _resolve_codes(ctx, level, [r["label"] for r in w["rows"]], w["path"])
        if level == "country":
            scope = "TH"
        elif level == "region":
            regs = {str(ctx["prov_region"][c]) for c in codes}
            if len(regs) != 1:
                raise BuildError(f"{w['path']}: provinces span several regions {regs}")
            scope = regs.pop()
        elif level == "province":
            scope = ctx["home"]["province"]
        else:
            scope = ctx["home"]["district"]
        rows = [{"code": c, "values": plugin.from_excel(r["values"])} for c, r in zip(codes, w["rows"])]
        total = plugin.from_excel(w["total"]["values"]) if w["total"] else \
            plugin.sum_values([r["values"] for r in rows])
        key = (plugin.ID, w["year"], level, scope)
        if key in out:
            raise BuildError(f"two Excel files for {key}: {w['path']}")
        if plugin.ID == "dspm":
            xl_keys = {g: list(kv) for g, kv in w["rows"][0]["values"].items()}
        else:
            xl_keys = list(w["columns"])
        out[key] = _mk_dataset(plugin, ctx, w["year"], level, scope, rows, total, excel_export_date, "excel",
                               {"excel_path": w["path"], "xl_keys": xl_keys,
                                "has_total_row": w["total"] is not None})
    return out


def build_datasets(site: dict, ctx: dict, indicators: list[str], years: list[int], log=print) -> dict:
    api, excel, monthly, warnings = {}, {}, {}, []
    excel_dir = ROOT / site["excel"]["dir"]
    export_date = site["excel"]["exportDate"]
    for ind in indicators:
        plugin = PLUGINS[ind]
        wbs = [w for w in xlsx_hdc.discover(excel_dir, ind) if w["year"] in years]
        excel.update(excel_datasets(plugin, ctx, wbs, export_date))
        for y in years:
            for lvl, src in SOURCE_LEVELS[ind].items():
                if src == "excel" and not any(k[0] == ind and k[1] == y and k[2] == lvl for k in excel):
                    warnings.append(f"{ind} {y}: no Excel export for {lvl} level (source matrix says Excel) - "
                                    f"export HDC xlsx into {site['excel']['dir']}/{ind}/{y}/")
        for y in years:
            if ind == "dspm":
                for prov in ctx["drill_provinces"]:
                    cache = dspm.load_cache(y, prov)
                    if cache is None:
                        warnings.append(f"dspm {y}: no cache for province {prov} (run fetch)")
                        continue
                    api.update(api_datasets(dspm, ctx, y, cache, warnings))
                    for lvl, scope, clen in (("province", prov, 4), ("district", ctx["home"]["district"], 6)):
                        m = dspm.monthly_view(cache, lvl, scope, clen)
                        crow = child_level(lvl)
                        for r in m["rows"]:
                            r["name"] = area_name(ctx, crow, r["code"])
                        monthly[(ind, y, lvl, scope)] = {
                            "indicator": ind, "year": y, "level": lvl, "scope": scope,
                            "scopeName": area_name(ctx, lvl, scope), "parent": scope_parent(ctx, lvl, scope),
                            "asOf": fmt_asof(cache["asOf"]), "source": "api", **m}
            else:
                cache = coverage.load_cache(y)
                if cache is None:
                    warnings.append(f"coverage {y}: no cache (run fetch)")
                    continue
                api.update(api_datasets(coverage, ctx, y, cache, warnings))
    published = {}
    for key, ds in list(api.items()) + list(excel.items()):
        ind, y, level, scope = key
        want = SOURCE_LEVELS[ind][level]
        src = api if want == "api" else excel
        if key in src and key not in published:
            published[key] = src[key]
    return {"api": api, "excel": excel, "published": published, "monthly": monthly, "warnings": warnings}


# ------------------------------------------------------------------ JSON writing
def _round_pcts(plugin, vals):
    return vals  # pct fields are already rounded to 2 decimals when derived; Excel pcts are 2-decimal cells


def _jsonify(plugin, values, has):
    if not has:
        values = plugin.null_values(values)
    key = "groups" if plugin.ID == "dspm" else "metrics"
    return {key: values}


def dataset_json(site_id: str, plugin, ds: dict) -> dict:
    return {"schema": 1, "site": site_id, "indicator": ds["indicator"], "year": ds["year"],
            "level": ds["level"],
            "scope": {"code": ds["scope"], "name": ds["scopeName"], "parent": ds["parent"]},
            "asOf": ds["asOf"], "source": ds["source"],
            "rows": [{"code": r["code"], "name": r["name"], "hasData": r["hasData"],
                      **_jsonify(plugin, r["values"], r["hasData"])} for r in ds["rows"]],
            "total": {"code": ds["scope"], "name": "รวม", "hasData": ds["total"]["hasData"],
                      **_jsonify(plugin, ds["total"]["values"], ds["total"]["hasData"])}}


def dataset_file(ds_key) -> str:
    ind, y, level, scope = ds_key
    return f"{ind}_{y}_{level}_{scope}.json"


def monthly_file(key) -> str:
    ind, y, level, scope = key
    return f"{ind}_{y}_monthly_{scope}.json"


def build_tree(ctx, published) -> dict:
    scopes = {(lvl, sc) for (_, _, lvl, sc) in published}
    def node(level, code):
        return {"code": code, "level": level, "name": area_name(ctx, level, code)}
    def build(level, code):
        n = node(level, code)
        kids = []
        cl = child_level(level)
        for c in child_codes(ctx, level, code):
            if (cl, c) in scopes:
                kids.append(build(cl, c))
        if kids:
            n["children"] = kids
        return n
    return build("country", "TH")


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
    for key in sorted(built["monthly"], key=lambda k: (k[1], LEVEL_ORDER.index(k[2]))):
        m = built["monthly"][key]
        fname = monthly_file(key)
        body = {"schema": 1, "site": site_id, "indicator": m["indicator"], "year": m["year"], "level": m["level"],
                "scope": {"code": m["scope"], "name": m["scopeName"], "parent": m["parent"]},
                "asOf": m["asOf"], "source": m["source"], "fiscalYearStartMonth": 10,
                "months": m["months"], "rows": m["rows"]}
        (out_dir / fname).write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index_ds.append({"indicator": key[0], "year": key[1], "level": key[2], "scope": key[3],
                         "kind": "monthly", "file": fname, "asOf": m["asOf"], "source": m["source"]})
        written.append((fname, len(m["rows"]), m["asOf"], m["source"]))
    inds = [i for i in site["indicators"] if i in PLUGINS]
    years = sorted({k[1] for k in built["published"]})
    index = {"schema": 1, "site": site_id, "name": site["name"], "org": site["org"], "logo": site["logo"],
             "years": years, "currentYear": site["currentYear"], "home": site["home"],
             "colorRules": site["colorRules"],
             "sourceLabels": {"api": "MOPH Open Data API", "excel": site["excel"]["sourceLabel"]},
             "indicators": {i: PLUGINS[i].META for i in inds},
             "targets": site["targets"], "tree": build_tree(ctx, built["published"]),
             "datasets": index_ds}
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    written.append(("index.json", len(index_ds), "", ""))
    return {"files": written}
