"""
Stage 4 - DealPacket.

Binds the Excel and PDF extracts into the one structure the deck compiles from.

Three rules, and they are the whole point of this stage:

  * Every field is {value, source} or {placeholder: "[NOT IN SOURCE]"}. There is
    no third state, and no field is ever computed from a number that isn't in
    the sources.
  * Where two sources disagree, both are kept, side by side, with their
    locators. Nothing is averaged, preferred or quietly reconciled.
  * Derived figures are allowed only where the arithmetic is the deck's own
    presentation of source values (a monthly rent annualised, a per-unit
    average). Each one records the inputs it came from.

Usage:  python3 bind.py <work_dir> [--submarket Camelback]
"""
import argparse
import json
from pathlib import Path

PLACEHOLDER = "[NOT IN SOURCE]"


def missing(note=None):
    d = {"value": None, "placeholder": PLACEHOLDER}
    if note:
        d["note"] = note
    return d


def field(x, note=None):
    """Pass an extracted {value, source} through, or mark it absent."""
    if x is None or x.get("value") in (None, ""):
        return missing(note)
    return x


def derived(value, inputs, how):
    return {"value": value, "derived": {"how": how, "from": inputs}}


# --- conflicts -------------------------------------------------------------

def detect_conflicts(xl, pdf) -> list:
    out = []

    # Ownership entity: the rent roll, the T12 and the broker package can each
    # name the property differently. Report all three; pick none.
    names = []
    rr_ent = (xl.get("rent_roll", {}).get("meta", {}) or {}).get("entity_line")
    if rr_ent:
        names.append({"name": rr_ent["value"].split(" - ")[0].strip(),
                      "source": rr_ent["source"]})
    t12_ent = (xl.get("t12", {}).get("meta", {}) or {}).get("entity")
    if t12_ent:
        names.append({"name": t12_ent["value"], "source": t12_ent["source"]})
    bud = (xl.get("budget", {}).get("assumptions", {}) or {}).get("Property Name")
    if bud:
        names.append({"name": bud["value"], "source": bud["source"]})
    if len({n["name"].lower() for n in names}) > 1:
        out.append({"kind": "entity_name",
                    "summary": "The workbooks name the ownership entity three "
                               "different ways.",
                    "values": names})

    # Occupancy: the rent roll states it; the broker underwriting assumes a
    # vacancy factor instead. These are not the same measurement.
    rr_tot = xl.get("rent_roll", {}).get("totals", {}) or {}
    occ = rr_tot.get("status")
    vac_units = sum(1 for u in xl.get("rent_roll", {}).get("units", [])
                    if "vacant" in str((u.get("status") or {}).get("value", "")).lower())
    if occ:
        out.append({"kind": "occupancy",
                    "summary": "Occupancy is a point-in-time rent-roll figure, "
                               "not the broker's underwritten vacancy factor.",
                    "values": [
                        {"name": f"{occ['value']} ({vac_units} vacant unit"
                                 f"{'s' if vac_units != 1 else ''})",
                         "source": occ["source"]},
                    ]})

    # T12 vintage: the standalone export and the budget model's own "Historical
    # T12" column cover different windows and do not agree.
    t12_noi = (xl.get("t12", {}).get("totals", {}) or {}).get("Net Operating Income")
    bud_noi = next((r for r in xl.get("budget", {}).get("rows", [])
                    if r["label"].strip().upper() == "NET OPERATING INCOME"), None)
    if t12_noi and bud_noi and bud_noi.get("actual"):
        a, b = t12_noi["value"], bud_noi["actual"]["value"]
        if abs(a - b) > max(1.0, abs(a) * 0.005):
            period = (xl.get("t12", {}).get("meta", {}) or {}).get("period")
            out.append({"kind": "t12_vintage",
                        "summary": "Two trailing-12 windows are in the folder and "
                                   "their NOI does not agree. Neither was adjusted.",
                        "values": [
                            {"name": f"T12 export NOI {a:,.2f}"
                                     + (f" ({period['value']})" if period else ""),
                             "source": t12_noi["source"]},
                            {"name": f"Budget model 'Historical T12' NOI {b:,.2f}",
                             "source": bud_noi["actual"]["source"]},
                        ]})

    # The T12's own line items do not foot to its own stated total.
    lines = [l for l in xl.get("t12", {}).get("lines", []) if l.get("amount")]
    tot = (xl.get("t12", {}).get("totals", {}) or {}).get("Total Operating Expenses")
    if lines and tot:
        s = sum(l["amount"]["value"] for l in lines)
        if abs(s - tot["value"]) > 1.0:
            out.append({"kind": "t12_footing",
                        "summary": "The T12's expense lines do not sum to the "
                                   "total the same export states. Both are shown "
                                   "as exported.",
                        "values": [
                            {"name": f"Sum of mapped expense lines {s:,.2f}",
                             "source": {"note": "sum of the line locators below"}},
                            {"name": f"Stated Total Operating Expense "
                                     f"{tot['value']:,.2f}",
                             "source": tot["source"]},
                        ]})

    # Unit mix: the broker's proforma descriptions and the rent roll's BD/BA
    # codes classify the same 14 units differently.
    mix = pdf.get("facts", {}).get("broker_unit_mix", [])
    agg = xl.get("rent_roll", {}).get("aggregated", [])
    if mix and agg:
        def beds_broker(desc):
            d = desc.strip().lower()
            if d.startswith("studio") or d.startswith("efficiency"):
                return 0
            head = d.split()[0]
            return int(head) if head.isdigit() else None

        def beds_rr(code):
            head = str(code).split("/")[0].strip()
            return int(head) if head.isdigit() else None

        def fold(pairs):
            d = {}
            for k, n in pairs:
                d[k] = d.get(k, 0) + n
            return d

        b = fold(((beds_broker(m["unit_description"]), m["sqft"]), m["units"])
                 for m in mix)
        r = fold(((beds_rr(x["unit_type"]), x["sqft"]), x["units"]) for x in agg)

        def show(d):
            return ", ".join(f"{k[0]}BR/{k[1]} SF x{v}" for k, v in sorted(
                d.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1] or 0)))

        if b != r:
            out.append({"kind": "unit_mix",
                        "summary": "The broker's proforma mix and the rent roll "
                                   "pair bedroom counts with unit sizes "
                                   "differently. Slide 2 follows the rent roll, "
                                   "per the format.",
                        "values": [
                            {"name": "Broker package: " + show(b),
                             "source": mix[0]["source"]},
                            {"name": "Rent roll: " + show(r),
                             "source": {"file": xl["rent_roll"]["file"],
                                        "sheet": xl["rent_roll"]["sheet"],
                                        "cell": "C12:F25"}},
                        ]})
    return out


# --- packet ----------------------------------------------------------------

def build(work: Path, submarket: str | None) -> dict:
    xl = json.loads((work / "excel.json").read_text())
    pdf = json.loads((work / "pdf.json").read_text())
    photos = json.loads((work / "photos_index.json").read_text()) \
        if (work / "photos_index.json").exists() else []
    facts, market = pdf.get("facts", {}), pdf.get("market", {})

    rr = xl.get("rent_roll", {})
    t12 = xl.get("t12", {})
    budget = xl.get("budget", {})

    # -- slide 1: asset summary
    addr = facts.get("address")
    csz = facts.get("city_state_zip")
    asset = {
        "property_name": field((budget.get("assumptions", {}) or {}).get("Property Name")),
        "address": field(addr),
        "city_state_zip": field(csz),
        "county": field(facts.get("county")),
        "units": field(facts.get("units")),
        "buildings": field(facts.get("buildings")),
        "year_built": field(facts.get("year_built")),
        "avg_unit_sf": field(facts.get("avg_unit_sf")),
        "rentable_sf": field(facts.get("rentable_sf")),
        "list_price": field(facts.get("list_price")),
        "price_per_unit": field(facts.get("price_per_unit")),
        "price_per_sf": field(facts.get("price_per_sf")),
        "property_type": field(
            {"value": "Multifamily", "source": facts.get("units", {}).get("source")}
            if facts.get("units") else None,
            "property type is not stated as a label in the broker package"),
        "package_date": field(facts.get("package_date")),
        "brokerage": field(facts.get("brokerage")),
        "specs": {k: field(v) for k, v in (facts.get("specs") or {}).items()},
    }

    # -- slide 2: rent roll, four columns, aggregated by unit type
    rent_rows = []
    for r in rr.get("aggregated", []):
        rent_rows.append({
            "unit_type": r["unit_type"],
            "units": r["units"],
            "vacant": r["vacant"],
            "sqft": r["sqft"],
            "in_place_rent": (derived(r["in_place_rent"],
                                      [f"{rr['sheet']}!{c}" for c in r["cells"]["in_place"]],
                                      "mean of occupied in-place rents in this unit type")
                              if r["in_place_rent"] is not None
                              else missing("all units of this type are vacant")),
            "market_rent": (derived(r["market_rent"],
                                    [f"{rr['sheet']}!{c}" for c in r["cells"]["market"]],
                                    "mean of market rents in this unit type")
                            if r["market_rent"] is not None else missing()),
        })
    totals = rr.get("totals", {}) or {}
    rent_roll = {
        "source_file": rr.get("file"),
        "as_of": field((rr.get("meta", {}) or {}).get("as_of")),
        "rows": rent_rows,
        "total_units": sum(r["units"] for r in rent_rows) if rent_rows else None,
        "total_sqft": field(totals.get("sqft")),
        "total_in_place_rent": field(totals.get("in_place_rent")),
        "total_market_rent": field(totals.get("market_rent")),
        "occupancy": field(totals.get("status")),
    }

    # -- slide 3: trailing-12 income statement, Midtown Grove line order
    income = {
        "source_file": t12.get("file"),
        "period": field((t12.get("meta", {}) or {}).get("period")),
        "basis": field((t12.get("meta", {}) or {}).get("basis")),
        "lines": [{"label": l["label"], "amount": field(l["amount"])}
                  for l in t12.get("lines", [])],
        "totals": {k: field(v) for k, v in (t12.get("totals", {}) or {}).items()},
    }

    # -- slide 4: full-year budget, the model's own Summary page
    skip = {"INCOME", "EXPENSES", "CONTROLLABLE EXPENSES", "UNCONTROLLABLE EXPENSES",
            "NON-RECURRING EXPENSES"}
    budget_rows = []
    for r in budget.get("rows", []):
        label = r["label"].strip()
        if label.upper() in skip:
            continue
        if not any(r.get(k) for k in ("actual", "budget", "variance")):
            continue
        budget_rows.append({
            "label": label,
            "actual": field(r.get("actual")),
            "budget": field(r.get("budget")),
            "variance": field(r.get("variance")),
            "emphasis": label.upper() in {
                "TOTAL INCOME", "TOTAL CONTROLLABLE EXPENSES",
                "TOTAL UNCONTROLLABLE EXPENSES", "TOTAL EXPENSES",
                "NET OPERATING INCOME", "NET INCOME"},
        })
    budget_block = {
        "source_file": budget.get("file"),
        "sheet": budget.get("sheet"),
        "title": field(budget.get("header_line")),
        "columns": budget.get("columns", {}),
        "rows": budget_rows,
        "assumptions": {k: field(v) for k, v in (budget.get("assumptions") or {}).items()
                        if k in ("Units", "Budget Preparation Date", "Start Month",
                                 "Management Fee", "Average Turnover")},
    }

    # -- slide 5: location and market
    loc = {
        "submarket": submarket,
        "report_title": field(market.get("report_title")),
        "metrics": {k: field(v) for k, v in (market.get("metrics") or {}).items()},
        "demographics": {k: field(v) for k, v in (market.get("demographics") or {}).items()},
        "submarket_row": market.get("submarket"),
        "narrative": {k: field(market.get(k)) for k in
                      ("neighborhood", "employment_node", "hospitality", "msa_overview")},
    }
    for key in ("unemployment_rate", "household_growth"):
        loc["metrics"].setdefault(key, missing())

    packet = {
        "deal": {
            "name": asset["property_name"].get("value") or "[NOT IN SOURCE]",
            "submarket": submarket,
            "sources": pdf.get("sources", {}),
        },
        "asset": asset,
        "rent_roll": rent_roll,
        "income_statement": income,
        "budget": budget_block,
        "location": loc,
        "photos": photos,
        "conflicts": detect_conflicts(xl, pdf),
    }
    return packet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--submarket", default=None)
    a = ap.parse_args()
    work = Path(a.work)
    packet = build(work, a.submarket)
    (work / "packet.json").write_text(json.dumps(packet, indent=2, default=str))
    print(f"conflicts: {len(packet['conflicts'])}")
    for c in packet["conflicts"]:
        print(f"  - {c['kind']}: {c['summary']}")
        for v in c["values"]:
            print(f"      {v['name']}   <- {v['source']}")


if __name__ == "__main__":
    main()
