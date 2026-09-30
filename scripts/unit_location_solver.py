"""Exact whole-unit location solver — HDC ตำบล Excel 2569 (export 2569-09-30) vs API per-unit vectors.

Read-only on the repo, no network: committed cache data/cache/dspm/2569/<prov>.json + data/lookup/units.json.
Run: python3 scripts/unit_location_solver.py [xlsx-dir ...]  (default: data/excel_reference/dspm/2569/2569-09-30 + "unit miss/")
  -> prints everything; writes overrides_proposal.json + solver_result.json to data/raw_api/unit_solver/ (gitignored).
Local tool only (needs numpy, not in requirements.txt; the Actions bot never runs it).

Hypothesis ก: HDC puts every reporting unit (hospcode) WHOLE into one tambon of its own location table, so each
Excel row (tambon) = sum of the vectors of a SUBSET of the province's units.  Vector = 15 count keys (gender
excluded) x 6 age groups = 90 ints, compared exactly.

Method (global, exhaustive — no "moves" assumption, swaps included automatically):
 1. For EVERY Excel row of the 22 districts enumerate ALL subsets of the province's non-zero units whose vector sum
    == the row (DFS, branch on the most-constrained dimension, prune by v<=rem and sum(available)>=rem).  A node
    budget defers the rare expensive row.
 2. A unit has ONE location, so units that are uniquely fixed by another row are removed from the pool of a deferred
    row, which is then enumerated exhaustively over that reduced pool.
 3. Rows must be pairwise disjoint.  Unit whose HDC row differs from our pipeline tambon -> override; unit that our
    pipeline puts in an Excel district but that sits in no Excel row -> ELSEWHERE (HDC counts it elsewhere/drops it).
"""
import json, sys, glob, os, itertools, time
import numpy as np
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(REPO, "data", "raw_api", "unit_solver")
os.makedirs(S, exist_ok=True)
os.chdir(REPO); sys.path.insert(0, REPO)
XLSX_DIRS = sys.argv[1:] or [d for d in ("data/excel_reference/dspm/2569/2569-09-30", "unit miss") if os.path.isdir(d)]
from scripts.indicators import dspm
from scripts import build_lookup, build_site as B
from scripts.loaders import xlsx_hdc

site = B.load_site("angthong"); ctx = B.make_context(site); lk = ctx["lookup"]
reg = dict(build_lookup.load_units())
reg.pop("overrides", None)   # baseline = GIS registry + fallback rule, even after overrides land in units.json
COUNT = [k for k in dspm.COUNT_KEYS if k not in ("normal_female", "normal_male")]
DIMS = [(g, k) for g in dspm.GROUPS for k in COUNT]
TI, SI = 0, DIMS.index(("total", "screened"))
Z = np.zeros(len(DIMS), dtype=np.int64)
def vec(values): return np.array([(values[g][k] or 0) for g, k in DIMS], dtype=np.int64)
TARGET_DISTRICTS = ["2604", "1202", "1302", "1606", "1909", "1306", "1204", "1206", "1201"]
SOURCE = "HDC Excel ตำบล 2569 export 2569-09-30"
BUDGET1, BUDGET2 = 200_000, 50_000_000

# ---------------------------------------------------------------- load
UV, TAM, AREAS, PROV_OF = {}, {}, {}, {}
XL = {}
import shutil
XL_IN = os.path.join(S, "xl", "2569")            # read_workbook takes the year from the folder name
shutil.rmtree(os.path.join(S, "xl"), ignore_errors=True); os.makedirs(XL_IN)
for d in XLSX_DIRS:
    for f in glob.glob(f"{d}/*.xlsx"):
        if not os.path.basename(f).startswith("~$"):
            shutil.copy(f, XL_IN)
for f in sorted(glob.glob(f"{XL_IN}/*.xlsx")):
    w = xlsx_hdc.read_workbook(f, "dspm"); labels = [r["label"] for r in w["rows"]]
    d = B._detect_scope(ctx, "district", labels, f)
    codes = B._resolve_codes(ctx, "district", d, labels, f)
    XL[d] = {"file": f.rsplit("/", 1)[1], "rows": {c: vec(dspm.from_excel(r["values"])) for c, r in zip(codes, w["rows"])}}
for p in sorted({d[:2] for d in XL}):
    c = dspm.load_cache(2569, p); tam = dspm.resolve_tambons(c, reg); AREAS.update(dspm.unit_areas(c))
    for h, s in dspm._sums(c, lambda a6, h, m: h).items():
        UV[h] = vec(dspm._values(c, s)); TAM[h] = tam[h]; PROV_OF[h] = p
BASE = {h: TAM[h]["tambon"] for h in TAM}
ROWS = {c: v for d in XL for c, v in XL[d]["rows"].items()}          # every Excel row (tambon code -> vector)

def kind(h): return "registry" if h in reg["units"] else "fallback"
def tname(c): return lk["subdistricts"].get(c, f"(no such tambon {c})") if c else "ELSEWHERE"
def dname(d): return lk["districts"].get(d, f"(pseudo district {d})")
def uinfo(h):
    u = reg["units"].get(h)
    return f"{h} [registry hostype={u.get('hostype')} {u.get('name','').strip()}]" if u else f"{h} [fallback]"

# ---------------------------------------------------------------- exact subset enumeration
class Budget(Exception): pass
def exact_all(cands, need, budget):
    cands = sorted(h for h in cands if UV[h].any() and np.all(UV[h] <= need))
    if not need.any(): return [()]
    if not cands: return []
    M = np.array([UV[h] for h in cands]); NZ = M > 0
    out, nodes = [], [0]
    def rec(avail, rem, chosen):
        nodes[0] += 1
        if nodes[0] > budget: raise Budget
        if not rem.any(): out.append(tuple(sorted(cands[i] for i in chosen))); return
        fit = avail & np.all(M <= rem, axis=1)
        if not fit.any() or np.any(M[fit].sum(axis=0) < rem): return
        cnt = NZ[fit].sum(axis=0); dims = np.where(rem > 0)[0]
        j = dims[np.argmin(cnt[dims])]                       # most-constrained dimension
        i = np.where(fit & NZ[:, j])[0][0]                   # some unit must cover it: take i or drop i
        a2 = fit.copy(); a2[i] = False
        chosen.append(i); rec(a2, rem - M[i], chosen); chosen.pop()
        rec(a2, rem, chosen)
    rec(np.ones(len(cands), bool), need.copy(), [])
    return out

def main():
    print(f"dims={len(DIMS)} (15 count keys x 6 groups, gender excluded); Excel districts={len(XL)} rows={len(ROWS)}")
    print("\n=== baseline (pipeline rule: GIS registry, else max-target areacode) — mismatched rows per district")
    for d in sorted(XL):
        api = {}
        for h, t in BASE.items():
            if t[:4] == d: api[t] = api.get(t, Z) + UV[h]
        nb = sum(1 for c in set(XL[d]["rows"]) | set(api) if not np.array_equal(XL[d]["rows"].get(c, Z), api.get(c, Z)))
        print(f"  {d} {dname(d):14s} rows={len(XL[d]['rows']):2d} mismatched={nb} excel_target="
              f"{sum(int(v[TI]) for v in XL[d]['rows'].values())} api_target={sum(int(v[TI]) for v in api.values())}")

    # step 1
    sols, deferred, t0 = {}, [], time.time()
    for c, x in ROWS.items():
        pool = [h for h in UV if PROV_OF[h] == c[:2]]
        try: sols[c] = exact_all(pool, x, BUDGET1)
        except Budget: deferred.append(c)
    # step 2 (iterate: fixed units of other rows leave the pool)
    for c in deferred:
        fixed = {h for r, s in sols.items() if len(s) == 1 and r != c for h in s[0]}
        pool = [h for h in UV if PROV_OF[h] == c[:2] and h not in fixed]
        sols[c] = exact_all(pool, ROWS[c], BUDGET2)
        print(f"  deferred row {c} {tname(c)}: pool reduced to {len(pool)} units (units fixed by other rows removed)"
              f" -> {len(sols[c])} solution(s)")
    print(f"  enumeration done in {time.time()-t0:.1f}s; rows with 0 solutions: {[c for c,s in sols.items() if not s]};"
          f" rows with >1 solution: {[c for c,s in sols.items() if len(s) > 1]}")
    # step 3
    loc, clash = {}, []
    for c, s in sols.items():
        if len(s) != 1: continue
        for h in s[0]:
            if h in loc: clash.append((h, loc[h], c))
            loc[h] = c
    print(f"  disjointness clashes: {clash or 'none'}")
    zero = sorted(h for h in UV if not UV[h].any())
    overrides = {h: c for h, c in loc.items() if BASE[h] != c}
    elsewhere = sorted(h for h in UV if UV[h].any() and h not in loc and BASE[h][:4] in XL)

    # per-district report
    result = {}
    for d in TARGET_DISTRICTS:
        ins = sorted(h for h, c in overrides.items() if c[:4] == d)
        outs = sorted(h for h in elsewhere if BASE[h][:4] == d)
        leave = sorted(h for h, c in overrides.items() if BASE[h][:4] == d and c[:4] != d)
        amb = [c for c in XL[d]["rows"] if len(sols[c]) != 1]
        status = "unsolvable" if any(not sols[c] for c in XL[d]["rows"]) else ("ambiguous" if amb else "solved-unique")
        print(f"\n=== {d} {dname(d)} ({XL[d]['file']}) -> {status}")
        for h in ins:
            print(f"   MOVE {uinfo(h)} {BASE[h]} {tname(BASE[h])} -> {overrides[h]} {tname(overrides[h])}"
                  f"  target={int(UV[h][TI])} screened={int(UV[h][SI])} areas={AREAS[h]['areas']}")
        for h in leave:
            print(f"   LEAVES to other district: {uinfo(h)} {BASE[h]} -> {overrides[h]} ({dname(overrides[h][:4])})")
        for h in outs:
            print(f"   ELSEWHERE {uinfo(h)} cur {BASE[h]} {tname(BASE[h])} target={int(UV[h][TI])} "
                  f"screened={int(UV[h][SI])} areas={AREAS[h]['areas']}")
        for c in sorted(XL[d]["rows"]):
            before = sum((UV[h] for h in UV if BASE[h] == c), Z)
            if not np.array_equal(before, ROWS[c]):
                print(f"     row {c} {tname(c):14s} excel target/screened {int(ROWS[c][TI])}/{int(ROWS[c][SI])}  "
                      f"api before {int(before[TI])}/{int(before[SI])}  HDC set = {list(sols[c][0]) if len(sols[c])==1 else sols[c]}")
        gone = sorted({BASE[h] for h in ins + outs + leave} - set(XL[d]["rows"]))
        for c in gone:
            if c[:4] == d: print(f"     row {c} {tname(c)} not in Excel (API had units there; all of them move)")
        result[d] = {"status": status, "moves": {h: [BASE[h], overrides[h]] for h in ins + leave},
                     "elsewhere": outs, "ambiguous_rows": amb}

    # proposal
    proposal = {h: {"tambon": c, "source": SOURCE,
                     "note": f"{dname(c[:4])}, was {BASE[h]} ({kind(h)})"
                             + (f" in {dname(BASE[h][:4])}" if BASE[h][:4] != c[:4] else "")}
                for h, c in sorted(overrides.items())}
    # verification with overrides applied
    print("\n=== after applying overrides_proposal.json — all 22 Excel districts")
    A = dict(BASE); A.update({h: p["tambon"] for h, p in proposal.items()})
    after = {}
    for d in sorted(XL):
        api = {}
        for h, t in A.items():
            if t[:4] == d: api[t] = api.get(t, Z) + UV[h]
        bad = {c: XL[d]["rows"].get(c, Z) - api.get(c, Z) for c in sorted(set(XL[d]["rows"]) | set(api))}
        bad = {c: r for c, r in bad.items() if r.any()}
        after[d] = {c: {f"{g}.{k}": int(r[i]) for i, (g, k) in enumerate(DIMS) if r[i]} for c, r in bad.items()}
        print(f"  {d} {dname(d):14s} rows={len(XL[d]['rows']):2d} mismatched={len(bad)}")
        for c, r in bad.items():
            culprits = [h for h in elsewhere if A[h] == c]
            ok = np.array_equal(-r, sum((UV[h] for h in culprits), Z))
            print(f"     {c} {tname(c)} excel {int(XL[d]['rows'].get(c, Z)[TI])}/{int(XL[d]['rows'].get(c, Z)[SI])} "
                  f"vs api {int(api.get(c, Z)[TI])}/{int(api.get(c, Z)[SI])} (target/screened); "
                  f"diff == -(ELSEWHERE {culprits}): {ok}; cells: {after[d][c]}")
    print(f"\n=== zero-vector units (location undeterminable, irrelevant to the numbers): {len(zero)}")
    print("\n=== ELSEWHERE units")
    for h in elsewhere:
        print(f"  {uinfo(h)} pipeline {BASE[h]} {tname(BASE[h])} target={int(UV[h][TI])} screened={int(UV[h][SI])} "
              f"areas={AREAS[h]['areas']} missing-entry={h in reg['missing']}")
    # region Excel hint
    w = xlsx_hdc.read_workbook(f"{REPO}/data/excel_reference/dspm/2569/เขต 4.xlsx", "dspm")
    pm = {v["name"]: k for k, v in lk["provinces"].items()}
    print("\n=== region Excel 'เขต 4.xlsx' (snapshot 2569-09-29, one day older) province target vs API (hint only)")
    for r in w["rows"]:
        p = pm[r["label"]]
        if p in {PROV_OF[h] for h in UV}:
            at = sum(int(UV[h][TI]) for h in UV if PROV_OF[h] == p)
            print(f"  {p} {r['label']}: excel {r['values']['total']['target']} api {at} diff {r['values']['total']['target'] - at}")
    # units of our non-Excel districts etc.: summary of override kinds
    print(f"\noverrides: {len(proposal)} ({sum(1 for h in proposal if kind(h)=='registry')} registry, "
          f"{sum(1 for h in proposal if kind(h)=='fallback')} fallback); ELSEWHERE: {len(elsewhere)}")
    json.dump(proposal, open(f"{S}/overrides_proposal.json", "w"), ensure_ascii=False, indent=2)
    json.dump({"per_district": result, "elsewhere": {h: {"pipelineTambon": BASE[h], "target": int(UV[h][TI]),
               "areas": AREAS[h]["areas"], "kind": kind(h)} for h in elsewhere},
               "row_solution_counts": {c: len(s) for c, s in sols.items()}, "after_overrides_mismatch": after},
              open(f"{S}/solver_result.json", "w"), ensure_ascii=False, indent=1)
    print(f"wrote {S}/overrides_proposal.json and {S}/solver_result.json")

if __name__ == "__main__":
    main()
