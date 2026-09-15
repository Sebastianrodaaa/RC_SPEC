# 0004. Surface conflicts; do not reconcile them

**Status:** accepted (2026-09-06)
**Axis:** Disagreement

## Context

On the Urbana trial the folder contained three different names for the ownership entity and two trailing-12 windows whose NOI differed by $34k. Picking one in code would hide the other from the person underwriting the deal.

## Decision

Where two sources disagree, both readings are kept with their locators. Nothing is averaged, preferred, or quietly reconciled. Occupancy on the rent roll is reported as a point-in-time figure, not as the broker’s vacancy factor. The reviewer-facing list is `conflicts.md`. Conflicts do not fail verify; invented numbers do.

## Consequences

- The generator never “fixes” a folder.
- Who reads `conflicts.md`, and whether a non-empty list should fail the build, is still open (Q-C1, Q-N1).
