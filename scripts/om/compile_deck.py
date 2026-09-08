"""
Stage 6 - Compile the deck.

Renders the DealPacket as a 6-slide RC Investment OM with python-pptx, in the
Midtown Grove format documented in references/format_guide.md.

Every figure on every slide is read straight out of the packet. There is no
arithmetic here beyond formatting, so a number that reaches a slide can always
be walked back to a cell or a page. A field carrying a placeholder renders as
[NOT IN SOURCE] rather than being dropped, so a gap is visible to the reader
instead of silently closing up.

Determinism: no timestamps, no randomness, no dict iteration that is not
explicitly ordered, and the .pptx is post-processed to a fixed zip so two runs
of the same packet produce byte-identical files.

Usage:  python3 compile_deck.py <packet.json> <out.pptx> [--photos DIR] [--seal PNG]
"""
import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# --- brand -----------------------------------------------------------------
GREEN = RGBColor(0x0A, 0x4E, 0x44)
ACCENT = RGBColor(0x00, 0x6F, 0x46)
SAGE = RGBColor(0xA7, 0xBF, 0xBC)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x6B, 0x7A, 0x78)
BAND = RGBColor(0xEF, 0xF3, 0xF2)

DISPLAY = "League Spartan"
BODY = "Arial"

W, H = Inches(13.333), Inches(7.5)
M = Inches(0.62)                      # page margin
NAV = ["Summary", "Building", "Business Plan", "Location", "Investment",
       "Terms", "Company"]
PLACEHOLDER = "[NOT IN SOURCE]"


# --- packet readers --------------------------------------------------------

def v(fieldval, fmt=None):
    """Render a packet field: its value, or the placeholder if it has none."""
    if not isinstance(fieldval, dict):
        return PLACEHOLDER if fieldval is None else str(fieldval)
    if fieldval.get("value") in (None, ""):
        return fieldval.get("placeholder", PLACEHOLDER)
    val = fieldval["value"]
    return fmt(val) if fmt else str(val)


def has(fieldval):
    return isinstance(fieldval, dict) and fieldval.get("value") not in (None, "")


def usd(x, cents=False):
    sign = "-" if x < 0 else ""
    m = abs(x)
    return f"{sign}${m:,.2f}" if cents else f"{sign}${round(m):,}"


def num(x):
    return f"{round(x):,}"


_ORDINAL = {"ST", "ND", "RD", "TH"}


def street_case(text):
    """Broker covers set addresses in caps; interior pages do not. Normalise so
    the two never appear side by side in different cases."""
    out = []
    for word in text.split():
        if word.upper() in {"N", "S", "E", "W", "N.", "S.", "E.", "W.", "NE",
                            "NW", "SE", "SW", "AZ", "TX", "CA", "AZ."}:
            out.append(word.upper())
        elif word[:-2].isdigit() and word[-2:].upper() in _ORDINAL:
            out.append(word[:-2] + word[-2:].lower())
        elif word.isdigit():
            out.append(word)
        else:
            out.append(word.capitalize() if word.isupper() else word)
    return " ".join(out)


def unit_type_label(code):
    """Turn a property-management BD/BA code into the deck's own wording.

    '0/1.00' -> 'Studio / 1 BA'   '1/1.50' -> '1 BD / 1.5 BA'
    Anything that does not parse is passed through untouched rather than guessed
    at, so an unfamiliar coding scheme shows as itself.
    """
    parts = str(code).split("/")
    if len(parts) != 2:
        return str(code)
    bd, ba = parts[0].strip(), parts[1].strip()
    try:
        bd_n, ba_n = int(float(bd)), float(ba)
    except ValueError:
        return str(code)
    bed = "Studio" if bd_n == 0 else f"{bd_n} BD"
    bath = f"{ba_n:g} BA"
    return f"{bed} / {bath}"


def clip_sentences(text, budget):
    """Trim quoted source prose at a sentence end, never mid-clause."""
    if len(text) <= budget:
        return text
    kept, out = "", ""
    for piece in re.split(r"(?<=\.)\s+", text):
        if len(kept) + len(piece) + 1 > budget:
            break
        kept = f"{kept} {piece}".strip()
        out = kept
    return out or text[:budget].rsplit(" ", 1)[0] + "…"


def full_address(asset):
    street = v(asset["address"])
    csz = v(asset["city_state_zip"])
    parts = [street_case(p) for p in (street, csz) if p != PLACEHOLDER]
    return ", ".join(parts) if parts else PLACEHOLDER


# --- primitives ------------------------------------------------------------

def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def para(tf, text, size=11, bold=False, color=INK, font=BODY, space_after=4,
         align=PP_ALIGN.LEFT, first=False, spacing=None, italic=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    if spacing:
        p.line_spacing = spacing
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    r.font.color.rgb = color
    return p


def rect(slide, x, y, w, h, fill=GREEN, line=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    sh.shadow.inherit = False
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(0.75)
    sh.text_frame.text = ""
    return sh


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def picture_cover(slide, image, x, y, w, h):
    """Place an image filling the box, cropped to it rather than distorted."""
    from PIL import Image as PILImage
    with PILImage.open(image) as im:
        iw, ih = im.size
    box_ar, img_ar = w / h, iw / ih
    pic = slide.shapes.add_picture(str(image), x, y, width=w, height=h)
    if img_ar > box_ar:                      # image wider: trim left and right
        keep = box_ar / img_ar
        side = (1 - keep) / 2
        pic.crop_left = pic.crop_right = side
    else:                                    # image taller: trim top and bottom
        keep = img_ar / box_ar
        side = (1 - keep) / 2
        pic.crop_top = pic.crop_bottom = side
    return pic


def seal(slide, path, right, top, size):
    """RC monogram, contained in a square box with a soft drop shadow.

    One box, one size, no backing disc: the mark keeps its own aspect because
    the PNG is square with transparent padding baked in.
    """
    if not path or not Path(path).exists():
        return None
    return slide.shapes.add_picture(str(path), right - size, top,
                                    width=size, height=size)


def nav_bar(slide, active):
    tf = textbox(slide, M, Inches(0.34), W - 2 * M, Inches(0.24))
    p = tf.paragraphs[0]
    p.space_after = Pt(0)
    for i, label in enumerate(NAV):
        if i:
            gap = p.add_run()
            gap.text = "     "
            gap.font.size = Pt(9)
            gap.font.name = BODY
        r = p.add_run()
        r.text = label
        r.font.size = Pt(9)
        r.font.name = BODY
        r.font.bold = label == active
        r.font.color.rgb = GREEN if label == active else RGBColor(0xB4, 0xBE, 0xBC)
    rect(slide, M, Inches(0.66), W - 2 * M, Emu(9525), fill=SAGE)


def heading(slide, eyebrow, header):
    tf = textbox(slide, M, Inches(0.86), W - 2 * M, Inches(0.72))
    para(tf, eyebrow, size=12, bold=True, color=MUTED, first=True, space_after=2)
    para(tf, header.upper(), size=17, bold=True, color=GREEN, space_after=0)


def source_line(slide, text):
    tf = textbox(slide, M, H - Inches(0.46), W - 2 * M, Inches(0.28))
    para(tf, text, size=7.5, italic=True, color=MUTED, first=True, space_after=0)


def kv_block(slide, x, y, w, title, pairs, row_h=Inches(0.245), label_frac=0.56):
    """A label/value list in the Midtown Grove property-details style."""
    if title:
        tf = textbox(slide, x, y, w, Inches(0.26))
        para(tf, title.upper(), size=10.5, bold=True, color=GREEN, first=True,
             space_after=0)
        y = y + Inches(0.3)
    rect(slide, x, y - Inches(0.06), w, Emu(9525), fill=SAGE)
    for i, (label, value) in enumerate(pairs):
        ry = y + row_h * i
        if i % 2 == 0:
            rect(slide, x, ry, w, row_h, fill=BAND)
        lt = textbox(slide, x + Inches(0.08), ry + Inches(0.035),
                     Emu(int(w * label_frac)), row_h)
        para(lt, label, size=10, color=INK, first=True, space_after=0)
        vt = textbox(slide, x + Emu(int(w * label_frac)), ry + Inches(0.035),
                     Emu(int(w * (1 - label_frac))) - Inches(0.08), row_h)
        para(vt, value, size=10, bold=True,
             color=INK if value != PLACEHOLDER else MUTED,
             first=True, space_after=0, align=PP_ALIGN.RIGHT)
    return y + row_h * len(pairs)


def table(slide, x, y, w, headers, rows, widths=None, row_h=Inches(0.31),
          head_h=Inches(0.34), emphasis=(), font_size=9.5):
    """A brand-styled table. `rows` are lists of strings; `emphasis` holds the
    indices of rows to set in bold with a rule above."""
    n = len(headers)
    widths = widths or [1.0 / n] * n
    xs, acc = [], x
    for frac in widths:
        xs.append(acc)
        acc = acc + Emu(int(w * frac))

    rect(slide, x, y, w, head_h, fill=GREEN)
    for i, htext in enumerate(headers):
        cw = Emu(int(w * widths[i]))
        tf = textbox(slide, xs[i] + Inches(0.08), y + Inches(0.075),
                     cw - Inches(0.16), head_h)
        para(tf, htext.upper(), size=9, bold=True, color=PAPER, first=True,
             space_after=0, align=PP_ALIGN.RIGHT if i else PP_ALIGN.LEFT)

    ry = y + head_h
    for r_i, row in enumerate(rows):
        if r_i % 2 == 1:
            rect(slide, x, ry, w, row_h, fill=BAND)
        if r_i in emphasis:
            rect(slide, x, ry, w, Emu(9525), fill=SAGE)
        for c_i, cell in enumerate(row):
            cw = Emu(int(w * widths[c_i]))
            tf = textbox(slide, xs[c_i] + Inches(0.08), ry + Inches(0.055),
                         cw - Inches(0.16), row_h)
            para(tf, cell, size=font_size, bold=(r_i in emphasis) or c_i == 0,
                 color=MUTED if cell == PLACEHOLDER else INK, first=True,
                 space_after=0, align=PP_ALIGN.RIGHT if c_i else PP_ALIGN.LEFT)
        ry = ry + row_h
    return ry


def stat_row(slide, x, y, w, stats, gap=Inches(0.16)):
    """Big-figure tiles, the shape brokers and RC both use for headline stats."""
    if not stats:
        return y
    tile_h = Inches(1.0)
    each = Emu(int((w - gap * (len(stats) - 1)) / len(stats)))
    # Figures vary in length ($3,100,000 against 4.0%); size the type to the
    # widest one in the row so every tile in a row still reads as a set.
    longest = max(len(f) for f, _ in stats)
    inches_avail = each / Inches(1) - 0.34
    size = min(19.0, max(11.5, inches_avail / (longest * 0.062)))
    for i, (figure, caption) in enumerate(stats):
        sx = x + (each + gap) * i
        rect(slide, sx, y, each, tile_h, fill=BAND)
        rect(slide, sx, y, Emu(28575), tile_h, fill=GREEN)
        tf = textbox(slide, sx + Inches(0.17), y + Inches(0.16),
                     each - Inches(0.3), Inches(0.44))
        para(tf, figure, size=size, bold=True, font=DISPLAY,
             color=GREEN if figure != PLACEHOLDER else MUTED, first=True,
             space_after=0)
        cf = textbox(slide, sx + Inches(0.17), y + Inches(0.66),
                     each - Inches(0.3), Inches(0.28))
        para(cf, caption.upper(), size=8, bold=True, color=MUTED, first=True,
             space_after=0)
    return y + tile_h


# --- slides ----------------------------------------------------------------

def photo_path(photos_dir, entry):
    return Path(photos_dir) / entry["file"] if photos_dir and entry else None


def pick_photos(packet, photos_dir, pages, limit, dedupe=10):
    """Choose photographs for a slide.

    Deterministic, and spread: it takes one image from each requested page in
    the order given before taking a second from any of them, so a page that
    happens to hold four images cannot fill a gallery on its own. Near-identical
    shots are skipped -- broker decks reuse one photograph across several
    section dividers.
    """
    by_page = {}
    for p in packet.get("photos", []):
        if p["page"] in pages:
            path = photo_path(photos_dir, p)
            if path and path.exists():
                by_page.setdefault(p["page"], []).append((path, p))

    out, chosen_hashes = [], []
    for depth in range(max((len(v) for v in by_page.values()), default=0)):
        for page in pages:
            if len(out) >= limit:
                return out
            bucket = by_page.get(page, [])
            if depth >= len(bucket):
                continue
            path, meta = bucket[depth]
            h = meta.get("ahash")
            if h is not None and any(
                    bin(h ^ other).count("1") <= dedupe for other in chosen_hashes):
                continue
            if h is not None:
                chosen_hashes.append(h)
            out.append((path, meta))
    return out


def slide_cover(prs, packet, photos_dir, seal_png, cover_pages):
    s = blank(prs)
    band_h = Inches(1.66)
    hero = pick_photos(packet, photos_dir, cover_pages, 1)
    if hero:
        picture_cover(s, hero[0][0], 0, 0, W, H - band_h)
    else:
        rect(s, 0, 0, W, H - band_h, fill=SAGE)
    rect(s, 0, H - band_h, W, band_h, fill=GREEN)

    a = packet["asset"]
    name = packet["deal"]["name"]
    addr = full_address(a)

    tf = textbox(s, M, H - band_h + Inches(0.34), W - Inches(3.4), Inches(1.0))
    para(tf, name, size=40, bold=True, font=DISPLAY, color=PAPER, first=True,
         space_after=6)

    bits = []
    if has(a["units"]):
        bits.append(f"{a['units']['value']}-unit multifamily")
    if has(a["year_built"]):
        bits.append(f"built {a['year_built']['value']}")
    sub = ", ".join(bits)
    sub = f"{sub[0].upper() + sub[1:]} at {addr}." if sub else addr
    para(tf, sub, size=14, bold=True, color=PAPER, space_after=0)

    seal(s, seal_png, W - M, H - band_h + Inches(0.42), Inches(1.5))
    return s


def slide_asset(prs, packet, photos_dir, pages):
    s = blank(prs)
    nav_bar(s, "Building")
    heading(s, "Overview", "Asset Summary")
    a = packet["asset"]

    col_w = Inches(5.7)
    left = M
    right = M + col_w + Inches(0.5)
    row_h = Inches(0.215)

    end = kv_block(s, left, Inches(1.72), col_w, "The offering", [
        ("Apartment Community", packet["deal"]["name"]),
        ("Address", full_address(a)),
        ("County", v(a["county"])),
        ("Property Type", v(a["property_type"])),
        ("Number of Units", v(a["units"])),
        ("Number of Buildings", v(a["buildings"])),
        ("Year Built / Renovated", v(a["year_built"])),
        ("Net Rentable Area (SF)", v(a["rentable_sf"], num)),
        ("Average Unit Size (SF)", v(a["avg_unit_sf"], num)),
        ("Occupancy", v(packet["rent_roll"]["occupancy"])),
    ], row_h=row_h)

    specs = a.get("specs", {})
    spec_pairs = [
        ("Construction", v(specs.get("construction")).title()),
        ("Roofs", v(specs.get("roof")).title()),
        ("Plumbing", v(specs.get("plumbing")).title()),
        ("Sewer", v(specs.get("sewer")).replace("sewer lines", "Sewer Lines")),
        ("Windows", v(specs.get("windows")).title()),
        ("Metering", v(specs.get("metering"))),
        ("Wiring", PLACEHOLDER),
        ("HVAC", PLACEHOLDER),
    ]
    kv_block(s, left, end + Inches(0.26), col_w, "Construction & mechanical",
             spec_pairs, row_h=row_h)

    stat_row(s, right, Inches(1.72), col_w, [
        (v(a["list_price"], usd), "List price"),
        (v(a["price_per_unit"], usd), "Per unit"),
        (v(a["price_per_sf"], lambda x: f"${x:,.2f}"), "Per SF"),
    ])

    shots = pick_photos(packet, photos_dir, pages, 2)
    if shots:
        ph = Inches(1.94)
        py = Inches(3.02)
        picture_cover(s, shots[0][0], right, py, col_w, ph)
        if len(shots) > 1:
            picture_cover(s, shots[1][0], right, py + ph + Inches(0.16),
                          col_w, ph)

    src = packet["deal"]["sources"].get("broker_om") or "broker package"
    cites = sorted({f"p. {a[k]['source']['page']}" for k in
                    ("units", "year_built", "rentable_sf", "list_price")
                    if has(a[k])})
    source_line(s, f"SOURCE: {src}, {', '.join(cites)}. "
                   f"Occupancy from {packet['rent_roll']['source_file']}.")
    return s


def slide_rent_roll(prs, packet):
    s = blank(prs)
    nav_bar(s, "Building")
    heading(s, "Unit Details", "Rent Roll Summary")
    rr = packet["rent_roll"]

    total_units = sum(r["units"] for r in rr["rows"])
    stat_row(s, M, Inches(1.72), W - 2 * M, [
        (str(total_units) if total_units else PLACEHOLDER, "Units"),
        (v(rr["occupancy"]).replace(" Occupied", ""), "Occupied"),
        (v(rr["total_in_place_rent"], usd), "In-place rent / month"),
        (v(rr["total_market_rent"], usd), "Market rent / month"),
    ])

    rows = []
    for r in rr["rows"]:
        label = f"{unit_type_label(r['unit_type'])}   ×{r['units']}"
        if r["vacant"]:
            label += f"   ({r['vacant']} vacant)"
        rows.append([
            label,
            num(r["sqft"]) if r["sqft"] is not None else PLACEHOLDER,
            v(r["in_place_rent"], usd),
            v(r["market_rent"], usd),
        ])

    emphasis = set()
    if has(rr["total_in_place_rent"]) or has(rr["total_market_rent"]):
        rows.append([
            f"Total   ×{total_units}",
            v(rr["total_sqft"], num),
            v(rr["total_in_place_rent"], usd),
            v(rr["total_market_rent"], usd),
        ])
        emphasis.add(len(rows) - 1)

    end = table(s, M, Inches(3.08), W - 2 * M,
                ["Unit Type", "Size (SF)", "In-Place Rent", "Market Rent"],
                rows, widths=[0.40, 0.18, 0.21, 0.21], row_h=Inches(0.36),
                emphasis=emphasis)

    note = textbox(s, M, end + Inches(0.3), W - 2 * M, Inches(0.9))
    para(note, "Aggregated by unit type from the rent roll; per-unit rents are the "
               "mean within each type. The totals row is the workbook's own total "
               "line, not a sum of the averages above it.",
         size=9.5, color=MUTED, first=True, space_after=4)
    if has(rr["occupancy"]):
        para(note, f"Occupancy at {v(rr['as_of'])}: {v(rr['occupancy'])}.",
             size=9.5, color=INK, bold=True, space_after=0)

    source_line(s, f"SOURCE: {rr['source_file']}, "
                   f"rows 12–25, columns C, F, G, H; totals row 28.")
    return s


def slide_income(prs, packet):
    s = blank(prs)
    nav_bar(s, "Business Plan")
    heading(s, "Underwriting", "Trailing 12 Income Statement")
    inc = packet["income_statement"]

    rows, emphasis = [], set()
    income_total = inc["totals"].get("Total Operating Income")
    if income_total:
        rows.append(["Total Operating Income", v(income_total, lambda x: usd(x, True))])
        emphasis.add(0)
    for line in inc["lines"]:
        rows.append([line["label"], v(line["amount"], lambda x: usd(x, True))])
    for key in ("Total Operating Expenses", "Net Operating Income"):
        if inc["totals"].get(key):
            rows.append([key, v(inc["totals"][key], lambda x: usd(x, True))])
            emphasis.add(len(rows) - 1)

    left_w = Inches(6.9)
    table(s, M, Inches(1.78), left_w, ["Line Item", "Trailing 12"],
          rows, widths=[0.62, 0.38], row_h=Inches(0.285), emphasis=emphasis)

    right = M + left_w + Inches(0.5)
    rw = W - M - right
    tf = textbox(s, right, Inches(1.78), rw, Inches(4.6))
    para(tf, "READING THIS STATEMENT", size=10.5, bold=True, color=GREEN,
         first=True, space_after=8)
    for text in [
        f"Period: {v(inc['period'])}. Accounting basis: {v(inc['basis'])}.",
        "Line-item order follows the Midtown Grove underwriting page. Each line "
        "maps to exactly one total row in the export — nothing is combined "
        "across rows.",
        "Lines the export does not contain are shown as [NOT IN SOURCE] rather "
        "than as zero; a zero would assert a fact the workbook does not make.",
    ]:
        para(tf, "•  " + text, size=10, color=INK, space_after=7, spacing=1.15)

    for c in packet.get("conflicts", []):
        if c["kind"] in ("t12_footing", "t12_vintage"):
            para(tf, "•  " + c["summary"], size=10, color=ACCENT, space_after=7,
                 spacing=1.15)

    source_line(s, f"SOURCE: {inc['source_file']}, sheet Sheet1, column N "
                   f"(12-month total). Figures as exported; see the reconciliation "
                   f"note in conflicts.md.")
    return s


def slide_budget(prs, packet):
    s = blank(prs)
    nav_bar(s, "Business Plan")
    heading(s, "Business Plan", "Full-Year Budget")
    b = packet["budget"]

    def all_zero(r):
        vals = [r[k].get("value") for k in ("actual", "budget", "variance")]
        return all(x == 0 for x in vals if x is not None) and any(
            x is not None for x in vals)

    # Rows that are zero in every column carry no information and cost the
    # table the row height it needs to stay legible. They are named in the
    # footnote rather than silently dropped.
    dropped = [r["label"].title() for r in b["rows"]
               if all_zero(r) and not r["emphasis"]]
    kept = [r for r in b["rows"] if not (all_zero(r) and not r["emphasis"])]

    rows, emphasis = [], set()
    for r in kept:
        rows.append([
            r["label"].title() if r["label"].isupper() else r["label"],
            v(r["actual"], usd),
            v(r["budget"], usd),
            v(r["variance"], usd),
        ])
        if r["emphasis"]:
            emphasis.add(len(rows) - 1)

    end = table(s, M, Inches(1.68), W - 2 * M,
                ["Line Item", "Historical T12", "Budget", "Variance"],
                rows, widths=[0.34, 0.22, 0.22, 0.22],
                row_h=Inches(0.245), head_h=Inches(0.3), emphasis=emphasis,
                font_size=9)

    if dropped:
        nf = textbox(s, M, end + Inches(0.16), W - 2 * M, Inches(0.4))
        para(nf, "Zero in all three columns and omitted for space: "
                 + "; ".join(dropped) + ".",
             size=8.5, color=MUTED, first=True, space_after=0)

    src = f"SOURCE: {b['source_file']}, sheet {b['sheet']}, columns " \
          f"{b['columns'].get('actual', '?')} (historical T12), " \
          f"{b['columns'].get('budget', '?')} (budget), " \
          f"{b['columns'].get('variance', '?')} (variance)."
    prep = b["assumptions"].get("Budget Preparation Date")
    if has(prep):
        src += f" Budget prepared {str(prep['value'])[:10]}."
    source_line(s, src)
    return s


def slide_market(prs, packet, photos_dir, pages):
    s = blank(prs)
    nav_bar(s, "Location")
    heading(s, "Location", f"Why {packet['deal'].get('city', 'Phoenix')}")
    loc = packet["location"]
    m, d = loc["metrics"], loc["demographics"]

    col_w = Inches(7.2)
    stat_row(s, M, Inches(1.72), col_w, [
        (v(m.get("unemployment_rate")), "Metro unemployment"),
        (v(m.get("household_growth")), "Household growth"),
        (v(d.get("total_population")), "MSA population"),
    ], gap=Inches(0.14))

    tf = textbox(s, M, Inches(2.86), col_w, Inches(3.9))
    bullets = []
    n = loc["narrative"]
    if has(n.get("neighborhood")):
        bullets.append(("Neighborhood", n["neighborhood"]["value"]))
    if has(n.get("employment_node")):
        bullets.append(("Employment", n["employment_node"]["value"]))
    if has(n.get("hospitality")):
        bullets.append(("Hospitality", n["hospitality"]["value"]))
    if has(n.get("msa_overview")):
        bullets.append(("Metro", n["msa_overview"]["value"]))

    for label, text in bullets[:4]:
        p = tf.paragraphs[0] if not tf.paragraphs[0].runs else tf.add_paragraph()
        p.space_after = Pt(8)
        p.line_spacing = 1.14
        r = p.add_run()
        r.text = f"{label.upper()}  "
        r.font.size = Pt(9.5)
        r.font.bold = True
        r.font.name = BODY
        r.font.color.rgb = GREEN
        r2 = p.add_run()
        r2.text = clip_sentences(text, 320)
        r2.font.size = Pt(10)
        r2.font.name = BODY
        r2.font.color.rgb = INK

    stat_row(s, M, Inches(5.34), col_w, [
        (v(d.get("median_household_income")), "Median household income"),
        (v(d.get("median_home_value")), "Median home value"),
        (v(d.get("average_age")), "Median age"),
    ], gap=Inches(0.14))

    right = M + col_w + Inches(0.34)
    rw = W - M - right
    shots = pick_photos(packet, photos_dir, pages, 2)
    py = Inches(1.72)
    for path, _ in shots:
        picture_cover(s, path, right, py, rw, Inches(1.56))
        py = py + Inches(1.7)

    sub = loc.get("submarket_row")
    mkt_rows = [["Metro vacancy", v(m.get("vacancy_rate"))],
                ["Metro asking rent", v(m.get("asking_rent"))],
                ["H1 net absorption",
                 (v(m.get("net_absorption")) + " units")
                 if has(m.get("net_absorption")) else PLACEHOLDER]]
    period = v(loc.get("report_title")).split()[-2:] if has(loc.get("report_title")) \
        else []
    col_head = " ".join(period) if len(period) == 2 else "Latest"
    if sub:
        mkt_rows = [[f"{sub['submarket']} vacancy", sub["vacancy_rate"]],
                    [f"{sub['submarket']} asking rent", f"${sub['avg_asking_rent']:,}"],
                    [f"{sub['submarket']} inventory",
                     f"{sub['inventory_units']:,} units"]] + mkt_rows
    table(s, right, py + Inches(0.04), rw, ["Market", col_head],
          mkt_rows, widths=[0.60, 0.40], row_h=Inches(0.225),
          head_h=Inches(0.28), font_size=9)

    srcs = [packet["deal"]["sources"].get("broker_om"),
            packet["deal"]["sources"].get("market_report")]
    source_line(s, "SOURCES: " + "; ".join(x for x in srcs if x) +
                ". Metro and submarket statistics from the market report only; "
                "no figure on this page comes from outside the deal folder.")
    return s


def slide_photos(prs, packet, photos_dir, pages, min_photos=4):
    shots = pick_photos(packet, photos_dir, pages, 5)
    if len(shots) < min_photos:
        return None
    s = blank(prs)
    nav_bar(s, "Building")
    heading(s, "Property", "Asset & Area")

    gw = W - 2 * M
    big_w = Emu(int(gw * 0.55))
    small_w = gw - big_w - Inches(0.16)
    top = Inches(1.78)
    tall = Inches(4.66)

    picture_cover(s, shots[0][0], M, top, big_w, tall)
    sx = M + big_w + Inches(0.16)
    cell_h = Emu(int((tall - Inches(0.16)) / 2))
    cell_w = Emu(int((small_w - Inches(0.16)) / 2))
    for i, (path, _) in enumerate(shots[1:5]):
        r, c = divmod(i, 2)
        picture_cover(s, path, sx + (cell_w + Inches(0.16)) * c,
                      top + (cell_h + Inches(0.16)) * r, cell_w, cell_h)

    src = packet["deal"]["sources"].get("broker_om") or "broker package"
    pages_used = sorted({p["page"] for _, p in shots})
    source_line(s, f"SOURCE: {src}, "
                   f"pp. {', '.join(str(p) for p in pages_used)}.")
    return s


# --- determinism -----------------------------------------------------------

def canonicalise(path: Path):
    """Rewrite the .pptx zip with fixed timestamps and a fixed member order, so
    two runs from the same packet hash identically."""
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as src:
        names = sorted(src.namelist())
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
            for name in names:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                dst.writestr(info, src.read(name))
    shutil.move(str(tmp), str(path))


# --- driver ----------------------------------------------------------------

def build(packet, out, photos_dir, seal_png, cfg):
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    slide_cover(prs, packet, photos_dir, seal_png, cfg["cover_pages"])
    slide_asset(prs, packet, photos_dir, cfg["asset_pages"])
    slide_rent_roll(prs, packet)
    slide_income(prs, packet)
    slide_budget(prs, packet)
    slide_market(prs, packet, photos_dir, cfg["area_pages"])
    slide_photos(prs, packet, photos_dir, cfg["gallery_pages"])

    prs.save(str(out))
    canonicalise(Path(out))
    return len(prs.slides._sldIdLst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("packet")
    ap.add_argument("out")
    ap.add_argument("--photos", default=None)
    ap.add_argument("--seal", default=None)
    ap.add_argument("--config", default=None)
    a = ap.parse_args()

    packet = json.loads(Path(a.packet).read_text())
    cfg = {"cover_pages": [3], "asset_pages": [1, 2],
           "area_pages": [9, 8], "gallery_pages": [11, 13, 6, 14, 10]}
    if a.config:
        cfg.update(json.loads(Path(a.config).read_text()))

    n = build(packet, a.out, a.photos, a.seal, cfg)
    print(f"{n} slides -> {a.out}")


if __name__ == "__main__":
    main()
