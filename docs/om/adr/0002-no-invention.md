# 0002. No invented numbers; verify is the enforcement

**Status:** accepted (2026-09-06)
**Axis:** Numbers

## Context

An offering memorandum that silently fills a gap will be read as a fact about the deal. The alternative — refusing to ship a deck with holes — hides the gap from the reviewer.

## Decision

No figure reaches a slide unless a cell or a PDF page states it. Absence renders as `[NOT IN SOURCE]`. `verify.py` walks every numeric token on every slide and fails the run if one has no ancestor in `packet.json`. A rebuild from the same packet must be byte-identical. The only arithmetic allowed is the deck’s own presentation of source values, and each of those records the cells it used.

T12 numbers are not sent through an LLM. Market data is not fetched from the web.

## Consequences

- A fabricated `$7,450,000` fails the build. The `.pptx` may already be on disk; `run.py` exits non-zero with “should not be sent”.
- Gaps stay visible to the reader instead of closing up.
- Source-line footers and locators are ignored by the tracer so `H18` does not launder the integer 18.
