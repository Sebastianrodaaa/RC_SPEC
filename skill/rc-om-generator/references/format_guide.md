## Logo

Cover only. Use the official brand PNG as-is:

- Dark photography: `/brand/RC-Logo_Green_White.png`
- Light pages: do not repeat the logo

Never redraw it (no SVG recreation). Never stretch it. One size axis
(`height: 9cqh; width: auto; object-fit: contain`). No backing disc.

## Cover type

Stack from the bottom in document flow (flex column). Do not absolutely
position the title and the KPI row on top of each other. Four single-line
KPIs only. Construction details do not belong on the cover.

## Photos

Landscape interiors sit in a landscape frame (`h-[36cqh]` full content width,
`object-cover`). Never `h-full` inside a tall sidebar — CSS grid stretch will
turn a horizontal photo vertical.
