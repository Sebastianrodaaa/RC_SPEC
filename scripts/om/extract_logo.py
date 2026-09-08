"""
Stage 3c - Official seal.

RC's monogram sits in the template OM as a stencil (an image mask) composited
against the brand band, so the raw embedded bitmap is useless on its own. This
script instead renders the page region the mark occupies at high DPI -- which
gives the mark exactly as a reader sees it -- then keys the band colour out,
tight-crops to ink, defringes the halo that keying leaves behind, un-squashes a
mark that was placed non-uniformly, and writes a 1024x1024 transparent PNG.

The cover places this file with object-fit: contain and a drop-shadow.
Never a backing disc, never independent width/height.

Usage:
  python3 extract_logo.py <pdf> <out_png> [--page N] [--dpi 900] [--ink white|dark|auto]
"""
import argparse
import io
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

CANVAS = 1024
PAD = 0.94  # fraction of the canvas the mark fills on its long axis


# --- locating ---------------------------------------------------------------

def mark_rects(doc, page_no=None):
    """Candidate placements: small, wide-ish images parked near a page edge."""
    out = []
    pages = [page_no - 1] if page_no else range(doc.page_count)
    for pno in pages:
        page = doc[pno]
        pw, ph = page.rect.width, page.rect.height
        for info in page.get_images(full=True):
            for r in page.get_image_rects(info[0]):
                w, h = r.width, r.height
                if w < 24 or h < 12:
                    continue
                if w > pw * 0.35 or h > ph * 0.25:
                    continue          # too big to be a mark
                if not (0.8 <= w / h <= 4.0):
                    continue
                edge = min(r.x0, r.y0, pw - r.x1, ph - r.y1)
                out.append({"page": pno, "xref": info[0], "rect": r,
                            "area": w * h, "edge": edge})
    # Prefer the largest mark closest to an edge; deterministic tie-break.
    out.sort(key=lambda c: (-c["area"], c["edge"], c["xref"]))
    return out


# --- keying -----------------------------------------------------------------

def _key_out(rgb: np.ndarray, ink: str, ring: int = 6):
    """Return (alpha 0..1, ink RGB) by keying against the surrounding band.

    The clip is rendered with a margin, so the outer ring of the patch is pure
    background whatever the mark is doing inside. Keying on distance from that
    colour -- rather than on a light/dark guess -- handles a reversed mark on a
    brand band and a dark mark on white with the same code path.
    """
    border = np.concatenate([
        rgb[:ring].reshape(-1, 3), rgb[-ring:].reshape(-1, 3),
        rgb[:, :ring].reshape(-1, 3), rgb[:, -ring:].reshape(-1, 3),
    ])
    bg = np.median(border, axis=0)
    dist = np.abs(rgb - bg).sum(axis=2)
    alpha = np.clip((dist - 24.0) / 90.0, 0.0, 1.0)

    if ink == "white":
        fill = (255, 255, 255)
    elif ink == "dark":
        fill = (10, 78, 68)
    else:
        solid = alpha > 0.9
        fill = tuple(int(v) for v in np.median(rgb[solid], axis=0)) if solid.any() \
            else (255, 255, 255)
        # Anti-aliasing drags the median off the true flat colour; snap it back.
        if min(fill) > 215:
            fill = (255, 255, 255)
        elif max(fill) < 40:
            fill = (0, 0, 0)
    return alpha, fill


def normalise(patch: Image.Image, ink: str = "auto") -> Image.Image:
    rgb = np.asarray(patch.convert("RGB")).astype(float)
    alpha, fill = _key_out(rgb, ink)

    solid = alpha > 0.55
    if not solid.any():
        raise ValueError("no ink found in the rendered patch")

    ys, xs = np.where(solid)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    alpha = alpha[y0:y1, x0:x1]

    # Resample the coverage channel ALONE, then paint the flat ink through it.
    # Resizing straight-alpha RGBA blends ink toward the transparent zeros and
    # leaves exactly the grey halo this step exists to remove.
    h, w = alpha.shape
    mask = Image.fromarray((alpha * 255).astype(np.uint8), "L")

    # Un-squash a mark that was placed with unequal scale.
    if 0.72 < w / h < 1.38 and abs(w - h) / max(w, h) > 0.04:
        w = h = max(w, h)
        mask = mask.resize((w, h), Image.LANCZOS)

    scale = (CANVAS * PAD) / max(w, h)
    mask = mask.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                       Image.LANCZOS)

    # Compose in numpy: PIL's paste alpha-composites against the transparent
    # canvas, which would re-introduce grey at every partially covered pixel.
    out = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = fill
    oy = (CANVAS - mask.height) // 2
    ox = (CANVAS - mask.width) // 2
    out[oy:oy + mask.height, ox:ox + mask.width, 3] = np.asarray(mask)
    return Image.fromarray(out, "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--page", type=int, default=None)
    ap.add_argument("--dpi", type=int, default=900)
    ap.add_argument("--ink", default="auto", choices=["auto", "white", "dark"])
    a = ap.parse_args()

    doc = pymupdf.open(a.pdf)
    for cand in mark_rects(doc, a.page):
        page = doc[cand["page"]]
        # Render with a margin so the patch border is guaranteed background.
        r = pymupdf.Rect(cand["rect"])
        mx, my = r.width * 0.14, r.height * 0.14
        clip = pymupdf.Rect(r.x0 - mx, r.y0 - my, r.x1 + mx, r.y1 + my) & page.rect
        pix = page.get_pixmap(clip=clip, dpi=a.dpi, alpha=False)
        # tobytes("png") rather than frombytes(): the raw sample buffer is
        # row-padded, and reading it directly shears the patch.
        patch = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        try:
            seal = normalise(patch, a.ink)
        except ValueError:
            continue
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        seal.save(a.out)
        print(f"seal: page {cand['page'] + 1} xref {cand['xref']} "
              f"rect {[round(v, 1) for v in cand['rect']]} -> {a.out} {seal.size}")
        return
    raise SystemExit("no seal candidate found")


if __name__ == "__main__":
    main()
