"""Reader for HDC Excel exports (oracle files in data/excel_reference/<site>/{dspm,coverage}/<year>/).

Output structure mirrors what the API aggregate produces:
  DSPM     value = {group: {key: number|None}}   (groups total,m9,m18,m30,m42,m60; keys as in indicators/dspm.py)
  Coverage value = {key: number|None}

The level of a workbook is detected from the header of column A (never from the file name):
  เขตสุขภาพ -> scope country (rows = 13 health regions)
  จังหวัด    -> scope region  (rows = provinces)
  อำเภอ      -> scope province (rows = districts)
  ตำบล       -> scope district (rows = subdistricts)
Rows are matched to area codes by NAME later (see build_site / verify); this module only reads.
"""
from __future__ import annotations

import re
from pathlib import Path

import openpyxl

LEVEL_BY_HEADER = {"เขตสุขภาพ": "country", "จังหวัด": "region", "อำเภอ": "province", "ตำบล": "district"}
GROUPS = ["total", "m9", "m18", "m30", "m42", "m60"]

# DSPM column order inside one age group (spec §3.2). Extra keys: total-only / 2569-only.
_DSPM_ORDER = ["target", "screened", "pct_screened", "normal_first", "pct_normal_first",
               "suspect_wait30", "suspect_refer", "suspect_total", "pct_suspect",
               "followed", "pct_followed", "normal_after", "delay_after_total",
               "delay_1B202", "delay_1B212", "delay_1B222", "delay_1B232", "delay_1B242",
               "pending_followup", "lost_followup", "normal_female", "normal_male",
               "normal_total", "pct_normal"]

# header text (whitespace stripped) that must appear in rows 2-4 above each key (layout validation)
_DSPM_HEADER = {
    "target": "เป้าหมาย", "screened": "คัดกรอง(2)", "pct_screened": "ร้อยละคัดกรอง",
    "normal_first": "สมวัยครั้งแรก(2.1)", "pct_normal_first": "ร้อยละสมวัยครั้งแรก",
    "suspect_wait30": "(2.2)", "suspect_refer": "(2.3)", "suspect_total": "(2.4)",
    "pct_suspect": "ร้อยละสงสัยล่าช้า", "followed": "ติดตามได้(3)", "pct_followed": "ร้อยละติดตามได้",
    "normal_after": "สมวัย(3.1)", "delay_after_total": "รวม(3.2)",
    "delay_1B202": "1B202", "delay_1B212": "1B212", "delay_1B222": "1B222",
    "delay_1B232": "1B232", "delay_1B242": "1B242",
    "pending_followup": "รอการติดตาม(4)", "lost_followup": "ติดตามไม่ได้ใน30วัน(5)",
    "normal_female": "สมวัยเพศหญิง", "normal_male": "สมวัยเพศชาย",
    "normal_total": "รวมสมวัย", "pct_normal": "ร้อยละสมวัย",
}

COVERAGE_KEYS = {1: "population", 2: "prevalence", 3: "expected", 4: "served_teda4i", 5: "served_icd9",
                 6: "diagnosed_icd10", 7: "reached_cum", 8: "pct_reached_cum", 9: "reached_fy",
                 10: "pct_reached_fy", 11: "out_of_province"}


class XlsxLayoutError(RuntimeError):
    pass


def _norm(v) -> str:
    return re.sub(r"\s+", "", str(v)) if v is not None else ""


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise XlsxLayoutError(f"non-numeric cell {v!r}")


def dspm_keys(group: str, has_gender: bool) -> list[str]:
    keys = []
    for k in _DSPM_ORDER:
        if k == "pct_normal_first" and group != "total":
            continue
        if k in ("normal_female", "normal_male") and not has_gender:
            continue
        keys.append(k)
    return keys


def _dspm_layout(ws, path):
    """Detect group start columns (0-based) from row 2 'เป้าหมาย' cells; return {group: [(col,key)...]}."""
    row2 = [c.value for c in ws[2]]
    starts = [i for i, v in enumerate(row2) if v is not None and _norm(v).startswith("เป้าหมาย")]
    if len(starts) != 6:
        raise XlsxLayoutError(f"{path}: expected 6 age-group blocks, found {len(starts)}")
    ncols = ws.max_column
    ends = starts[1:] + [ncols]
    widths = [e - s for s, e in zip(starts, ends)]
    if widths[0] == 22 and set(widths[1:]) == {21}:
        has_gender = False
    elif widths[0] == 24 and set(widths[1:]) == {23}:
        has_gender = True
    else:
        raise XlsxLayoutError(f"{path}: unexpected block widths {widths}")
    layout = {}
    for g, s in zip(GROUPS, starts):
        keys = dspm_keys(g, has_gender)
        assert len(keys) == (ends[GROUPS.index(g)] - s)
        cols = []
        for off, k in enumerate(keys):
            col = s + off
            head = "".join(_norm(ws.cell(r, col + 1).value) for r in (2, 3, 4))
            need = _DSPM_HEADER[k]
            ok = need in head and not (k == "pct_normal" and "ครั้งแรก" in head) \
                and not (k == "pct_screened" and False)
            if k == "normal_after" and "ร้อยละ" in head:
                ok = False
            if not ok:
                raise XlsxLayoutError(f"{path}: group {g} col {col} key {k}: header {head!r} lacks {need!r}")
            cols.append((col, k))
        layout[g] = cols
    return layout, has_gender


def _rows(ws, first_row, ncols):
    out = []
    for r in range(first_row, ws.max_row + 1):
        vals = [c.value for c in ws[r]]
        if all(v is None for v in vals):
            continue
        out.append((r, vals))
    return out


def read_workbook(path: Path, indicator: str) -> dict:
    path = Path(path)
    ws = openpyxl.load_workbook(path, data_only=True).active
    header = _norm(ws.cell(1, 1).value)
    if header not in LEVEL_BY_HEADER:
        raise XlsxLayoutError(f"{path}: unknown column-A header {header!r}")
    year = int(path.parent.name)
    rows_raw = _rows(ws, 5 if indicator == "dspm" else 3, ws.max_column)
    info = {"path": str(path), "year": year, "indicator": indicator, "header": header,
            "level": LEVEL_BY_HEADER[header]}
    if indicator == "dspm":
        layout, has_gender = _dspm_layout(ws, path)
        info["has_gender"] = has_gender
        conv = lambda vals: {g: {k: _num(vals[c]) for c, k in cols} for g, cols in layout.items()}
    else:
        colmap = {}
        for c in range(1, ws.max_column):
            m = re.search(r"\((\d+)\)", str(ws.cell(2, c + 1).value or ""))
            if m:
                n = int(m.group(1))
                if n != c:
                    raise XlsxLayoutError(f"{path}: coverage column {c} header says ({n})")
                colmap[c] = COVERAGE_KEYS[n]
        if set(colmap.values()) < set(list(COVERAGE_KEYS.values())[:10]):
            raise XlsxLayoutError(f"{path}: coverage columns missing: {colmap}")
        info["columns"] = sorted(colmap.values())
        conv = lambda vals: {k: _num(vals[c]) for c, k in colmap.items()}
    rows, total = [], None
    for i, (r, vals) in enumerate(rows_raw):
        label = "" if vals[0] is None else str(vals[0]).strip()
        rec = {"label": label, "excel_row": r, "values": conv(vals)}
        if label == "รวม" or (label == "" and i == len(rows_raw) - 1):
            if total is not None:
                raise XlsxLayoutError(f"{path}: two total rows")
            total = rec
        elif label == "":
            raise XlsxLayoutError(f"{path}: blank label on row {r}")
        else:
            rows.append(rec)
    info["rows"], info["total"] = rows, total
    return info


def discover(excel_dir: Path, indicator: str) -> list[dict]:
    """Read every workbook of an indicator under excel_dir/<indicator>/<year>/*.xlsx."""
    out = []
    base = Path(excel_dir) / indicator
    if not base.exists():
        return out
    for f in sorted(base.glob("*/*.xlsx")):
        if f.name.startswith("~$"):
            continue
        out.append(read_workbook(f, indicator))
    return out
