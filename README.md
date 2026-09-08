# RC Investment OM generator

Point it at a deal folder; it returns a 6-slide offering memorandum in RC
Investment's format, plus a note of everywhere the source files disagree with
each other.

```bash
python3 scripts/om/run.py "/path/to/Deal Folder" ./out \
    --submarket Camelback --name urbana_om
```

Output in `./out`:

| File | What it is |
|---|---|
| `urbana_om.pptx` | The deck |
| `conflicts.md` | Where the sources disagree, and every `[NOT IN SOURCE]` field, with cell and page references |
| `packet.json` | The extracted data every figure on every slide came from |
| `work/` | Intermediate extracts and the photographs harvested from the broker package |

## What it needs in the folder

Nothing is matched by filename — files are classified by type and by what their
first pages actually say — so folder naming does not matter.

| Role | Recognised by | Used for |
|---|---|---|
| Broker package | "offering memorandum", exclusive advisors, a table of contents | Asset facts, specs, market narrative, photographs |
| Rent roll | a workbook whose header row has Unit / BD-BA / Sqft / Rent columns | Slide 2, occupancy |
| T12 | a single-sheet workbook headed "Income Statement" | Slide 3 |
| Budget model | a workbook with both a `Summary` and a `Budget` sheet | Slide 4 |
| Market report | "MarketBeat", vacancy and absorption tables | Slide 5 statistics |
| Template OM | RC's own prior deck | The RC seal for the cover |

Only the broker package is required. Anything missing shows on the slide as
`[NOT IN SOURCE]` — the deck still builds, and the gap is visible rather than
silently closed.

## The rule the whole thing is built around

No figure reaches a slide unless a cell or a PDF page states it.

That is enforced, not just intended. `verify.py` walks every numeric token on
every slide and fails the run if one has no ancestor in `packet.json`. A
fabricated `$7,450,000` on any slide fails the build. The only arithmetic
allowed is the deck's own presentation of source values — a mean rent within a
unit type — and each of those records the cells it averaged.

## Repeatability

The generator is a pure function of the packet. `verify.py` rebuilds the deck
into a scratch path and compares SHA-256; the `.pptx` zip is written with fixed
timestamps and a fixed member order, so two runs produce byte-identical files.
The run fails if they differ.

## When sources disagree

They will. On the Urbana trial the folder contained three different names for
the ownership entity and two trailing-12 windows whose NOI differed by $34k.
Nothing is reconciled: both readings go into `conflicts.md` with the cell that
states each one, and the decision stays with whoever is reviewing the deal.

## Tuning

`--submarket NAME` pulls that row from the market report's statistics table for
the location slide. Without it, only metro-level figures appear.

`--config layout.json` overrides which broker pages photographs are drawn from,
when the automatic pick lands on the wrong ones:

```json
{"cover_pages": [3],
 "asset_pages": [1, 2],
 "area_pages": [9, 8],
 "gallery_pages": [11, 13, 6, 14, 10]}
```

Page numbers are the broker package's PDF pages. `work/photos_index.json` lists
every harvested image with the page it came from, which is the quickest way to
find the right ones.

## Requirements

Python 3.10+, and:

```bash
pip install python-pptx openpyxl pdfplumber pymupdf pillow
```

## Files

```
SKILL.md                     the procedure, for an agent
README.md                    this file
references/format_guide.md   the Midtown Grove format, documented
scripts/om/run.py            end-to-end driver
scripts/om/ingest.py         1. classify the folder
scripts/om/extract.py        2. Excel: rent roll, T12, budget
scripts/om/extract_pdf.py    3. PDFs: asset facts, market statistics
scripts/om/extract_images.py 4. photographs
scripts/om/extract_logo.py   5. the RC seal
scripts/om/bind.py           6. the DealPacket, and conflict detection
scripts/om/compile_deck.py   7. the deck
scripts/om/verify.py         8. traceability and repeatability gates
```
