# RC Investment OM skill

Point this at a deal folder. It produces a 5–6 slide investor OM in RC’s Midtown Grove pattern.

## Trial deal

Urbana @ 39th, Phoenix AZ. Sources in the shared packet:

| Role | File |
| --- | --- |
| Format guide | Midtown Grove Preliminary Investment Summary |
| Broker OM | Urbana @ 39th OM |
| T12 | Urbana @ 39th, July 2026 T12.xlsx |
| Rent roll | Urbana @ 39th Rent Roll August 2026.xlsx |
| Budget | Urbana @ 39th Budget 2026 V1.xlsm |
| Market | Phoenix Americas MarketBeat Multifamily Q2 2026 |

## Run

```bash
python3 scripts/om/extract.py
```

Writes:

- `src/data/deal.ts` — canonical packet
- `public/Urbana_OM.pptx` — native deck
- `data/urbana/verify.json` — hash, placeholders, unit mix

Open the app to present the deck. Click any figure for file + cell/page.

## Rules

- No fabricated market stats.
- Marketing / admin / HVAC render as placeholders when absent from that source.
- Consecutive runs must share `contentHash`.
