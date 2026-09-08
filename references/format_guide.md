# RC Investment OM format guide

Documented from *Midtown Grove — Preliminary Investment Summary*, the deck RC
Investment treats as house format. Page references are to that PDF.

## Canvas

- 1224 × 792 pt — a 17" × 11" landscape page, i.e. 15.28" × 9.9" at 72 dpi.
  Build at **13.333" × 7.5"** (16:9) so it opens cleanly in PowerPoint and
  Google Slides; the proportions of the original hold.

## Palette

Sampled from the source PDF's fill colours.

| Role | Value | Where it appears |
|---|---|---|
| Brand green | `#0A4E44` | cover band, section rules, table headers, nav bar |
| Accent green | `#006F46` | emphasis fills |
| Sage | `#A7BFBC` | table banding, hairlines |
| Ink | `#000000` | body copy |
| Paper | `#FFFFFF` | page ground, reversed type on green |

## Type

The source sets display type in **League Spartan Bold** and body copy in
**Arial**. League Spartan is rarely installed on a reviewer's machine, so the
compiler asks for it and falls back to Arial, which is what the body already
uses — the deck degrades to one family rather than to a substitute nobody chose.

| Element | Face | Size |
|---|---|---|
| Cover property name | League Spartan Bold | 40 pt |
| Cover subtitle | Arial Bold | 14 pt |
| Slide eyebrow (e.g. `Overview`) | Arial Bold | 12 pt |
| Slide header (e.g. `THE OFFERING`) | Arial Bold, all caps, letterspaced | 16 pt |
| Body / bullets | Arial | 11 pt |
| Table body | Arial | 10 pt |
| Source line | Arial Italic | 7.5 pt |

## Page furniture

- **Cover** (p. 1): full-bleed photo above a brand-green band across the bottom
  ~22% of the page. Property name reversed out of the band on the left; RC
  monogram reversed out on the right, placed with `contain` and a soft drop
  shadow — no backing disc, no independent width and height.
- **Interior pages** (p. 3 onward): a thin nav strip across the top —
  `Summary  Building  Business Plan  Location  Investment  Terms  Company` —
  with the active section in brand green and the rest in grey. Beneath it, a
  section eyebrow in sentence case, then the ALL-CAPS header, then content.
- **Content style**: bullets, not paragraphs. Label/value pairs are set as
  two-column lists (p. 7). Photographs appear on most pages.
- **Source attribution**: an italic `SOURCES:` line at the foot of any page
  carrying market data (pp. 21, 22, 27).

## Section order in the source

`Overview → Property Details → Unit Details → Floor Plans → Amenities →
Capitalization → Underwriting Assumptions → Sales Comps → Rent Comps →
Market (Houston) → Investment Terms → Portfolio → People`

## Per-slide content patterns worth copying

**Property Details** (p. 7) — two stacked label/value blocks:
`THE OFFERING` (name, address, units, year, gross SF, average unit SF,
buildings, floors, parcel, parking, location grade, occupancy) then
`CONSTRUCTION & MECHANICAL` (construction, roofs, plumbing, wiring, HVAC).

**Unit Details** (p. 8) — `KEY FACTS AND FIGURES` above a `UNIT MIX SUMMARY`
table, aggregated by unit type with a totals row. The source runs seven columns;
**the POC spec overrides this to four** — unit type, size (SF), in-place rent,
market rent.

**Underwriting Assumptions** (p. 15) — income items in the left column,
expense items in the right, each a one-line sentence. Expense order, which is
the order slide 3 follows:

`Repairs and Maintenance → Payroll → Administrative → Marketing →
Contract Services → Utilities → Real Estate Taxes → Insurance →
Management Fee → Capital Reserves → Total Operating Expenses →
Net Operating Income`

**Market** (p. 21) — an ALL-CAPS city header, then bullets grouped under
`Economy:` and `Multifamily:`, closing with an italic `SOURCES:` line.

## What the POC changes

The spec fixes the deck at 5–6 slides and reorders around the source data:
asset summary, rent roll, income statement, budget, location and market, and an
optional photo page. Returns, capitalisation, comps, terms and team pages from
the full Midtown Grove deck are out of scope.
