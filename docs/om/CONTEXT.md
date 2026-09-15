# RC OM — glossary

Nouns the atlas and the code share. One line each.

- **Deal folder** — A directory of broker PDFs, workbooks and photos for one asset; naming does not matter.
- **Broker package** — The offering-memorandum PDF (exclusive advisors, table of contents); the one required file.
- **Template OM** — RC’s own prior deck; used only to take the seal from the cover band.
- **Rent roll** — A workbook whose header row has Unit / BD-BA / Sqft / Rent; feeds slide 2 and occupancy.
- **T12** — Trailing-twelve-month income statement; a single-sheet workbook headed “Income Statement”.
- **Budget model** — A workbook with both a Summary and a Budget sheet; feeds slide 4.
- **Market report** — A MarketBeat-style PDF of vacancy, rent and absorption; feeds slide 5 when `--submarket` is set.
- **Manifest** — `work/manifest.json`: each file’s path, MIME, role and evidence weights.
- **Deal packet** — `packet.json`: the only structure the compiler and verifier read.
- **Locator** — Workbook/sheet/cell, or PDF/page, attached to every extracted figure.
- **Placeholder** — `{placeholder: "[NOT IN SOURCE]"}`; the only legal form of absence.
- **Derived figure** — A presentation of source values (mean rent within a unit type) that records the cells it used.
- **Conflict** — Two sourced readings that disagree; both kept; never averaged.
- **House format** — Midtown Grove, rebuilt at 16:9 and slimmed to 5–6 slides.
- **RC seal** — The monogram, rendered from the template cover as a keyed stencil, never the raw embedded bitmap.
- **Verify** — Two gates: every slide figure traces to the packet, and a rebuild is byte-identical.
- **Conflicts note** — `conflicts.md`, reviewer-facing; disagreements plus every `[NOT IN SOURCE]` field.
- **Submarket** — Named row pulled from the market report’s statistics table (`--submarket`).
- **Extra slides** — Returns, comps, terms, team: in the source deck, not in this POC.
