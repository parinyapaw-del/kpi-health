"""Shared helpers for indicator plugins."""
from __future__ import annotations

PCT_TOL = 0.06  # percent-field tolerance (Excel rounds to 2 decimals)


def pct(num, den):
    """100*num/den rounded to 2 decimals; None when either side missing or den == 0."""
    if num is None or den in (None, 0):
        return None
    return round(100.0 * num / den, 2)


def add(*vals):
    if any(v is None for v in vals):
        return None
    return sum(vals)


def ssum(vals):
    """Sum ignoring None; None if all None."""
    vs = [v for v in vals if v is not None]
    return sum(vs) if vs else None


def fmt_asof(date_com: str) -> str:
    """'202609290908' (CE, YYYYMMDDhhmm) -> '2569-09-29T09:08' (Buddhist-year ISO)."""
    s = str(date_com)
    return f"{int(s[0:4]) + 543}-{s[4:6]}-{s[6:8]}T{s[8:10]}:{s[10:12]}"


def close(a, b, tol=PCT_TOL):
    return a is not None and b is not None and abs(a - b) <= tol + 1e-9


# ------------------------------------------------------------------ percent formulas (single source per plugin)
# Each plugin defines PCT = {pct_key: (numerator_key, denominator_key)}; derive / META / check_values / compare
# all read it, so a formula is written exactly once.
def derive_pcts(pcts: dict, d: dict) -> None:
    """Fill every missing percent of `d` in place from its counts (provided percents, e.g. Excel, are kept)."""
    for k, (n, den) in pcts.items():
        if d.get(k) is None:
            d[k] = pct(d.get(n), d.get(den))


def check_pcts(pcts: dict, v: dict, where: str) -> list[tuple[str, str]]:
    """Hard issues for percents that disagree with num/den*100 (or are non-zero with a zero denominator)."""
    issues = []
    for k, (n, den) in pcts.items():
        num, d = v.get(n), v.get(den)
        if num is None or d is None:
            continue
        if d == 0:
            if v.get(k) not in (None, 0):
                issues.append(("hard", f"{where} {k}={v.get(k)} but denominator {den}=0"))
        elif v.get(k) is not None and not close(v[k], 100.0 * num / d):
            issues.append(("hard", f"{where} {k}={v[k]} != {num}/{d}*100={100.0 * num / d:.2f}"))
    return issues


def compare_values(pcts: dict, api: dict, xl: dict, keys, prefix: str = "", tolerant=()) -> list[str]:
    """API-built vs Excel values of one row/group. Percents (and `tolerant` keys) compare within PCT_TOL; a percent
    whose API denominator is 0 (API value None) only has to be 0/blank in Excel. Counts compare exactly."""
    bad = []
    for k in keys:
        a, x = api.get(k), xl.get(k)
        if x is None:
            continue
        if k in pcts and api.get(pcts[k][1]) == 0:
            if x not in (0, None):
                bad.append(f"{prefix}{k}: api den=0 (None) vs excel {x}")
            continue
        if k in pcts or k in tolerant:
            if not close(a, x):
                bad.append(f"{prefix}{k}: api {a} vs excel {x}")
        elif a != x:
            bad.append(f"{prefix}{k}: api {a} vs excel {x}")
    return bad


# ------------------------------------------------------------------ unit-location fallback (Phase 2 spec §4.3)
def fallback_tambon(areas: dict):
    """Fallback location of a reporting unit the GIS registry does not know: the areacode6 where the unit has its
    largest DSPM target, ties -> lowest code; None when `areas` is empty.
    Canonical input = the unit's areas of ONE fiscal year (dspm.resolve_tambons, what the web uses; verified 100%
    against the HDC ตำบล Excel 2569). units.json `missing[h].maxTargetArea` applies the same rule to the targets
    summed over all configured years and is informational only."""
    if not areas:
        return None
    return sorted(areas.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
