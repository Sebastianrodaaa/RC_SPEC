# 0003. Four-column rent roll (POC override)

**Status:** accepted (2026-09-06)
**Axis:** Rent roll

## Context

Midtown Grove p. 8 runs a seven-column unit-mix table. The POC is filled from a rent roll that reliably states unit type, size, in-place rent and market rent — not the extra columns of the source deck.

## Decision

Slide 2 aggregates the rent roll by unit type into four columns: unit type, size (SF), in-place rent, market rent. In-place and market rents are the mean of occupied (resp. listed) cells in that type, with those cells recorded as a derived figure. Where the broker’s proforma mix disagrees, slide 2 follows the rent roll and the disagreement is a conflict.

## Consequences

- The full seven-column table is out of scope with the extra Midtown Grove slides.
- Vacant types with no in-place rents render `[NOT IN SOURCE]` for that column rather than a made-up zero.
