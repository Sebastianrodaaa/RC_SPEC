"""
Stage 2 - Excel extraction.

Reads the rent roll, the trailing-12 income statement and the budget summary
with openpyxl in cached-value mode (data_only=True), so what comes out is what
Excel last displayed rather than a formula string.

Nothing here interprets or adjusts a figure. Every value carries the workbook,
sheet and cell it came from, and anything the workbook does not contain comes
back as None so the binder can mark it [NOT IN SOURCE].

Usage:  python3 extract.py <manifest.json> <out_dir>
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

PLACEHOLDER = "[NOT IN SOURCE]"


# --- helpers ---------------------------------------------------------------

def cite(book: str, sheet: str, cell: str) -> dict:
    return {"file": book, "sheet": sheet, "cell": cell}


def val(cellobj, book, sheet):
    if cellobj is None or cellobj.value is None:
        return None
    return {"value": cellobj.value, "source": cite(book, sheet, cellobj.coordinate)}


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def find_row(ws, predicate, max_row=None):
    for row in ws.iter_rows(min_row=1, max_row=max_row or ws.max_row):
        if predicate([c.value for c in row]):
            return row
    return None


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# --- rent roll -------------------------------------------------------------

RR_HEADERS = {
    "unit": ("unit",),
    "bdba": ("bd/ba", "bed/bath", "unit type", "type"),
    "sqft": ("sqft", "sq ft", "square feet", "size"),
    "market": ("market rent", "market"),
    "rent": ("rent", "in-place rent", "actual rent"),
    "status": ("status",),
}


def _header_map(values):
    out = {}
    for i, v in enumerate(values):
        n = norm(v)
        if not n:
            continue
        for key, aliases in RR_HEADERS.items():
            if key in out:
                continue
            if n in aliases:
                out[key] = i
    return out


def extract_rent_roll(path: Path) -> dict:
    book = path.name
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb[wb.sheetnames[0]]
    sheet = ws.title

    hdr = find_row(ws, lambda vs: len(_header_map(vs)) >= 4)
    if hdr is None:
        return {"error": "no rent-roll header row found", "file": book}
    cols = _header_map([c.value for c in hdr])
    hdr_row = hdr[0].row

    # Preamble lines carry the ownership entity and the as-of date.
    meta = {}
    for row in ws.iter_rows(min_row=1, max_row=hdr_row - 1, max_col=1):
        c = row[0]
        if not isinstance(c.value, str):
            continue
        t = c.value.strip()
        if norm(t).startswith("properties:"):
            meta["entity_line"] = {"value": t.split(":", 1)[1].strip(),
                                   "source": cite(book, sheet, c.coordinate)}
        elif norm(t).startswith("as of:"):
            meta["as_of"] = {"value": t.split(":", 1)[1].strip(),
                             "source": cite(book, sheet, c.coordinate)}

    units, totals = [], {}
    for row in ws.iter_rows(min_row=hdr_row + 1, max_row=ws.max_row):
        cells = {k: row[i] for k, i in cols.items() if i < len(row)}
        unit_v = cells.get("unit").value if cells.get("unit") is not None else None
        sqft_c, mkt_c, rent_c = cells.get("sqft"), cells.get("market"), cells.get("rent")

        # A totals line names a count instead of a unit ("14 Units").
        if isinstance(unit_v, str) and re.search(r"\bunits?\b", unit_v, re.I):
            totals = {
                "label": {"value": unit_v.strip(),
                          "source": cite(book, sheet, cells["unit"].coordinate)},
                "sqft": val(sqft_c, book, sheet),
                "market_rent": val(mkt_c, book, sheet),
                "in_place_rent": val(rent_c, book, sheet),
            }
            st = cells.get("status")
            if st is not None and isinstance(st.value, str):
                totals["status"] = {"value": st.value.strip(),
                                    "source": cite(book, sheet, st.coordinate)}
            continue

        if unit_v is None or not (sqft_c and num(sqft_c.value)):
            continue

        bdba = cells.get("bdba")
        status = cells.get("status")
        units.append({
            "unit": {"value": str(unit_v).strip(),
                     "source": cite(book, sheet, cells["unit"].coordinate)},
            "bdba": val(bdba, book, sheet),
            "sqft": val(sqft_c, book, sheet),
            "market_rent": val(mkt_c, book, sheet),
            "in_place_rent": val(rent_c, book, sheet),
            "status": val(status, book, sheet),
        })

    return {"file": book, "sheet": sheet, "header_row": hdr_row,
            "meta": meta, "units": units, "totals": totals}


def aggregate_rent_roll(rr: dict) -> list:
    """Roll units up to one row per unit type. Four columns, per the format."""
    buckets = {}
    for u in rr.get("units", []):
        bd = (u["bdba"] or {}).get("value")
        sf = (u["sqft"] or {}).get("value")
        key = (str(bd).strip() if bd is not None else "?", sf)
        b = buckets.setdefault(key, {"bdba": key[0], "sqft": sf, "count": 0,
                                     "in_place": [], "market": [],
                                     "cells_in_place": [], "cells_market": [],
                                     "vacant": 0})
        b["count"] += 1
        ip, mk = u["in_place_rent"], u["market_rent"]
        status = norm((u.get("status") or {}).get("value"))
        if "vacant" in status or ip is None:
            b["vacant"] += 1
        if ip is not None and num(ip["value"]):
            b["in_place"].append(ip["value"])
            b["cells_in_place"].append(ip["source"]["cell"])
        if mk is not None and num(mk["value"]):
            b["market"].append(mk["value"])
            b["cells_market"].append(mk["source"]["cell"])

    rows = []
    for (bd, sf), b in buckets.items():
        rows.append({
            "unit_type": bd,
            "sqft": sf,
            "units": b["count"],
            "vacant": b["vacant"],
            "in_place_rent": round(sum(b["in_place"]) / len(b["in_place"]))
            if b["in_place"] else None,
            "market_rent": round(sum(b["market"]) / len(b["market"]))
            if b["market"] else None,
            "cells": {"in_place": b["cells_in_place"], "market": b["cells_market"]},
        })
    # Studios, then 1-beds, then 2-beds; larger unit first inside a tie.
    def sort_key(r):
        m = re.match(r"^\s*(\d+)\s*/\s*([\d.]+)", str(r["unit_type"]))
        bd = int(m.group(1)) if m else 99
        ba = float(m.group(2)) if m else 99.0
        return (bd, ba, -(r["sqft"] or 0))
    rows.sort(key=sort_key)
    return rows


# --- trailing 12 -----------------------------------------------------------

# Midtown Grove's operating-expense order. Each entry is (display label,
# tuple of exact T12 total-row labels that may carry it). Nothing is summed
# across two source rows: one slide line maps to at most one workbook row.
T12_LINES = [
    ("Repairs & Maintenance", ("total repairs", "total repairs and maintenance",
                               "repairs and maintenance")),
    ("Payroll",               ("total payroll", "payroll", "total labor")),
    ("Administrative",        ("total administration expenses", "administrative",
                               "total administrative")),
    ("Marketing",             ("total promotion / advertising", "marketing",
                               "total marketing")),
    ("Contract Services",     ("total contracting expenses", "total contract servces",
                               "total contract services", "contract services")),
    ("Landscaping",           ("total landscaping", "landscaping")),
    ("Utilities",             ("total utilities", "utilities")),
    ("Real Estate Taxes",     ("property tax", "total property tax", "real estate taxes")),
    ("Insurance",             ("insurance", "total insurance")),
    ("Management Fee",        ("total management fees", "management fees")),
    ("Capital Reserves",      ("total replacements", "capital reserves",
                               "total capital improvements")),
]

T12_TOTALS = [
    ("Total Operating Income",   ("total operating income", "total income")),
    ("Total Operating Expenses", ("total operating expense", "total operating expenses",
                                  "total expenses")),
    ("Net Operating Income",     ("noi - net operating income", "net operating income",
                                  "noi")),
]


def _t12_total_column(ws, hdr_row):
    for c in ws[hdr_row]:
        if norm(c.value) == "total":
            return c.column
    return ws.max_column


def extract_t12(path: Path) -> dict:
    book = path.name
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb[wb.sheetnames[0]]
    sheet = ws.title

    hdr = find_row(ws, lambda vs: norm(vs[0]) in ("account name", "account", "gl account"))
    hdr_row = hdr[0].row if hdr else 1
    total_col = _t12_total_column(ws, hdr_row)

    labels = {}
    for row in ws.iter_rows(min_row=hdr_row + 1, max_row=ws.max_row, max_col=1):
        c = row[0]
        if isinstance(c.value, str) and c.value.strip():
            labels.setdefault(norm(c.value), c.row)

    meta = {}
    for row in ws.iter_rows(min_row=1, max_row=hdr_row - 1, max_col=1):
        c = row[0]
        if not isinstance(c.value, str):
            continue
        t = c.value.strip()
        low = norm(t)
        if low.startswith("period range:"):
            meta["period"] = {"value": t.split(":", 1)[1].strip(),
                              "source": cite(book, sheet, c.coordinate)}
        elif low.startswith("properties:"):
            meta["property_line"] = {"value": t.split(":", 1)[1].strip(),
                                     "source": cite(book, sheet, c.coordinate)}
        elif low.startswith("accounting basis:"):
            meta["basis"] = {"value": t.split(":", 1)[1].strip(),
                             "source": cite(book, sheet, c.coordinate)}
        elif low.endswith("llc") or low.endswith("lp"):
            meta.setdefault("entity", {"value": t,
                                       "source": cite(book, sheet, c.coordinate)})

    def pull(aliases):
        for a in aliases:
            r = labels.get(a)
            if r:
                c = ws.cell(row=r, column=total_col)
                if num(c.value):
                    return {"value": c.value, "source": cite(book, sheet, c.coordinate)}
        return None

    lines = [{"label": lab, "amount": pull(al)} for lab, al in T12_LINES]
    totals = {lab: pull(al) for lab, al in T12_TOTALS}

    return {"file": book, "sheet": sheet, "meta": meta,
            "total_column": openpyxl.utils.get_column_letter(total_col),
            "lines": lines, "totals": totals}


# --- budget ----------------------------------------------------------------

def extract_budget(path: Path) -> dict:
    """Read the model's own Summary page: label, T12 actual, budget, variance."""
    book = path.name
    wb = openpyxl.load_workbook(str(path), data_only=True)
    if "Summary" not in wb.sheetnames:
        return {"error": "no Summary sheet", "file": book}
    ws = wb["Summary"]
    sheet = ws.title

    hdr = find_row(ws, lambda vs: any(norm(v) == "budget" for v in vs)
                   and any("historical" in norm(v) for v in vs), max_row=30)
    if hdr is None:
        return {"error": "no Summary header row", "file": book}
    hdr_row = hdr[0].row

    cols = {}
    for c in hdr:
        n = norm(c.value)
        if "historical" in n:
            cols["actual"] = c.column
        elif n == "budget":
            cols["budget"] = c.column
        elif n == "variance":
            cols["variance"] = c.column

    label_col = None
    for c in hdr:
        if norm(c.value) and "unit" in norm(c.value):
            label_col = c.column
            break
    label_col = label_col or 2

    rows = []
    for r in range(hdr_row + 1, ws.max_row + 1):
        lab = ws.cell(row=r, column=label_col).value
        if not isinstance(lab, str) or not lab.strip():
            continue
        rec = {"label": lab.strip(),
               "gl": ws.cell(row=r, column=max(1, label_col - 1)).value,
               "row": r}
        for k, col in cols.items():
            rec[k] = val(ws.cell(row=r, column=col), book, sheet)
        rows.append(rec)

    header_line = None
    for r in range(1, hdr_row):
        v = ws.cell(row=r, column=1).value
        if isinstance(v, str) and v.strip():
            header_line = {"value": v.strip(), "source": cite(book, sheet, f"A{r}")}
            break

    assumptions = {}
    if "Assumptions" in wb.sheetnames:
        aws = wb["Assumptions"]
        for r in aws.iter_rows(min_row=1, max_row=aws.max_row, max_col=2):
            k, v = r[0].value, r[1].value
            if isinstance(k, str) and v is not None and not isinstance(v, str):
                assumptions[k.strip()] = {"value": v,
                                          "source": cite(book, "Assumptions",
                                                         r[1].coordinate)}
            elif isinstance(k, str) and isinstance(v, str) and v.strip():
                assumptions[k.strip()] = {"value": v.strip(),
                                          "source": cite(book, "Assumptions",
                                                         r[1].coordinate)}
    return {"file": book, "sheet": sheet, "header_line": header_line,
            "header_row": hdr_row, "columns": {k: openpyxl.utils.get_column_letter(v)
                                               for k, v in cols.items()},
            "rows": rows, "assumptions": assumptions}


# --- driver ----------------------------------------------------------------

def main():
    manifest = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    by_role = {}
    for f in manifest["files"]:
        by_role.setdefault(f["role"], []).append(Path(f["path"]))

    result = {}
    rr_files = by_role.get("rent_roll", [])
    if rr_files:
        rr = extract_rent_roll(rr_files[0])
        rr["aggregated"] = aggregate_rent_roll(rr)
        result["rent_roll"] = rr

    # The T12 export is the single-sheet workbook; the multi-sheet model is the
    # budget. Both can classify as financial, so split them on shape here.
    fin = by_role.get("t12", []) + by_role.get("budget", []) + by_role.get("workbook_other", [])
    t12_path = budget_path = None
    for p in fin:
        names = openpyxl.load_workbook(str(p), read_only=True, data_only=True).sheetnames
        if "Summary" in names and "Budget" in names:
            budget_path = budget_path or p
        elif len(names) == 1:
            t12_path = t12_path or p
    if t12_path:
        result["t12"] = extract_t12(t12_path)
    if budget_path:
        result["budget"] = extract_budget(budget_path)

    (out / "excel.json").write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({k: (list(v.keys()) if isinstance(v, dict) else v)
                      for k, v in result.items()}, indent=2))


if __name__ == "__main__":
    main()
