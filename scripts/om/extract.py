#!/usr/bin/env python3
"""Deterministic Urbana OM extraction. Numbers come from cells, never an LLM."""
from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

ROOT = Path("/workspace")
SRC_CANDIDATES = [
    Path("/tmp/rc/RC Investments"),
    ROOT / "data" / "urbana" / "source",
]
SKILL_VERSION = "0.1.0"


def find_source() -> Path:
    for p in SRC_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit("No source folder found")


def cell(ws, addr):
    v = ws[addr].value
    return v


def money(v) -> float | None:
    if v is None or v == "":
        return None
    return round(float(v), 2)


def sourced(value, file, locator, snippet, extra=None):
    rec = {
        "value": value,
        "placeholder": None if value is not None else snippet,
        "source": {
            "file": file,
            "locator": locator,
            "snippet": snippet if value is not None else None,
        },
    }
    if extra:
        rec.update(extra)
    return rec


def placeholder(reason, file, locator):
    return {
        "value": None,
        "placeholder": reason,
        "source": {"file": file, "locator": locator, "snippet": None},
    }


def load_t12(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb["Sheet1"]
    fname = path.name
    period = cell(ws, "A7")
    entity = cell(ws, "A4")
    property_line = cell(ws, "A5")
    basis = cell(ws, "A8")
    rows = {
        "subsidized": money(cell(ws, "N16")),
        "loss_gain": money(cell(ws, "N17")),
        "total_rents": money(cell(ws, "N18")),
        "rent_income": money(cell(ws, "N19")),
        "pet_rent": money(cell(ws, "N20")),
        "concessions": money(cell(ws, "N21")),
        "fees": money(cell(ws, "N27")),
        "total_income": money(cell(ws, "N29")),
        "contracting": money(cell(ws, "N33")),
        "landscaping": money(cell(ws, "N36")),
        "management": money(cell(ws, "N40")),
        "repairs": money(cell(ws, "N45")),
        "utilities": money(cell(ws, "N53")),
        "tax_ins": money(cell(ws, "N57")),
        "total_expense": money(cell(ws, "N59")),
        "noi": money(cell(ws, "N61")),
        "cleaning": money(cell(ws, "N42")),
        "paint": money(cell(ws, "N43")),
        "plumbing_repair": money(cell(ws, "N44")),
        "electric": money(cell(ws, "N50")),
        "water": money(cell(ws, "N51")),
        "tax": money(cell(ws, "N55")),
        "insurance": money(cell(ws, "N56")),
    }
    wb.close()
    cat_sum = round(
        (rows["contracting"] or 0)
        + (rows["landscaping"] or 0)
        + (rows["management"] or 0)
        + (rows["repairs"] or 0)
        + (rows["utilities"] or 0)
        + (rows["tax_ins"] or 0),
        2,
    )
    residual = round((rows["total_expense"] or 0) - cat_sum, 2)
    lines = [
        {
            "label": "Rental income",
            "role": "income",
            **sourced(rows["rent_income"], fname, "Sheet1!N19", "Rent Income"),
        },
        {
            "label": "Subsidized / HAP",
            "role": "income",
            **sourced(rows["total_rents"], fname, "Sheet1!N18", "Total RENTS"),
        },
        {
            "label": "Other income (fees, pet)",
            "role": "income",
            **sourced(
                round((rows["fees"] or 0) + (rows["pet_rent"] or 0), 2),
                fname,
                "Sheet1!N27+N20",
                "Total FEES + Pet Rent",
            ),
        },
        {
            "label": "Concessions",
            "role": "income",
            **sourced(rows["concessions"], fname, "Sheet1!N21", "Concessions"),
        },
        {
            "label": "Total operating income",
            "role": "total",
            **sourced(rows["total_income"], fname, "Sheet1!N29", "Total Operating Income"),
        },
        {
            "label": "Marketing",
            "role": "expense",
            **placeholder("Not in T12 export — see Budget Summary promotion line", fname, "T12"),
        },
        {
            "label": "Repairs and maintenance",
            "role": "expense",
            **sourced(rows["repairs"], fname, "Sheet1!N45", "Total REPAIRS"),
        },
        {
            "label": "Admin",
            "role": "expense",
            **placeholder("Not in T12 export — see Budget Summary administration line", fname, "T12"),
        },
        {
            "label": "Utilities",
            "role": "expense",
            **sourced(rows["utilities"], fname, "Sheet1!N53", "Total UTILITIES"),
        },
        {
            "label": "Contracting (trash)",
            "role": "expense",
            **sourced(rows["contracting"], fname, "Sheet1!N33", "Total Contracting Expenses"),
        },
        {
            "label": "Landscaping",
            "role": "expense",
            **sourced(rows["landscaping"], fname, "Sheet1!N36", "Total Landscaping"),
        },
        {
            "label": "Management fees",
            "role": "expense",
            **sourced(rows["management"], fname, "Sheet1!N40", "Total MANAGEMENT FEES"),
        },
        {
            "label": "Property taxes and insurance",
            "role": "expense",
            **sourced(rows["tax_ins"], fname, "Sheet1!N57", "Total PROPERTY TAXES AND INSURANCE"),
        },
        {
            "label": "Total operating expense",
            "role": "total",
            **sourced(rows["total_expense"], fname, "Sheet1!N59", "Total Operating Expense"),
        },
        {
            "label": "NOI",
            "role": "noi",
            **sourced(rows["noi"], fname, "Sheet1!N61", "NOI - Net Operating Income"),
        },
    ]
    return {
        "period": period,
        "entity": entity,
        "propertyLine": property_line,
        "basis": basis,
        "file": fname,
        "lines": lines,
        "categorySum": cat_sum,
        "reportedExpense": rows["total_expense"],
        "expenseGap": residual,
        "detail": rows,
    }


TYPE_LABELS = {
    "0/1.00": "Studio",
    "1/1.00": "1 Bed / 1 Bath",
    "1/1.50": "1 Bed / 1.5 Bath",
    "2/1.00": "2 Bed / 1 Bath",
    "2/2.00": "2 Bed / 2 Bath",
}


def load_rent_roll(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb["Sheet1"]
    fname = path.name
    units = []
    for row in ws.iter_rows(min_row=12, max_row=25, max_col=12, values_only=False):
        unit_id = row[0].value
        if not unit_id or "Units" in str(unit_id) or "Total" in str(unit_id):
            continue
        rec = {
            "unit": str(unit_id),
            "bdba": row[2].value,
            "status": row[4].value,
            "sf": int(row[5].value) if row[5].value else None,
            "market": money(row[6].value),
            "in_place": money(row[7].value),
        }
        units.append(rec)
    totals_row = None
    for row in ws.iter_rows(min_row=26, max_row=28, max_col=12, values_only=False):
        if row[0].value and "Units" in str(row[0].value):
            totals_row = row
            break
    wb.close()

    groups = defaultdict(list)
    for u in units:
        groups[(u["bdba"], u["sf"])].append(u)

    mix = []
    for (bdba, sf), group in sorted(groups.items(), key=lambda x: (x[0][0] or "", x[0][1] or 0)):
        occupied = [g for g in group if g["in_place"] is not None]
        in_place_avg = round(sum(g["in_place"] for g in occupied) / len(occupied), 2) if occupied else None
        market_avg = round(sum(g["market"] for g in group if g["market"] is not None) / len(group), 2)
        mix.append(
            {
                "unitType": TYPE_LABELS.get(str(bdba), str(bdba)),
                "bdba": bdba,
                "sf": sf,
                "count": len(group),
                "occupied": len(occupied),
                "inPlaceAvg": sourced(
                    in_place_avg,
                    fname,
                    f"Sheet1 col H grouped by {bdba}/{sf}",
                    f"Average occupied in-place rent, n={len(occupied)}",
                ),
                "marketAvg": sourced(
                    market_avg,
                    fname,
                    f"Sheet1 col G grouped by {bdba}/{sf}",
                    f"Average market rent, n={len(group)}",
                ),
                "inPlaceTotal": round(sum(g["in_place"] or 0 for g in group), 2),
                "marketTotal": round(sum(g["market"] or 0 for g in group), 2),
            }
        )

    n_units = len(units)
    occ = round(sum(1 for u in units if u["in_place"] is not None) / n_units, 4) if n_units else None
    total_sf = sum(u["sf"] or 0 for u in units)
    in_place_gpr = round(sum(u["in_place"] or 0 for u in units), 2)
    market_gpr = round(sum(u["market"] or 0 for u in units), 2)
    as_of = "As of: 08/01/2026"
    occ_label = None
    if totals_row:
        occ_label = totals_row[4].value
    return {
        "file": fname,
        "asOf": as_of,
        "units": units,
        "mix": mix,
        "unitCount": sourced(n_units, fname, "count of unit rows", "14 unit rows"),
        "occupancy": sourced(occ, fname, "occupied / 14", occ_label or "92.8% Occupied"),
        "totalSf": sourced(total_sf, fname, "Sheet1!F26", "9900"),
        "inPlaceGpr": sourced(in_place_gpr, fname, "Sheet1!H26", "16960"),
        "marketGpr": sourced(market_gpr, fname, "Sheet1!G26", "18660"),
    }


def load_budget(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True, keep_vba=False, read_only=True)
    ws = wb["Summary"]
    fname = path.name

    def triple(label, hist, bud, var, hist_addr, bud_addr):
        return {
            "label": label,
            "historical": sourced(money(hist), fname, f"Summary!{hist_addr}", label),
            "budget": sourced(money(bud), fname, f"Summary!{bud_addr}", label),
            "variance": money(var),
        }

    # Column layout from inspection: D historical, G budget, I variance
    lines = [
        triple("Net rental income", ws["D11"].value, ws["G11"].value, ws["I11"].value, "D11", "G11"),
        triple("Total non-rental income", ws["D12"].value, ws["G12"].value, ws["I12"].value, "D12", "G12"),
        triple("Total income", ws["D13"].value, ws["G13"].value, ws["I13"].value, "D13", "G13"),
        triple("Contract services", ws["D17"].value, ws["G17"].value, ws["I17"].value, "D17", "G17"),
        triple("Repairs and maintenance", ws["D18"].value, ws["G18"].value, ws["I18"].value, "D18", "G18"),
        triple("Make ready", ws["D19"].value, ws["G19"].value, ws["I19"].value, "D19", "G19"),
        triple("Labor", ws["D20"].value, ws["G20"].value, ws["I20"].value, "D20", "G20"),
        triple("Utilities", ws["D21"].value, ws["G21"].value, ws["I21"].value, "D21", "G21"),
        triple("Promotion / advertising", ws["D22"].value, ws["G22"].value, ws["I22"].value, "D22", "G22"),
        triple("Administration", ws["D23"].value, ws["G23"].value, ws["I23"].value, "D23", "G23"),
        triple("Total controllable expenses", ws["D25"].value, ws["G25"].value, ws["I25"].value, "D25", "G25"),
        triple("Management fees", ws["D28"].value, ws["G28"].value, ws["I28"].value, "D28", "G28"),
        triple("Property tax", ws["D29"].value, ws["G29"].value, ws["I29"].value, "D29", "G29"),
        triple("Insurance", ws["D30"].value, ws["G30"].value, ws["I30"].value, "D30", "G30"),
        triple("Total uncontrollable expenses", ws["D31"].value, ws["G31"].value, ws["I31"].value, "D31", "G31"),
        triple("Total expenses", ws["D33"].value, ws["G33"].value, ws["I33"].value, "D33", "G33"),
        triple("Net operating income", ws["D35"].value, ws["G35"].value, ws["I35"].value, "D35", "G35"),
        triple("Net income", ws["D48"].value, ws["G48"].value, ws["I48"].value, "D48", "G48"),
    ]
    assumptions = wb["Assumptions"]
    name = assumptions["B3"].value
    prep = str(assumptions["B6"].value)
    start = str(assumptions["B7"].value)
    wb.close()
    return {
        "file": fname,
        "sheet": "Summary",
        "propertyName": name,
        "prepared": prep,
        "budgetStart": start,
        "lines": lines,
    }


def asset_from_om():
    """Asset facts taken from the Newmark OM. Locators are page-level."""
    fname = "Urbana @ 39th OM (4).pdf"
    return {
        "name": sourced("Urbana @ 39th", fname, "p.1 cover", "URBANA @ 39TH"),
        "address": sourced(
            "2936 N. 39th St, Phoenix, AZ 85018",
            fname,
            "p.1 / p.20",
            "2936 N. 39TH ST | PHOENIX, AZ",
        ),
        "propertyType": sourced(
            "Multifamily — boutique garden courtyard",
            fname,
            "p.1",
            "BOUTIQUE 14 UNIT FULLY RENOVATED",
        ),
        "unitCount": sourced(14, fname, "p.20 PROPERTY INFORMATION", "14 NUMBER OF UNITS"),
        "yearBuilt": sourced(1983, fname, "p.20 / p.4", "Constructed in 1983"),
        "yearRenovated": sourced(2025, fname, "p.20", "1983/2025 YEAR BUILT / RENOVATED"),
        "nra": sourced(9900, fname, "p.20", "9,900 NET RENTABLE AREA"),
        "listPrice": sourced(3100000, fname, "p.4 / p.20", "$3,100,000 LIST PRICE"),
        "pricePerUnit": sourced(221429, fname, "p.20", "$221,429 PRICE PER UNIT"),
        "construction": sourced(
            "Block construction",
            fname,
            "p.4",
            "The property features block construction",
        ),
        "roof": sourced(
            "Pitched asphalt shingle roofs",
            fname,
            "p.4",
            "pitched asphalt shingle roofs",
        ),
        "plumbing": sourced(
            "Copper plumbing; ABS sewer lines",
            fname,
            "p.4",
            "ABS sewer lines, and copper plumbing",
        ),
        "electrical": sourced(
            "Individually metered for electricity",
            fname,
            "p.4",
            "Individually metered for electricity",
        ),
        "hvac": placeholder("HVAC type not stated in broker OM", fname, "p.4 property description"),
        "neighborhood": sourced(
            "Citrus Acres — Arcadia Lite",
            fname,
            "p.1 / p.7",
            "COVETED CITRUS ACRES-ARCADIA LITE NEIGHBORHOOD",
        ),
    }


def market_from_sources():
    om = "Urbana @ 39th OM (4).pdf"
    mb = "Phoenix_Americas_MarketBeat_Multifamily_Q2_2026.pdf"
    bullets = [
        {
            "text": "Phoenix employment 2.5 million after adding 20,500 jobs over the last year.",
            **sourced(2_500_000, mb, "p.1 ECONOMY", "employment level of 2.5 million, after adding 20,500 jobs"),
        },
        {
            "text": "Unemployment 4.0% (from 3.8%), below the 4.2% national average and third-lowest among large U.S. metros.",
            **sourced(0.04, mb, "p.1 ECONOMIC INDICATORS", "unemployment rate ticked up from 3.8% to 4.0%"),
        },
        {
            "text": "Household growth rate 1.2%. Median household income $97,400, up 3.8% year-over-year.",
            **sourced(0.012, mb, "p.1 Household Growth Rate*", "1.2% Phoenix Household Growth Rate"),
        },
        {
            "text": "Population +0.8% YoY, more than double the national average, though decelerating.",
            **sourced(0.008, mb, "p.1", "0.8% YOY increase marked a deceleration"),
        },
        {
            "text": "Metro vacancy 11.6% (−100 bps YoY) on record first-half absorption of 12,741 units.",
            **sourced(0.116, mb, "p.1 SUPPLY & DEMAND", "compress vacancy by 100 basis points (bps) YOY to 11.6%"),
        },
        {
            "text": "Asking rent $1,592 / unit, flat q/q and 2.3% below Q2 2025; concessions 8.4% of yearly effective rent.",
            **sourced(1592, mb, "p.1 PRICING", "average asking rent remaining flat at $1,592 per month"),
        },
        {
            "text": "Citrus Acres / Arcadia Lite is a renovating infill pocket off the Camelback Corridor (~30,000 employees, ~10M SF office/retail).",
            **sourced(
                30000,
                om,
                "p.7–p.9",
                "Camelback Corridor is home to more than 30,000 employees and nearly 10M SF",
            ),
        },
        {
            "text": "Neighborhood demand is supported by Global Ambassador (opened 2024), Biltmore Fashion Park, and Camelback / Papago recreation.",
            **sourced(None, om, "p.7–p.10", None),
        },
    ]
    bullets[-1]["value"] = True
    bullets[-1]["placeholder"] = None
    bullets[-1]["source"]["snippet"] = "Global Ambassador, a 5 Star and Michelin Key Hotel that opened in 2024"
    why_phoenix = [
        "Job growth still adding tens of thousands of positions a year, with unemployment under the U.S. average.",
        "Household formation (1.2%) and income growth (3.8%) are both in the source packet — no web overlay.",
        "Record H1 2026 absorption is compressing vacancy even as asking rents stabilize.",
    ]
    return {"bullets": bullets, "whyPhoenix": why_phoenix}


def photos():
    def p(src, page, role, caption, kind):
        return {
            "src": src,
            "page": page,
            "role": role,
            "kind": kind,
            "caption": caption,
            "source": {
                "file": "Urbana @ 39th OM (4).pdf",
                "locator": f"p.{page} embedded image",
                "snippet": caption,
            },
        }

    return [
        p("/om-photos/urbana_p01_01_1059x819.jpeg", 1, "hero", "Street elevation at dusk", "asset"),
        p("/om-photos/urbana_p06_14_1035x819.jpeg", 6, "courtyard", "Renovated courtyard, saguaro and gazebo", "asset"),
        p("/om-photos/urbana_p05_10_819x655.jpeg", 5, "kitchen", "Renovated kitchen — shaker / quartz / stainless", "asset"),
        p("/om-photos/urbana_p13_32_1071x818.jpeg", 13, "interior-a", "Living room after interior renovation", "asset"),
        p("/om-photos/urbana_p13_33_1023x818.jpeg", 13, "interior-b", "Bedroom — in-unit laundry, plank floors", "asset"),
        p("/om-photos/urbana_p14_34_1074x818.jpeg", 14, "interior-c", "Kitchen toward courtyard", "asset"),
        p("/om-photos/urbana_p14_35_1024x818.jpeg", 14, "bath", "Renovated bath", "asset"),
        p("/om-photos/urbana_p12_30_1336x819.jpeg", 12, "courtyard-day", "Courtyard in daylight", "asset"),
        p("/om-photos/urbana_p11_29_2115x819.jpeg", 11, "wide-asset", "Property wide", "asset"),
        p("/om-photos/urbana_p15_36_2114x819.jpeg", 15, "wide-interior", "Interior wide", "asset"),
        p("/om-photos/urbana_p23_46_2010x779.jpeg", 23, "aerial", "Aerial — Citrus Acres / Arcadia Lite", "area"),
        p("/om-photos/urbana_p24_47_1603x819.jpeg", 24, "context", "Neighborhood context", "area"),
        p("/om-photos/urbana_p07_16_673x449.jpeg", 7, "street", "Neighborhood street", "area"),
        p("/om-photos/urbana_p03_06_2115x820.jpeg", 3, "cover-wide", "Cover wide", "asset"),
        p("/om-photos/urbana_p20_45_2017x819.jpeg", 20, "overview", "Property overview spread", "asset"),
    ]


def upright_photos():
    """Broker PDF embeds some interiors sideways. Rotate known files once."""
    from PIL import Image

    jobs = [
        (ROOT / "public/om-photos/urbana_p14_35_1024x818.jpeg", Image.Transpose.ROTATE_270),
    ]
    for path, op in jobs:
        if not path.exists():
            continue
        im = Image.open(path)
        if im.size[1] > im.size[0]:
            continue
        im.transpose(op).save(path, quality=92)


def conflicts(t12, roll, budget):
    return [
        {
            "id": "occupancy",
            "severity": "info",
            "text": "August rent roll occupancy is 92.8% (1 vacant of 14). Broker OM describes a fully renovated lease-up; budget model Assumptions/Rental.Analysis treats 14 units. Deck uses the rent roll.",
        },
        {
            "id": "entity-name",
            "severity": "info",
            "text": f"T12 entity is “{t12['entity']}”; rent roll header is “Urbana At Fairmount LLC”. Same address.",
        },
        {
            "id": "unit-mix",
            "severity": "warn",
            "text": "Broker OM p.20 unit mix (patio tags, 2/2 at 900 SF) does not match the August rent roll (2/2 at 700 SF, 1/1.50 at 900 SF). Slide 2 uses the rent roll, per spec.",
        },
        {
            "id": "t12-vs-budget-hist",
            "severity": "warn",
            "text": f"July 2026 T12 NOI is ${t12['detail']['noi']:,.2f} (Aug 2025–Jul 2026). Budget Summary “Historical T12” NOI is ${budget['lines'][-2]['historical']['value']:,.2f} — a different vintage. Slides keep both, labeled.",
        },
        {
            "id": "t12-expense-gap",
            "severity": "info",
            "text": f"Sum of T12 expense category totals is ${t12['categorySum']:,.2f} vs Total Operating Expense N59 ${t12['reportedExpense']:,.2f} (gap ${t12['expenseGap']:,.2f}). Deck prints the Total Operating Expense cell as the total.",
        },
        {
            "id": "hvac",
            "severity": "info",
            "text": "HVAC system type is not stated in the broker OM. Shown as a placeholder on Slide 1.",
        },
    ]


def stable_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def build_packet(src: Path):
    t12 = load_t12(src / "Urbana @ 39th, July 2026 T12 (1).xlsx")
    roll = load_rent_roll(src / "Urbana @ 39th Rent Roll August 2026.xlsx")
    budget = load_budget(src / "Urbana @ 39th Budget 2026 V1 (1).xlsm")
    asset = asset_from_om()
    market = market_from_sources()
    pics = photos()
    conf = conflicts(t12, roll, budget)
    core = {
        "skillVersion": SKILL_VERSION,
        "deal": "Urbana @ 39th",
        "asset": asset,
        "rentRoll": roll,
        "t12": t12,
        "budget": budget,
        "market": market,
        "photos": pics,
        "conflicts": conf,
        "slides": [
            {"id": "asset", "title": "Asset summary", "sources": ["broker OM p.1, p.4, p.20", "photos p.1, p.6"]},
            {"id": "rent", "title": "Rent roll", "sources": ["Urbana @ 39th Rent Roll August 2026.xlsx"]},
            {"id": "t12", "title": "Income statement", "sources": ["Urbana @ 39th, July 2026 T12 (1).xlsx"]},
            {"id": "budget", "title": "Budget", "sources": ["Budget 2026 V1.xlsm!Summary"]},
            {"id": "market", "title": "Location and market", "sources": ["OM p.7–10", "MarketBeat Q2 2026"]},
            {"id": "photos", "title": "Photos", "sources": ["OM embedded images"]},
        ],
    }
    core["contentHash"] = stable_hash(core)
    core["generatedAt"] = datetime.now(timezone.utc).isoformat()
    return core


def write_ts(packet: dict, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(packet, indent=2)
    dest.write_text(
        f"/* Auto-generated by scripts/om/extract.py — do not edit by hand. */\n"
        f"export const deal = {body} as const;\n"
        f"export type DealPacket = typeof deal;\n"
    )


def build_pptx(packet: dict, dest: Path):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    INK = RGBColor(0x0C, 0x0E, 0x10)
    GOLD = RGBColor(0xC4, 0xA3, 0x6A)
    PAPER = RGBColor(0xF3, 0xEF, 0xE6)
    MUTED = RGBColor(0x8A, 0x84, 0x7A)
    DARK = RGBColor(0x1A, 0x1A, 0x1A)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    def fill(shape, rgb):
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb
        shape.line.fill.background()

    def tb(slide, x, y, w, h, text, size=14, color=PAPER, bold=False, font="Georgia", align=PP_ALIGN.LEFT):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bold
        run.font.name = font
        return box

    def gold_rule(slide, x, y, w):
        sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.025))
        fill(sh, GOLD)

    def rc_mark(slide, x=0.4, y=0.28, dark=False):
        tb(slide, x, y, 1.2, 0.35, "RC", size=16, color=GOLD if not dark else GOLD, bold=True, font="Georgia")

    def footer(slide, label, page, dark=True):
        c = PAPER if dark else MUTED
        tb(slide, 0.4, 7.15, 8, 0.25, f"RC Investment Properties  ·  Confidential  ·  {label}", size=10, color=c)
        tb(slide, 12.2, 7.15, 0.8, 0.25, str(page), size=10, color=c, align=PP_ALIGN.RIGHT)

    # --- Slide 1 asset
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    fill(bg, INK)
    hero = ROOT / "public" / packet["photos"][0]["src"].lstrip("/")
    if hero.exists():
        s.shapes.add_picture(str(hero), Inches(6.6), Inches(0), Inches(6.8), Inches(7.5))
    shade = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.4), 0, Inches(0.4), prs.slide_height)
    fill(shade, INK)
    rc_mark(s)
    tb(s, 0.4, 0.7, 5.8, 0.3, "OFFERING MEMORANDUM", size=11, color=GOLD, font="Arial")
    tb(s, 0.4, 1.05, 5.9, 1.1, "Urbana @ 39th", size=40, color=PAPER, bold=True)
    tb(s, 0.4, 2.05, 5.9, 0.4, "2936 N. 39th St, Phoenix, AZ 85018", size=14, color=GOLD)
    gold_rule(s, 0.4, 2.55, 1.4)
    facts = [
        ("14", "Units"),
        ("1983 / 2025", "Built / renovated"),
        ("9,900 SF", "Net rentable"),
        ("Block", "Construction"),
        ("Asphalt shingle", "Roof"),
        ("Copper / ABS", "Plumbing / sewer"),
        ("Individually metered", "Electric"),
        ("[NOT IN SOURCE]", "HVAC"),
    ]
    y = 2.8
    for val, lab in facts:
        tb(s, 0.4, y, 2.6, 0.28, lab.upper(), size=10, color=MUTED, font="Arial")
        tb(s, 2.7, y, 3.4, 0.32, val, size=14, color=PAPER)
        y += 0.42
    footer(s, "Asset summary", 1)

    # --- Slide 2 rent roll
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    fill(bg, PAPER)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.9))
    fill(bar, INK)
    tb(s, 0.4, 0.28, 8, 0.4, "Rent roll  ·  aggregated by unit type", size=22, color=PAPER, bold=True)
    tb(s, 10.2, 0.32, 2.7, 0.3, "RC", size=16, color=GOLD, align=PP_ALIGN.RIGHT)
    rows = [["Unit type", "Size (SF)", "In-place rent", "Market rent"]]
    for m in packet["rentRoll"]["mix"]:
        rows.append(
            [
                f"{m['unitType']}  ({m['count']})",
                f"{m['sf']:,}",
                f"${m['inPlaceAvg']['value']:,.0f}" if m["inPlaceAvg"]["value"] is not None else "—",
                f"${m['marketAvg']['value']:,.0f}",
            ]
        )
    rr = packet["rentRoll"]
    rows.append(
        [
            f"Total  ({rr['unitCount']['value']} units)",
            f"{rr['totalSf']['value']:,}",
            f"${rr['inPlaceGpr']['value']:,.0f} tot.",
            f"${rr['marketGpr']['value']:,.0f} tot.",
        ]
    )
    table = s.shapes.add_table(len(rows), 4, Inches(0.5), Inches(1.3), Inches(12.3), Inches(4.6)).table
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(13)
                p.font.name = "Calibri"
                p.font.color.rgb = PAPER if i == 0 else DARK
                p.font.bold = i == 0 or i == len(rows) - 1
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = INK
    tb(
        s,
        0.5,
        6.2,
        12,
        0.6,
        f"Source: {rr['file']}  ·  {rr['asOf']}  ·  Occupancy {rr['occupancy']['source']['snippet']}  ·  "
        "Unit rows are average rent per unit; total row is monthly GPR. Vacant unit 106 excluded from 1/1 in-place average.",
        size=11,
        color=MUTED,
        font="Arial",
    )
    footer(s, "Rent roll", 2, dark=False)

    def money_or_dash(v):
        if v is None:
            return "—"
        return f"${v:,.0f}"

    # --- Slide 3 T12
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    fill(bg, PAPER)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.9))
    fill(bar, INK)
    tb(s, 0.4, 0.22, 10, 0.28, "Trailing 12 income statement", size=22, color=PAPER, bold=True)
    tb(s, 0.4, 0.55, 10, 0.25, str(packet["t12"]["period"]) + "  ·  cash basis", size=11, color=GOLD)
    trows = [["Line", "Amount", "Source cell"]]
    for line in packet["t12"]["lines"]:
        trows.append(
            [
                line["label"],
                money_or_dash(line["value"]) if line["value"] is not None else line["placeholder"][:42],
                line["source"]["locator"],
            ]
        )
    table = s.shapes.add_table(len(trows), 3, Inches(0.5), Inches(1.15), Inches(12.3), Inches(5.6)).table
    table.columns[0].width = Inches(5.4)
    table.columns[1].width = Inches(3.4)
    table.columns[2].width = Inches(3.5)
    for i, row in enumerate(trows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.name = "Calibri"
                p.font.color.rgb = PAPER if i == 0 else DARK
                p.font.bold = i == 0 or (i > 0 and packet["t12"]["lines"][i - 1]["role"] in ("total", "noi"))
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = INK
    footer(s, "Income statement", 3, dark=False)

    # --- Slide 4 budget
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    fill(bg, PAPER)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.9))
    fill(bar, INK)
    tb(s, 0.4, 0.22, 12, 0.28, "Budget  ·  actuals vs full-year budget", size=22, color=PAPER, bold=True)
    tb(s, 0.4, 0.55, 12, 0.25, "Source: Budget 2026 V1.xlsm  ·  sheet Summary", size=11, color=GOLD)
    brows = [["Line", "Historical T12", "Budget", "Variance"]]
    for line in packet["budget"]["lines"]:
        brows.append(
            [
                line["label"],
                money_or_dash(line["historical"]["value"]),
                money_or_dash(line["budget"]["value"]),
                money_or_dash(line["variance"]),
            ]
        )
    table = s.shapes.add_table(len(brows), 4, Inches(0.4), Inches(1.1), Inches(12.5), Inches(5.7)).table
    for i, row in enumerate(brows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(10)
                p.font.name = "Calibri"
                p.font.color.rgb = PAPER if i == 0 else DARK
                p.font.bold = i == 0
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = INK
    footer(s, "Budget", 4, dark=False)

    # --- Slide 5 market
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    fill(bg, INK)
    aerial = ROOT / "public" / packet["photos"][10]["src"].lstrip("/")
    if aerial.exists():
        s.shapes.add_picture(str(aerial), Inches(7.2), Inches(0.9), Inches(5.8), Inches(5.9))
    rc_mark(s)
    tb(s, 0.4, 0.7, 6.5, 0.3, "LOCATION AND MARKET", size=11, color=GOLD, font="Arial")
    tb(s, 0.4, 1.0, 6.6, 0.7, "Citrus Acres · Arcadia Lite", size=28, color=PAPER, bold=True)
    y = 1.85
    for b in packet["market"]["bullets"][:6]:
        tb(s, 0.4, y, 6.6, 0.7, "·  " + b["text"], size=13, color=PAPER)
        y += 0.72
    footer(s, "Location and market", 5)

    # --- Slide 6 photos
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    fill(bg, INK)
    tb(s, 0.4, 0.2, 10, 0.4, "Asset photography", size=20, color=PAPER, bold=True)
    grid = [2, 3, 4, 5, 6, 7]
    coords = [
        (0.3, 0.75),
        (4.55, 0.75),
        (8.8, 0.75),
        (0.3, 4.05),
        (4.55, 4.05),
        (8.8, 4.05),
    ]
    for idx, (x, y) in zip(grid, coords):
        img = ROOT / "public" / packet["photos"][idx]["src"].lstrip("/")
        if img.exists():
            s.shapes.add_picture(str(img), Inches(x), Inches(y), Inches(4.1), Inches(3.05))
    footer(s, "Photos", 6)

    dest.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(dest))


def verify(packet: dict) -> list[str]:
    errors = []
    rr = packet["rentRoll"]
    if rr["unitCount"]["value"] != 14:
        errors.append(f"unit count {rr['unitCount']['value']}")
    if rr["totalSf"]["value"] != 9900:
        errors.append(f"sf {rr['totalSf']['value']}")
    if rr["inPlaceGpr"]["value"] != 16960:
        errors.append(f"in-place GPR {rr['inPlaceGpr']['value']}")
    if rr["marketGpr"]["value"] != 18660:
        errors.append(f"market GPR {rr['marketGpr']['value']}")
    noi = packet["t12"]["detail"]["noi"]
    if noi != 161864.43:
        errors.append(f"NOI {noi}")
    if packet["t12"]["detail"]["total_income"] != 193401.33:
        errors.append("income")
    if packet["t12"]["detail"]["total_expense"] != 31536.9:
        errors.append("opex")
    if packet["asset"]["unitCount"]["value"] != 14:
        errors.append("asset units")
    if packet["asset"]["yearBuilt"]["value"] != 1983:
        errors.append("year built")
    # every numeric slide field must have a locator
    def walk(o, path=""):
        if isinstance(o, dict):
            if "source" in o and "value" in o:
                if o["value"] is not None and not o["source"].get("locator"):
                    errors.append(f"missing locator at {path}")
                if o["value"] is None and not o.get("placeholder"):
                    errors.append(f"null without placeholder at {path}")
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(packet)
    return errors


def main():
    src = find_source()
    print("SOURCE", src)
    packet = build_packet(src)
    out_json = ROOT / "data" / "urbana" / "dealpacket.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(packet, indent=2, default=str))
    write_ts(packet, ROOT / "src" / "data" / "deal.ts")
    upright_photos()
    from extract_logo import extract as extract_logo

    extract_logo()
    pptx_path = ROOT / "public" / "Urbana_OM.pptx"
    # Visual PPTX is compiled from 16:9 slide rasters (scripts/om/export-pptx.mjs)
    # so it matches Midtown Grove — not an Office-default table dump.
    if not (ROOT / "public" / "om-export" / "asset.png").exists():
        build_pptx(packet, pptx_path)

    errs = verify(packet)
    packet2 = build_packet(src)
    h1, h2 = packet["contentHash"], packet2["contentHash"]
    repeatable = h1 == h2
    report = {
        "ok": not errs and repeatable,
        "errors": errs,
        "contentHash": h1,
        "repeatable": repeatable,
        "pptx": str(pptx_path),
        "json": str(out_json),
        "unitMix": [
            {
                "type": m["unitType"],
                "n": m["count"],
                "sf": m["sf"],
                "inPlace": m["inPlaceAvg"]["value"],
                "market": m["marketAvg"]["value"],
            }
            for m in packet["rentRoll"]["mix"]
        ],
        "noi": packet["t12"]["detail"]["noi"],
        "placeholders": [
            line["label"] for line in packet["t12"]["lines"] if line["value"] is None
        ]
        + (["HVAC"] if packet["asset"]["hvac"]["value"] is None else []),
    }
    (ROOT / "data" / "urbana" / "verify.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
