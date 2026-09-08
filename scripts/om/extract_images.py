"""
Stage 3b - Image harvest.

Pulls embedded raster images out of the broker package (and any other PDF asked
for), scores them for use as slide photography, and writes the keepers to
<out>/photos/ with a sidecar index carrying the source page for each one.

Rejects: logos, maps, icons, charts, page furniture. The heuristics are size,
aspect ratio, colour variance and how much of the page the image covers -- a
photo on a broker page is large, colourful and roughly rectangular; a logo is
small and flat; a chart is large but has few distinct colours.

Usage:  python3 extract_images.py <pdf> <out_dir> [--pages 1,2,3] [--min-px 400]
"""
import argparse
import hashlib
import json
from pathlib import Path

import pymupdf
from PIL import Image, ImageStat


def _ahash(img: Image.Image) -> int:
    """64-bit average hash, for spotting the same shot re-cropped or re-scaled."""
    small = img.convert("L").resize((8, 8), Image.LANCZOS)
    px = list(small.getdata())
    mean = sum(px) / 64.0
    bits = 0
    for i, p in enumerate(px):
        if p > mean:
            bits |= 1 << i
    return bits


def _near_duplicate(h: int, seen_hashes, threshold: int = 6) -> bool:
    return any(bin(h ^ other).count("1") <= threshold for other in seen_hashes)


def _score(img: Image.Image):
    """Return (is_photo, metrics)."""
    w, h = img.size
    ar = w / h if h else 0
    small = img.convert("RGB").resize((64, 64))
    stat = ImageStat.Stat(small)
    var = sum(stat.stddev) / 3.0
    colours = len(set(small.getdata()))
    metrics = {"w": w, "h": h, "aspect": round(ar, 3),
               "stddev": round(var, 2), "colours": colours}
    if w < 400 or h < 300:
        return False, metrics | {"reject": "too_small"}
    if ar < 0.4 or ar > 4.0:
        return False, metrics | {"reject": "extreme_aspect"}
    if var < 18:
        return False, metrics | {"reject": "flat"}          # logo / solid block
    if colours < 900:
        return False, metrics | {"reject": "low_colour"}    # chart / diagram
    return True, metrics


def harvest(pdf_path: Path, out_dir: Path, pages=None, min_px=400):
    photos_dir = out_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(pdf_path))
    index, seen, hashes = [], set(), []

    for pno in range(doc.page_count):
        if pages and (pno + 1) not in pages:
            continue
        page = doc[pno]
        for info in page.get_images(full=True):
            xref = info[0]
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                raw = pix.tobytes("png")
            except Exception:
                continue
            digest = hashlib.sha1(raw).hexdigest()[:16]
            if digest in seen:
                continue
            seen.add(digest)

            tmp = photos_dir / f"{digest}.png"
            tmp.write_bytes(raw)
            with Image.open(tmp) as im:
                keep, metrics = _score(im)
                h = _ahash(im) if keep else None
            if not keep:
                tmp.unlink(missing_ok=True)
                continue
            # Broker decks reuse the same photograph at different crops across
            # section dividers; a gallery that shows it twice looks like a bug.
            if _near_duplicate(h, hashes):
                tmp.unlink(missing_ok=True)
                continue
            hashes.append(h)
            index.append({"file": tmp.name, "source_pdf": pdf_path.name,
                          "page": pno + 1, "xref": xref, "ahash": h, **metrics})

    # Deterministic ordering: page, then largest first, then digest.
    index.sort(key=lambda r: (r["page"], -(r["w"] * r["h"]), r["file"]))
    (out_dir / "photos_index.json").write_text(json.dumps(index, indent=2))
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--pages", default="")
    ap.add_argument("--min-px", type=int, default=400)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",") if x.strip()} or None
    idx = harvest(Path(a.pdf), Path(a.out), pages, a.min_px)
    print(json.dumps(idx, indent=2)[:4000])
    print(f"\n{len(idx)} photos kept")


if __name__ == "__main__":
    main()
