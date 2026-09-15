# RC OM — System Definition

_**This file is the living source of truth for the design.** The interactive atlas is built from the same data._

_Question status: **4 open · 16 resolved**._

## One paragraph

Point the generator at a deal folder and it returns a 5–6 slide RC Investment offering memorandum, plus a note of everywhere the source files disagree. Nothing is matched by filename. No figure reaches a slide unless a cell or a PDF page states it. Missing facts render as [NOT IN SOURCE]; conflicts are listed, never blended. The deck is a pure function of the packet: a rebuild must be byte-identical.

## Decisions locked

| Axis | Decision | ADR |
|---|---|---|
| Classification | Files are classified by MIME and first-page role, never by filename. | [0001](./adr/0001-classify-by-content.md) |
| Numbers | No figure reaches a slide unless a cell or PDF page states it; verify.py is the enforcement, not a guideline. | [0002](./adr/0002-no-invention.md) |
| Rent roll | Slide 2 is four columns aggregated by unit type, not Midtown Grove’s seven. | [0003](./adr/0003-four-column-rent-roll.md) |
| Disagreement | When sources disagree, both readings are kept with locators. Nothing is averaged or chosen between. | [0004](./adr/0004-surface-conflicts.md) |

## Cost model

No model bill. The generator is a local Python 3.10 pipeline (openpyxl, pdfplumber, pymupdf, python-pptx, pillow, numpy). One deal is one CLI run; there is no token, vendor, or per-seat cost.
The cost that matters is a bad extract reaching a slide. That is why stages stop at the first failure, and why verify.py fails the run if any numeric token on a slide has no ancestor in packet.json.

## Reading order (the atlas chapters)

1. **Folder and deck** — Strip everything away and this is the system: a deal folder in, an offering memorandum out. _(adds D, O)_
2. **The runner** — One command runs every stage in order and stops at the first failure. _(adds R)_
3. **Classifying** — Files are named by what their first pages say, never by what they are called. _(adds I)_
4. **Reading sources** — Four extractors pull facts with locators. None of them guess. _(adds X)_
5. **The packet** — The binder is the brain: sourced value, or [NOT IN SOURCE]. No third state. _(adds B, P)_
6. **When sources disagree** — They will. Both readings are kept. Nothing is blended. _(adds C)_
7. **House format** — Midtown Grove, rebuilt at 16:9, slimmed to the slides the folder can fill. _(adds F, K)_
8. **The gate** — A fabricated number fails the run. A disagreement does not — it is written down. _(adds V, N)_
9. **Later** — Designed for, not switched on: the rest of the Midtown Grove deck. _(adds G)_
10. **The whole system** — Everything at once, for free exploration.

## Structures

### The run

#### D · Deal folder

**In one line.** The drop: broker PDFs, workbooks, and photos for one deal.

**What it does.** A directory on disk. Naming does not matter. The generator walks every file, asks what it is, and only then decides what to read. The broker package is the one required file; everything else missing still produces a deck, with gaps marked instead of closed.

**How it's built.** Input to `scripts/om/run.py`. Recursed by `ingest.py` (skips dotfiles). Roles recognised: broker package, template OM, market report, rent roll, T12, budget, photo. Optional flags: `--submarket`, `--name`, `--config`.

**Steps in execution.**

1. **Point** — Pass the folder path and an output directory to run.py.
2. **Optional flags** — Submarket row, deck basename, photo-page JSON.
3. **Walk** — Every non-dotfile is classified. Filename is evidence, never the key.

**Questions.**

- ~~**Q-D1** Match files by name?~~ ✓ Never. MIME plus first-page role (ingest.py, 2026-09-06).
- ~~**Q-D2** Is the broker package required?~~ ✓ Yes. run.py exits if none is found. Other roles missing still produce a deck with [NOT IN SOURCE] (2026-09-06).

#### R · Runner

**In one line.** The CLI that runs every stage in order and stops at the first failure.

**What it does.** One command. Ingest, extract, bind, compile, verify. If a stage fails, later stages do not run, so a bad extract cannot reach a slide. Work files land in `out/work/`; the public artefacts are the deck, the packet, and the conflicts note.

**How it's built.** `scripts/om/run.py` shells each stage with the same Python. Stages: ingest → excel → pdf → photos → seal → bind → compile → verify. Seal is skipped when the folder has no template OM. Verify failure still leaves the .pptx on disk, and the process exits non-zero with “should not be sent”.

**Steps in execution.**

1. **Ingest** — Classify the folder into work/manifest.json.
2. **Excel / PDF / photos / seal** — Locator-bearing extracts into work/.
3. **Bind** — DealPacket + conflict list.
4. **Compile** — python-pptx writes the deck.
5. **Verify** — Trace every figure; rebuild and compare SHA-256.

**Questions.**

- ~~**Q-R1** Does a bad extract reach a slide?~~ ✓ No. Stages stop at the first failure (run.py, 2026-09-06).

#### I · Ingest

**In one line.** Names each file by what it says, not by what it is called.

**What it does.** A broker package is the PDF that talks like an offering memorandum. A template OM is RC’s own prior deck (investment-terms language). A MarketBeat PDF is a market report. Workbooks are scored from sheet names. Two files can both look like broker packages; ingest currently scores each file independently and does not pick a winner.

**How it's built.** `scripts/om/ingest.py`. PDF rules weighted against first-four-pages text (pdfplumber); Excel rules against sheet names (openpyxl read_only). Emits `work/manifest.json` with path, MIME, role, and evidence weights. `file --mime-type` is the probe.

**Steps in execution.**

1. **MIME** — file(1) plus extension.
2. **First pages** — PDFs: first four pages of text. Workbooks: sheet names.
3. **Score** — Weighted regex roles; highest score wins for that file.
4. **Manifest** — Write work/manifest.json and a by_role index.

**Questions.**

- ~~**Q-I1** Filename conventions?~~ ✓ None. Folder naming does not matter (README, 2026-09-06).
- **Q-I2** Two files both score as broker_om — pick one, merge, or fail?

#### X · Extractors

**In one line.** Four readers: Excel, PDF facts, photographs, RC seal. None invent a number.

**What it does.** Excel is read as last-displayed values, not formula strings. PDF facts are taken by position on the page so a spliced line cannot become “14 2” units. Photographs are harvested rasters, scored as photos, and de-duplicated. The RC seal is not the embedded bitmap — it is a stencil sitting on the brand band, so the page region is rendered and the band keyed out.

**How it's built.** `extract.py` (openpyxl `data_only=True`) → `excel.json`. `extract_pdf.py` (pdfplumber, position-aware grids, `clean_prose` drops sidebar-contaminated narrative) → `pdf.json`. `extract_images.py` (pymupdf + average hash) → `work/photos/` + `photos_index.json`. `extract_logo.py` (pymupdf render + numpy key) → `rc_seal_white.png`. Every figure carries workbook/sheet/cell or PDF/page.

**Steps in execution.**

1. **Excel** — Rent roll, T12 income statement, budget Summary sheet.
2. **PDF** — Asset facts and market statistics with page locators.
3. **Photos** — Keep large colourful rasters; drop logos, charts, near-duplicates.
4. **Seal** — Render, key the band, tight-crop, un-squash, 1024² PNG.

**Questions.**

- ~~**Q-X1** Read Excel formulas?~~ ✓ No. openpyxl data_only=True — cached displayed values (extract.py, 2026-09-06).
- ~~**Q-X2** Search the web for market data?~~ ✓ No. Folder only (SKILL.md, 2026-09-06).
- ~~**Q-X3** Pull the RC seal as the embedded bitmap?~~ ✓ No. Render the page region, key out the band, write a 1024² PNG (extract_logo.py, 2026-09-06).
- **Q-X4** When the automatic photo-page pick is wrong, is --config always a human step, or should photos_index.json drive a default per deal?

### The packet

#### B · Binder

**In one line.** The brain: every field is a sourced value or [NOT IN SOURCE]. There is no third state.

**What it does.** This is where extracts become the one structure the deck is allowed to read. Absence becomes a placeholder here, not in the extractors, so that decision lives in one place. Derived figures are allowed only as the deck’s own presentation of source values — a mean rent within a unit type — and each records the cells it averaged. The binder does not pick a winner when sources disagree.

**How it's built.** `scripts/om/bind.py`. Reads `excel.json`, `pdf.json`, `photos_index.json`. Writes `work/packet.json`. Helpers: `field`, `missing`, `derived`. Property type is the one labelled inference: “Multifamily” if units exist, still carrying the units locator.

**Steps in execution.**

1. **Pass or placeholder** — Every extract is {value, source} or {placeholder: "[NOT IN SOURCE]"}.
2. **Aggregate rent roll** — Four columns by unit type; mean in-place and market rent with cell lists.
3. **Line up T12 and budget** — Midtown Grove expense order; budget Summary actual / budget / variance.
4. **Detect conflicts** — Entity name, occupancy vs vacancy factor, T12 vintage, footing, unit mix.

**Questions.**

- ~~**Q-B1** A third state besides value and placeholder?~~ ✓ None. bind.py is explicit: no field is computed from a number that is not in the sources (2026-09-06).
- ~~**Q-B2** May the binder average two disagreeing figures?~~ ✓ No. Both readings kept with locators. Mean rent is only within one unit type from one rent roll (2026-09-06).

#### P · Deal packet

**In one line.** The extracted data every figure on every slide came from.

**What it does.** If it is not in the packet, it must not appear on a slide. The compiler reads only this file. The verifier walks it for numbers. Copying it next to the deck is how a reviewer traces a figure back to a cell without rerunning anything.

**How it's built.** `work/packet.json`, copied to `<out>/packet.json`. Keys: `deal`, `asset`, `rent_roll`, `income_statement`, `budget`, `location`, `photos`, `conflicts`. Locators, hashes and filenames are metadata — verify.py does not treat the 18 in `H18` as a figure.

**Steps in execution.**

1. **Write** — bind.py dumps the packet with stable JSON.
2. **Copy** — run.py copies it beside the deck.
3. **Read** — compile_deck.py and verify.py consume it; nothing else.

**Questions.**

- ~~**Q-P1** May the compiler read excel.json directly?~~ ✓ No. The generator is a pure function of the packet (README, 2026-09-06).

#### C · Conflicts

**In one line.** Places the folder disagrees with itself, each with the cell or page that states it.

**What it does.** On the Urbana trial the folder contained three names for the ownership entity and two trailing-12 windows whose NOI differed by $34k. Nothing was reconciled. The reviewer gets both readings. Occupancy on the rent roll is not the broker’s vacancy factor — they are listed as different measurements, not as a fight to win.

**How it's built.** `detect_conflicts` in `bind.py`. Kinds: `entity_name`, `occupancy`, `t12_vintage` (0.5% NOI tolerance), `t12_footing`, `unit_mix` (slide 2 follows the rent roll). Stored on the packet; rendered later as `conflicts.md`.

**Steps in execution.**

1. **Compare** — Entity strings, NOI windows, expense footing, unit-mix codes.
2. **Keep both** — Each value carries its locator. No preference.
3. **Hand off** — The list rides on the packet to the conflicts note.

**Questions.**

- **Q-C1** Who at RC Investment is the named reviewer of conflicts.md?

### What goes out

#### F · House format

**In one line.** Midtown Grove, slimmed to the slides the folder can actually fill.

**What it does.** The house deck is 17×11 landscape. We build 16:9 so it opens in PowerPoint and Google Slides. Brand green band, League Spartan with an Arial fallback, nav strip, italic SOURCES line. Returns, comps, terms and team pages from the full source are out of scope for this POC.

**How it's built.** `references/format_guide.md`, sampled from _Midtown Grove — Preliminary Investment Summary_. Palette `#0A4E44` / `#006F46` / `#A7BFBC`. Canvas 13.333″ × 7.5″. T12 expense order is copied from p. 15. Unit mix is the one POC override: four columns, not seven.

**Steps in execution.**

1. **Canvas** — 16:9, not the original 17×11, so reviewers can open it.
2. **Type** — Ask for League Spartan Bold; fall back to Arial, which body already uses.
3. **Order** — Cover, asset, rent roll, T12, budget, location, optional photos.

**Questions.**

- ~~**Q-F1** Seven-column unit mix like Midtown Grove p. 8?~~ ✓ POC overrides to four columns: unit type, size (SF), in-place rent, market rent (format_guide.md).
- ~~**Q-F2** Build at the original 17×11 in?~~ ✓ No. 13.333×7.5 (16:9) so it opens in PowerPoint and Google Slides (format_guide.md).

#### K · Compiler

**In one line.** Renders the packet as a deck. No arithmetic beyond formatting.

**What it does.** Every figure on every slide is read straight out of the packet. A placeholder field prints as [NOT IN SOURCE] rather than disappearing, so a gap stays visible. After save, the .pptx zip is rewritten with a 1980-01-01 timestamp and sorted members so two runs hash the same.

**How it's built.** `scripts/om/compile_deck.py` (python-pptx). Slides: cover, asset, rent roll, T12, budget, market, photos if ≥4 survive. Photo pages default `{cover: [3], asset: [1,2], area: [9,8], gallery: [11,13,6,14,10]}`, overridable with `--config`. `canonicalise()` freezes the zip.

**Steps in execution.**

1. **Read packet** — v() prints the value or the placeholder.
2. **Lay out** — Cover band + seal; interiors get the nav strip and ALL-CAPS headers.
3. **Freeze** — Rewrite the zip with fixed timestamps and member order.

**Questions.**

- ~~**Q-K1** LLM-write the market narrative?~~ ✓ No. Broker prose only; contaminated sidebar captures are dropped before they reach the packet (extract_pdf.py).
- ~~**Q-K2** Photo page always present?~~ ✓ Only when enough photographs survive selection (slide_photos, min_photos=4).

#### V · Verify

**In one line.** Two gates: every slide figure traces to the packet, and a rebuild is byte-identical.

**What it does.** This is the rule made mechanical. A fabricated $7,450,000 on any slide fails the build. Page furniture and SOURCE: footers are ignored. Magnitude is compared, not typesetting — $2.5M and 2500000 are the same figure. Conflicts do not fail the gate; invented numbers do.

**How it's built.** `scripts/om/verify.py`. `trace()` tokenises slide text against `packet_numbers()`. `determinism()` rebuilds into a temp path and compares SHA-256. `write_conflicts()` emits the reviewer note. run.py treats a failed gate as “the deck was written but should not be sent”.

**Steps in execution.**

1. **Trace** — Every numeric token on every slide must have a packet ancestor.
2. **Rebuild** — Run compile_deck.py again into scratch; hashes must match.
3. **Note** — Write conflicts.md from packet.conflicts plus [NOT IN SOURCE] fields.

**Questions.**

- ~~**Q-V1** What happens if a slide shows $7,450,000 with no packet ancestor?~~ ✓ verify.py fails. The deck was written but should not be sent (run.py, 2026-09-06).

#### O · Deck

**In one line.** The 5–6 slide offering memorandum in RC Investment’s format.

**What it does.** Cover with broker photo and RC seal; then asset summary, rent roll, trailing-12, full-year budget, location and market; photos only when enough survive. A reader who sees [NOT IN SOURCE] is looking at a gap in the folder, not a generator guess.

**How it's built.** `<out>/<name>.pptx` from `compile_deck.py`. Default basename `offering_memorandum`. 13.333″ × 7.5″, brand green `#0A4E44`. The cover places the seal contained in a square with a drop shadow — never a backing disc, never independent width and height.

**Steps in execution.**

1. **Cover** — Full-bleed photo, green band, property name, seal.
2. **Five interiors** — Asset, rent roll, T12, budget, location.
3. **Optional photos** — Gallery slide if four keepers remain.

#### N · Conflicts note

**In one line.** The reviewer-facing list of disagreements and missing fields.

**What it does.** Ships beside the deck. Each conflict is a heading, a sentence, and the locators. A second section lists every [NOT IN SOURCE] field. The decision stays with whoever is reviewing the deal. Today a folder full of conflicts still passes verify, as long as no figure was invented.

**How it's built.** `<out>/conflicts.md` from `verify.write_conflicts`. Locators render as `file → sheet!cell` or `file → p. N`. Placeholder walk uses field labels (“Payroll”) rather than array indexes.

**Steps in execution.**

1. **Conflicts** — One section per kind, both readings, locators.
2. **Not in source** — Walk the packet for placeholder fields.
3. **Hand to reviewer** — Written next to the deck; not attached inside the .pptx.

**Questions.**

- **Q-N1** Do conflicts fail the build, or only accompany the deck? (Today they accompany.)

### Not yet switched on (designed for, not built)

#### G · Extra slides _(not switched on)_

**In one line.** Later: returns, comps, terms and team — the rest of Midtown Grove.

**What it does.** The source deck continues into capitalisation, underwriting assumptions, sales comps, rent comps, investment terms, portfolio and people. The POC stops where the deal folder stops being a reliable fill. These pages are designed for, not switched on.

**How it's built.** Documented as out of scope in `references/format_guide.md` § What the POC changes. No compiler functions exist for them.

**Steps in execution.**

1. **Not built** — No slide_* functions, no packet keys, no verify coverage.

**Questions.**

- **Q-G1** When do extra Midtown Grove slides switch on? → _Out of scope for the POC; ghosted until a later milestone._

## Flows (representative packets)

Payload shapes are what the design implies, not measured traffic.

### One deal

| # | From → To | Packet | Representative payload |
|---|---|---|---|
| 1 | D → R | deal folder | `{"folder":"/deals/Urbana","submarket":"Camelback"}` |
| 2 | R → I | classify | `{"skip_dotfiles":true}` |
| 3 | I → R | manifest | `{"broker_om":"Urbana OM.pdf","rent_roll":"RR.xlsx","t12":"T12.xlsx"}` |
| 4 | R → X | extract | `{"stages":["excel","pdf","photos","seal"]}` |
| 5 | X → B | extracts | `{"excel":"excel.json","pdf":"pdf.json","photos":18}` |
| 6 | B → P | packet | `{"deal":"Urbana","fields":"sourced or [NOT IN SOURCE]"}` |
| 7 | B → C | disagreements | `{"kinds":["entity_name","t12_vintage"]}` |
| 8 | C → P | both readings | `{"t12_noi":412301.22,"budget_historical_t12":378000}` |
| 9 | P → K | packet.json | `{"only_input":true}` |
| 10 | F → K | house format | `{"canvas":"13.333x7.5","rent_roll_cols":4}` |
| 11 | K → O | pptx | `{"slides":6,"name":"urbana_om.pptx"}` |
| 12 | K → V | deck | `{"path":"out/urbana_om.pptx"}` |
| 13 | V → O | PASS | `{"trace":"ok","sha256":"byte-identical"}` |
| 14 | V → N | conflicts.md | `{"conflicts":2,"not_in_source":4}` |

### Invented figure

| # | From → To | Packet | Representative payload |
|---|---|---|---|
| 1 | K → V | deck with $7,450,000 | `{"token":"$7,450,000","ancestor":null}` |
| 2 | V → O | FAIL — do not send | `{"orphans":[["slide 1","$7,450,000"]]}` |

## Questions — index

Reference by ID. ✓ resolved (with date) · otherwise open.

- ~~**Q-D1**~~ (D) ✓ Never. MIME plus first-page role (ingest.py, 2026-09-06).
- ~~**Q-D2**~~ (D) ✓ Yes. run.py exits if none is found. Other roles missing still produce a deck with [NOT IN SOURCE] (2026-09-06).
- ~~**Q-R1**~~ (R) ✓ No. Stages stop at the first failure (run.py, 2026-09-06).
- ~~**Q-I1**~~ (I) ✓ None. Folder naming does not matter (README, 2026-09-06).
- **Q-I2** (I) Two files both score as broker_om — pick one, merge, or fail?
- ~~**Q-X1**~~ (X) ✓ No. openpyxl data_only=True — cached displayed values (extract.py, 2026-09-06).
- ~~**Q-X2**~~ (X) ✓ No. Folder only (SKILL.md, 2026-09-06).
- ~~**Q-X3**~~ (X) ✓ No. Render the page region, key out the band, write a 1024² PNG (extract_logo.py, 2026-09-06).
- **Q-X4** (X) When the automatic photo-page pick is wrong, is --config always a human step, or should photos_index.json drive a default per deal?
- ~~**Q-B1**~~ (B) ✓ None. bind.py is explicit: no field is computed from a number that is not in the sources (2026-09-06).
- ~~**Q-B2**~~ (B) ✓ No. Both readings kept with locators. Mean rent is only within one unit type from one rent roll (2026-09-06).
- ~~**Q-P1**~~ (P) ✓ No. The generator is a pure function of the packet (README, 2026-09-06).
- **Q-C1** (C) Who at RC Investment is the named reviewer of conflicts.md?
- ~~**Q-F1**~~ (F) ✓ POC overrides to four columns: unit type, size (SF), in-place rent, market rent (format_guide.md).
- ~~**Q-F2**~~ (F) ✓ No. 13.333×7.5 (16:9) so it opens in PowerPoint and Google Slides (format_guide.md).
- ~~**Q-K1**~~ (K) ✓ No. Broker prose only; contaminated sidebar captures are dropped before they reach the packet (extract_pdf.py).
- ~~**Q-K2**~~ (K) ✓ Only when enough photographs survive selection (slide_photos, min_photos=4).
- ~~**Q-V1**~~ (V) ✓ verify.py fails. The deck was written but should not be sent (run.py, 2026-09-06).
- **Q-N1** (N) Do conflicts fail the build, or only accompany the deck? (Today they accompany.)
- **Q-G1** (G) When do extra Midtown Grove slides switch on?

## What the platform gives vs what we own

**Platform gives:** Python 3.10, the file(1) MIME probe, openpyxl cached values, pdfplumber page text, pymupdf embedded rasters, python-pptx, and pillow.

**We own:** Content-based classification, locator-bearing extracts, the DealPacket shape, conflict detection that never reconciles, the Midtown Grove house format (POC-slimmed), the RC seal stencil, and the two verify gates (trace + byte-identical rebuild).

## Planned filesystem

```
scripts/om/
  run.py              end-to-end driver
  ingest.py           classify the folder
  extract.py          rent roll, T12, budget
  extract_pdf.py      asset facts, market statistics
  extract_images.py   photographs from the broker package
  extract_logo.py     RC seal as a keyed stencil
  bind.py             DealPacket + conflict detection
  compile_deck.py     python-pptx, house format
  verify.py           traceability + repeatability
references/format_guide.md
<out>/
  <name>.pptx
  packet.json
  conflicts.md
  work/               manifest, extracts, harvested photos
```

## How this file is maintained

Generated from `docs/om/atlas/data.mjs` by `node docs/om/atlas/build.mjs`, which also builds the interactive atlas (`atlas.html`, published at http://127.0.0.1:8765/atlas.html). Edit the data file, rebuild, republish — never edit this file by hand.
