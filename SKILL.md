---
name: rc-om-generator
description: >
  Generate a 5-6 slide RC Investment offering memorandum from a deal folder
  of broker PDFs, T12, rent roll, budget, and photos. Use when asked to build
  an OM, investment summary, or investor deck from Drive/folder materials.
---

# RC Investment OM generator

Extract, then compile. Never invent a number. Missing stats become `[NOT IN SOURCE]`.

## The one-line version

```bash
python3 scripts/om/run.py <deal_folder> <out_dir> --submarket <Submarket> --name <basename>
```

That runs every stage below in order and stops at the first failure, so a bad
extract cannot reach a slide. It writes the deck, `conflicts.md`, and the
`packet.json` every figure came from.

## Procedure

1. **Ingest** (`scripts/om/ingest.py`). Classify by MIME plus first-page role,
   never by filename. Roles: `template_om`, `broker_om`, `market_report`,
   `rent_roll`, `t12`, `budget`, `photo`.
2. **Excel** (`scripts/om/extract.py`). openpyxl with `data_only=True` so
   cached values are read, not formula strings. Rent roll, trailing-12 income
   statement, budget Summary sheet. Every figure carries workbook, sheet, cell.
3. **PDFs** (`scripts/om/extract_pdf.py`). Asset facts and market statistics
   with page locators. Broker stat grids are read by *position*, not by line —
   line-based extraction splices "14 2 / NUMBER OF UNITS NUMBER OF BUILDINGS".
   Narrative captures that swallowed a sidebar callout are rejected, not
   published.
4. **Photos** (`scripts/om/extract_images.py`). Harvest embedded rasters from
   the broker package; reject logos, charts and page furniture on size, aspect,
   colour variance; drop near-duplicates by average hash.
5. **Seal** (`scripts/om/extract_logo.py`). The mark is a stencil composited
   against the brand band, so render the page region rather than pulling the
   bitmap: key out the band, tight-crop to ink, un-squash an oval placement,
   defringe, write a 1024² transparent PNG. The cover places that file
   contained in a square box with a drop shadow — never a backing disc, never
   independent width and height.
6. **Bind** (`scripts/om/bind.py`). Every field is `{value, source}` or
   `{placeholder: "[NOT IN SOURCE]"}` — there is no third state. Rent roll is
   aggregated by unit type into **four columns only**: unit type, size (SF),
   in-place rent, market rent. Where sources disagree, both readings are kept
   with their locators; nothing is averaged or chosen between.
7. **Compile** (`scripts/om/compile_deck.py`). python-pptx, in the format
   documented in `references/format_guide.md`. Income-statement line order
   follows Midtown Grove. No arithmetic beyond formatting.
8. **Verify** (`scripts/om/verify.py`). Two gates: every numeric token on every
   slide must trace to the packet, and a rebuild must be byte-identical. Writes
   `conflicts.md` for the reviewer.

## Slide plan

| # | Slide | Source |
|---|---|---|
| — | Cover | Broker photo, RC seal from the template OM |
| 1 | Asset summary | Broker package + rent roll occupancy |
| 2 | Rent roll (four columns, aggregated) | Rent roll workbook |
| 3 | Trailing-12 income statement | T12 workbook |
| 4 | Full-year budget | Budget model, Summary sheet |
| 5 | Location and market | Broker package first, then market report |
| 6 | Photos (only when enough survive selection) | Broker package |

## Rules

- Do not search the web for market data. Use only what is in the folder.
- Do not send T12 numbers through an LLM. They move workbook to slide by cell
  reference.
- Surface conflicts — occupancy, entity name, T12 vintage, unit mix — do not
  blend them.
- A field with no source renders as `[NOT IN SOURCE]`, never as zero and never
  as a quietly closed gap.

## Tuning a new deal

`--submarket` picks the row to pull from the market report's statistics table.
`--config` takes a JSON file overriding which broker pages photos are drawn
from:

```json
{"cover_pages": [3], "asset_pages": [1, 2],
 "area_pages": [9, 8], "gallery_pages": [11, 13, 6, 14, 10]}
```

Everything else adapts to the folder without configuration.
