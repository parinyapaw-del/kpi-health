#!/usr/bin/env python3
"""Turn data/logo.webp (logo on white) into a transparent RGBA PNG.

Steps (Pillow only):
 1. Background = light pixels (min RGB channel >= LOW) that are connected to the
    image border, plus tiny enclosed light specks (e.g. counters inside Thai/Latin
    letters, area < --hole-area px). Enclosed light areas inside KEEP_BOX (the white
    cross of the emblem) and larger ones stay opaque, so the interior is not hollowed out.
 2. Inside the background region alpha ramps from 255 at min-channel LOW (200)
    down to 0 at HIGH (245); this grades the anti-aliased edge.
 3. Colour of semi-transparent pixels is un-mixed from white (removes white halo).
 4. Crop fully transparent margins (+2% padding), resize to width 800 (LANCZOS).

Usage (repo root): python3 scripts/process_logo.py [--in data/logo.webp] [--out site/assets/logo-angthong.png]
Region-4 logo:     python3 scripts/process_logo.py --in data/logo-r4.jpg --out site/assets/logo-r4.png --mode key --width 800
"""
import argparse
from collections import deque
from pathlib import Path

from PIL import Image

LOW, HIGH = 200, 245
CUT = 40          # alpha below this is JPEG noise / faint glow -> 0
# white cross in the emblem (source pixels x0,y0,x1,y1): enclosed light areas inside stay opaque
KEEP_BOX = (78, 188, 102, 214)
ROOT = Path(__file__).resolve().parent.parent


def background_mask(rgb, hole_area):
    w, h = rgb.size
    px = rgb.load()
    light = [[min(px[x, y]) >= LOW for x in range(w)] for y in range(h)]
    seen = [[False] * w for _ in range(h)]
    bg = [[False] * w for _ in range(h)]
    comps = []
    for sy in range(h):
        for sx in range(w):
            if not light[sy][sx] or seen[sy][sx]:
                continue
            comp, q = [], deque([(sx, sy)])
            seen[sy][sx] = True
            touches = False
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                if x in (0, w - 1) or y in (0, h - 1):
                    touches = True
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and light[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            comps.append((touches, comp))
    for touches, comp in comps:
        cx = sum(x for x, _ in comp) / len(comp)
        cy = sum(y for _, y in comp) / len(comp)
        keep = KEEP_BOX[0] <= cx <= KEEP_BOX[2] and KEEP_BOX[1] <= cy <= KEEP_BOX[3]
        speck = len(comp) < hole_area and not keep
        if touches or speck:
            for x, y in comp:
                bg[y][x] = True
    return bg


def process(src, dst, width=800, pad=0.02, hole_area=60, mode="border"):
    """mode="border": light pixels connected to the border (+ specks) become transparent (emblem interiors stay).
    mode="key": every light pixel is keyed on brightness (for line-art logos such as the region-4 octagon whose
    white interior must be transparent too)."""
    rgb = Image.open(src).convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    bg = [[True] * w for _ in range(h)] if mode == "key" else background_mask(rgb, hole_area)
    out = Image.new("RGBA", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            a = 255
            if bg[y][x]:
                m = min(r, g, b)
                a = 255 if m <= LOW else 0 if m >= HIGH else round(255 * (HIGH - m) / (HIGH - LOW))
                a = 0 if a < CUT else a
            if 0 < a < 255:  # un-mix from white background
                k = a / 255
                r, g, b = (max(0, min(255, round((c - 255 * (1 - k)) / k))) for c in (r, g, b))
            op[x, y] = (r, g, b, a)
    bbox = out.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox is None:
        raise SystemExit("logo is fully transparent - check input")
    l, t, r_, b_ = bbox
    px_pad, py_pad = round((r_ - l) * pad), round((b_ - t) * pad)
    box = (max(0, l - px_pad), max(0, t - py_pad), min(w, r_ + px_pad), min(h, b_ + py_pad))
    out = out.crop(box)
    nh = round(out.height * width / out.width)
    out = out.resize((width, nh), Image.LANCZOS)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, optimize=True)
    return out.size


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="src", default=str(ROOT / "data/logo.webp"))
    ap.add_argument("--out", default=str(ROOT / "site/assets/logo-angthong.png"))
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--hole-area", type=int, default=60, help="enclosed light specks smaller than this (px) become transparent")
    ap.add_argument("--mode", choices=["border", "key"], default="border",
                    help="border = keep enclosed light areas (Angthong emblem); key = all light pixels transparent (region-4 line art)")
    a = ap.parse_args()
    print("saved", a.out, process(a.src, a.out, a.width, hole_area=a.hole_area, mode=a.mode))
