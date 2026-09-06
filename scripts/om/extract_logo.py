#!/usr/bin/env python3
"""Build a cover-ready RC seal from the official raster.

The favicon is a vertically compressed oval (≈183×155) with a grey
alpha fringe. This restores a circle, kills the halo, and writes a
1024² PNG the cover can overlay without stretching.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "public" / "brand" / "RC-Logo_Green_fav.png"
DEST = ROOT / "public" / "brand" / "rc-seal.png"


def tight_crop(arr: np.ndarray, thr: int = 32) -> np.ndarray:
    ys, xs = np.where(arr[:, :, 3] > thr)
    if len(xs) == 0:
        return arr
    return arr[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def unsquash_to_circle(arr: np.ndarray) -> np.ndarray:
    """Scale the short axis up so a squashed oval becomes a circle."""
    h, w = arr.shape[:2]
    side = max(w, h)
    im = Image.fromarray(arr, "RGBA").resize((side, side), Image.Resampling.LANCZOS)
    return np.array(im)


def defringe(arr: np.ndarray) -> np.ndarray:
    """Drop grey/white semi-transparent fringe; snap the green body to opaque."""
    out = arr.copy()
    rgb = out[:, :, :3].astype(np.float32)
    alpha = out[:, :, 3].astype(np.float32)
    lum = rgb.mean(axis=2)
    # gold RC letters: keep
    gold = (rgb[:, :, 0] > 120) & (rgb[:, :, 1] > 90) & (rgb[:, :, 0] > rgb[:, :, 2] + 20)
    # dark green body
    body = (lum < 95) & (rgb[:, :, 1] > rgb[:, :, 0])
    fringe = (alpha < 230) & (lum > 110) & ~gold
    alpha[fringe] = 0
    alpha[body & (alpha > 40)] = 255
    alpha[gold & (alpha > 40)] = 255
    out[:, :, 3] = alpha.astype(np.uint8)
    return out


def pad_square(arr: np.ndarray, pad_ratio: float = 0.06) -> np.ndarray:
    h, w = arr.shape[:2]
    side = max(w, h)
    pad = int(round(side * pad_ratio))
    canvas = np.zeros((side + 2 * pad, side + 2 * pad, 4), dtype=np.uint8)
    y = pad + (side - h) // 2
    x = pad + (side - w) // 2
    canvas[y : y + h, x : x + w] = arr
    return canvas


def extract(src: Path = SRC, dest: Path = DEST, size: int = 1024) -> Path:
    im = Image.open(src).convert("RGBA")
    arr = np.array(im)
    arr = tight_crop(arr)
    arr = unsquash_to_circle(arr)
    arr = defringe(arr)
    arr = tight_crop(arr, thr=16)
    arr = pad_square(arr)
    out = Image.fromarray(arr, "RGBA").resize((size, size), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, "PNG")
    return dest


if __name__ == "__main__":
    path = extract()
    im = Image.open(path)
    print(f"wrote {path} {im.size} {im.mode}")
