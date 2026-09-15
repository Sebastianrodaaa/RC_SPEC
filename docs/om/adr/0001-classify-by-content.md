# 0001. Classify by content, never by filename

**Status:** accepted (2026-09-06)
**Axis:** Classification

## Context

Deal folders arrive from brokers with no shared naming scheme. Matching `*rent*roll*.xlsx` would silently skip a file called `Property_RR_FINAL_v3.xlsx`, or mis-read a budget named like an OM.

## Decision

`ingest.py` classifies every file by MIME plus what the first pages (or sheet names) actually say. Roles are scored with weighted regexes. Folder and file names are not keys.

## Consequences

- New deals need no rename step.
- Two files can both score as `broker_om`; ingest does not yet pick a winner (open: Q-I2).
- A file that does not match a role is `pdf_other` / `workbook_other` / `unknown` and is ignored by later stages.
