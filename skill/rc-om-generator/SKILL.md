---
name: rc-om-generator
description: >
  Generate a 5–6 slide RC Investment offering memorandum from a deal folder
  of broker PDFs, T12, rent roll, budget, and photos. Use when asked to build
  an OM, investment summary, or investor deck from Drive/folder materials.
---

# RC Investment OM generator

Extract-then-compile. Never invent a number. Missing stats become `[NOT IN SOURCE]`.

## Procedure

1. Ingest the folder. Classify by MIME + first-page role, not filename.
2. Parse Excel with `scripts/om/extract.py` (openpyxl, cached values).
3. Parse PDFs for asset facts, market quotes, and embedded photos.
   Run `scripts/om/extract_logo.py` on the official seal: tight-crop, unsquash
   oval favicons to a circle, defringe grey halo, write a 1024² PNG. Cover uses
   that file with `object-fit: contain` and a drop-shadow — never a backing disc,
   never independent width/height.
4. Bind into `DealPacket`. Every field has `value | placeholder` and a locator (cell or page).
5. Aggregate rent roll by unit type (four columns only).
6. Compile `rc_om_template` via the React deck and `python-pptx`.
7. Verify: every numeric token traces to the packet; run twice; hashes must match.
8. Surface conflicts (occupancy, entity name, T12 vintage) — do not blend them.

Do not search the web for market data. Do not send T12 numbers through an LLM.
