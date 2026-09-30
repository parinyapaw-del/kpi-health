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
