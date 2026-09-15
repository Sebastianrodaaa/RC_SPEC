// Single source of truth for the RC OM atlas. Edit this file; never edit
// SYSTEM.md or atlas.html by hand.
// Build: node docs/om/atlas/build.mjs  → writes docs/om/SYSTEM.md and docs/om/atlas.html

export const META = {
  title: 'RC OM',
  artifactUrl: 'http://127.0.0.1:8765/atlas.html',
  sourcePath: 'docs/om/atlas/data.mjs',
  buildCmd: 'node docs/om/atlas/build.mjs',
  stats: [
    { k: 'System', v: 'RC OM · v0' },
    { k: 'Stages', v: '8' },
    { k: 'Slides', v: '5–6' },
  ],
  intro: `_**This file is the living source of truth for the design.** The interactive atlas is built from the same data._`,
  onePara: `Point the generator at a deal folder and it returns a 5–6 slide RC Investment offering memorandum, plus a note of everywhere the source files disagree. Nothing is matched by filename. No figure reaches a slide unless a cell or a PDF page states it. Missing facts render as [NOT IN SOURCE]; conflicts are listed, never blended. The deck is a pure function of the packet: a rebuild must be byte-identical.`,
  costModel: [
    'No model bill. The generator is a local Python 3.10 pipeline (openpyxl, pdfplumber, pymupdf, python-pptx, pillow, numpy). One deal is one CLI run; there is no token, vendor, or per-seat cost.',
    'The cost that matters is a bad extract reaching a slide. That is why stages stop at the first failure, and why verify.py fails the run if any numeric token on a slide has no ancestor in packet.json.',
    '',
  ],
  deepDive: '',
  platformGives: 'Python 3.10, the file(1) MIME probe, openpyxl cached values, pdfplumber page text, pymupdf embedded rasters, python-pptx, and pillow.',
  weOwn: 'Content-based classification, locator-bearing extracts, the DealPacket shape, conflict detection that never reconciles, the Midtown Grove house format (POC-slimmed), the RC seal stencil, and the two verify gates (trace + byte-identical rebuild).',
  filesystem: `scripts/om/
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
  work/               manifest, extracts, harvested photos`,
};

export const DECISIONS = [
  { axis: 'Classification', decision: 'Files are classified by MIME and first-page role, never by filename.', adr: '[0001](./adr/0001-classify-by-content.md)' },
  { axis: 'Numbers', decision: 'No figure reaches a slide unless a cell or PDF page states it; verify.py is the enforcement, not a guideline.', adr: '[0002](./adr/0002-no-invention.md)' },
  { axis: 'Rent roll', decision: 'Slide 2 is four columns aggregated by unit type, not Midtown Grove’s seven.', adr: '[0003](./adr/0003-four-column-rent-roll.md)' },
  { axis: 'Disagreement', decision: 'When sources disagree, both readings are kept with locators. Nothing is averaged or chosen between.', adr: '[0004](./adr/0004-surface-conflicts.md)' },
];

export const GROUPS = [
  { id: 'loop', title: 'The run' },
  { id: 'mem', title: 'The packet' },
  { id: 'sup', title: 'What goes out' },
  { id: 'off', title: 'Not yet switched on' },
];

export const NODES = [
  { id: 'D', code: 'D', name: 'Deal folder', short: 'DEAL FOLDER', group: 'loop',
    gx: 1.5, gy: 7.8, w: 2, d: 2, h: 44, kind: 'screen',
    one: 'The drop: broker PDFs, workbooks, and photos for one deal.',
    what: 'A directory on disk. Naming does not matter. The generator walks every file, asks what it is, and only then decides what to read. The broker package is the one required file; everything else missing still produces a deck, with gaps marked instead of closed.',
    how: 'Input to <code>scripts/om/run.py</code>. Recursed by <code>ingest.py</code> (skips dotfiles). Roles recognised: broker package, template OM, market report, rent roll, T12, budget, photo. Optional flags: <code>--submarket</code>, <code>--name</code>, <code>--config</code>.',
    steps: [
      ['Point', 'Pass the folder path and an output directory to run.py.'],
      ['Optional flags', 'Submarket row, deck basename, photo-page JSON.'],
      ['Walk', 'Every non-dotfile is classified. Filename is evidence, never the key.'],
    ],
    cond: [
      { q: 'Match files by name?', r: 'Never. MIME plus first-page role (ingest.py, 2026-09-06).' },
      { q: 'Is the broker package required?', r: 'Yes. run.py exits if none is found. Other roles missing still produce a deck with [NOT IN SOURCE] (2026-09-06).' },
    ] },

  { id: 'R', code: 'R', name: 'Runner', short: 'RUNNER', group: 'loop',
    gx: 4.2, gy: 6.4, w: 2, d: 2, h: 38, kind: 'job',
    one: 'The CLI that runs every stage in order and stops at the first failure.',
    what: 'One command. Ingest, extract, bind, compile, verify. If a stage fails, later stages do not run, so a bad extract cannot reach a slide. Work files land in <code>out/work/</code>; the public artefacts are the deck, the packet, and the conflicts note.',
    how: '<code>scripts/om/run.py</code> shells each stage with the same Python. Stages: ingest → excel → pdf → photos → seal → bind → compile → verify. Seal is skipped when the folder has no template OM. Verify failure still leaves the .pptx on disk, and the process exits non-zero with “should not be sent”.',
    steps: [
      ['Ingest', 'Classify the folder into work/manifest.json.'],
      ['Excel / PDF / photos / seal', 'Locator-bearing extracts into work/.'],
      ['Bind', 'DealPacket + conflict list.'],
      ['Compile', 'python-pptx writes the deck.'],
      ['Verify', 'Trace every figure; rebuild and compare SHA-256.'],
    ],
    cond: [
      { q: 'Does a bad extract reach a slide?', r: 'No. Stages stop at the first failure (run.py, 2026-09-06).' },
    ] },

  { id: 'I', code: 'I', name: 'Ingest', short: 'INGEST', group: 'loop',
    gx: 1.2, gy: 4.6, w: 2, d: 2, h: 36, kind: 'box',
    one: 'Names each file by what it says, not by what it is called.',
    what: 'A broker package is the PDF that talks like an offering memorandum. A template OM is RC’s own prior deck (investment-terms language). A MarketBeat PDF is a market report. Workbooks are scored from sheet names. Two files can both look like broker packages; ingest currently scores each file independently and does not pick a winner.',
    how: '<code>scripts/om/ingest.py</code>. PDF rules weighted against first-four-pages text (pdfplumber); Excel rules against sheet names (openpyxl read_only). Emits <code>work/manifest.json</code> with path, MIME, role, and evidence weights. <code>file --mime-type</code> is the probe.',
    steps: [
      ['MIME', 'file(1) plus extension.'],
      ['First pages', 'PDFs: first four pages of text. Workbooks: sheet names.'],
      ['Score', 'Weighted regex roles; highest score wins for that file.'],
      ['Manifest', 'Write work/manifest.json and a by_role index.'],
    ],
    cond: [
      { q: 'Filename conventions?', r: 'None. Folder naming does not matter (README, 2026-09-06).' },
      { q: 'Two files both score as broker_om — pick one, merge, or fail?' },
    ] },

  { id: 'X', code: 'X', name: 'Extractors', short: 'EXTRACTORS', group: 'loop',
    gx: 4.0, gy: 3.0, w: 3, d: 2, h: 30, kind: 'cards',
    one: 'Four readers: Excel, PDF facts, photographs, RC seal. None invent a number.',
    what: 'Excel is read as last-displayed values, not formula strings. PDF facts are taken by position on the page so a spliced line cannot become “14 2” units. Photographs are harvested rasters, scored as photos, and de-duplicated. The RC seal is not the embedded bitmap — it is a stencil sitting on the brand band, so the page region is rendered and the band keyed out.',
    how: '<code>extract.py</code> (openpyxl <code>data_only=True</code>) → <code>excel.json</code>. <code>extract_pdf.py</code> (pdfplumber, position-aware grids, <code>clean_prose</code> drops sidebar-contaminated narrative) → <code>pdf.json</code>. <code>extract_images.py</code> (pymupdf + average hash) → <code>work/photos/</code> + <code>photos_index.json</code>. <code>extract_logo.py</code> (pymupdf render + numpy key) → <code>rc_seal_white.png</code>. Every figure carries workbook/sheet/cell or PDF/page.',
    steps: [
      ['Excel', 'Rent roll, T12 income statement, budget Summary sheet.'],
      ['PDF', 'Asset facts and market statistics with page locators.'],
      ['Photos', 'Keep large colourful rasters; drop logos, charts, near-duplicates.'],
      ['Seal', 'Render, key the band, tight-crop, un-squash, 1024² PNG.'],
    ],
    cond: [
      { q: 'Read Excel formulas?', r: 'No. openpyxl data_only=True — cached displayed values (extract.py, 2026-09-06).' },
      { q: 'Search the web for market data?', r: 'No. Folder only (SKILL.md, 2026-09-06).' },
      { q: 'Pull the RC seal as the embedded bitmap?', r: 'No. Render the page region, key out the band, write a 1024² PNG (extract_logo.py, 2026-09-06).' },
      { q: 'When the automatic photo-page pick is wrong, is --config always a human step, or should photos_index.json drive a default per deal?' },
    ] },

  { id: 'B', code: 'B', name: 'Binder', short: 'BINDER', group: 'mem',
    gx: 8.0, gy: 2.2, w: 3, d: 3, h: 64, kind: 'tall',
    one: 'The brain: every field is a sourced value or [NOT IN SOURCE]. There is no third state.',
    what: 'This is where extracts become the one structure the deck is allowed to read. Absence becomes a placeholder here, not in the extractors, so that decision lives in one place. Derived figures are allowed only as the deck’s own presentation of source values — a mean rent within a unit type — and each records the cells it averaged. The binder does not pick a winner when sources disagree.',
    how: '<code>scripts/om/bind.py</code>. Reads <code>excel.json</code>, <code>pdf.json</code>, <code>photos_index.json</code>. Writes <code>work/packet.json</code>. Helpers: <code>field</code>, <code>missing</code>, <code>derived</code>. Property type is the one labelled inference: “Multifamily” if units exist, still carrying the units locator.',
    steps: [
      ['Pass or placeholder', 'Every extract is {value, source} or {placeholder: "[NOT IN SOURCE]"}.'],
      ['Aggregate rent roll', 'Four columns by unit type; mean in-place and market rent with cell lists.'],
      ['Line up T12 and budget', 'Midtown Grove expense order; budget Summary actual / budget / variance.'],
      ['Detect conflicts', 'Entity name, occupancy vs vacancy factor, T12 vintage, footing, unit mix.'],
    ],
    cond: [
      { q: 'A third state besides value and placeholder?', r: 'None. bind.py is explicit: no field is computed from a number that is not in the sources (2026-09-06).' },
      { q: 'May the binder average two disagreeing figures?', r: 'No. Both readings kept with locators. Mean rent is only within one unit type from one rent roll (2026-09-06).' },
    ] },

  { id: 'P', code: 'P', name: 'Deal packet', short: 'PACKET', group: 'mem',
    gx: 11.5, gy: 2.4, w: 3, d: 3, h: 28, kind: 'store',
    one: 'The extracted data every figure on every slide came from.',
    what: 'If it is not in the packet, it must not appear on a slide. The compiler reads only this file. The verifier walks it for numbers. Copying it next to the deck is how a reviewer traces a figure back to a cell without rerunning anything.',
    how: '<code>work/packet.json</code>, copied to <code>&lt;out&gt;/packet.json</code>. Keys: <code>deal</code>, <code>asset</code>, <code>rent_roll</code>, <code>income_statement</code>, <code>budget</code>, <code>location</code>, <code>photos</code>, <code>conflicts</code>. Locators, hashes and filenames are metadata — verify.py does not treat the 18 in <code>H18</code> as a figure.',
    steps: [
      ['Write', 'bind.py dumps the packet with stable JSON.'],
      ['Copy', 'run.py copies it beside the deck.'],
      ['Read', 'compile_deck.py and verify.py consume it; nothing else.'],
    ],
    cond: [
      { q: 'May the compiler read excel.json directly?', r: 'No. The generator is a pure function of the packet (README, 2026-09-06).' },
    ] },

  { id: 'C', code: 'C', name: 'Conflicts', short: 'CONFLICTS', group: 'mem',
    gx: 8.0, gy: 6.8, w: 3, d: 3, h: 24, kind: 'store',
    one: 'Places the folder disagrees with itself, each with the cell or page that states it.',
    what: 'On the Urbana trial the folder contained three names for the ownership entity and two trailing-12 windows whose NOI differed by $34k. Nothing was reconciled. The reviewer gets both readings. Occupancy on the rent roll is not the broker’s vacancy factor — they are listed as different measurements, not as a fight to win.',
    how: '<code>detect_conflicts</code> in <code>bind.py</code>. Kinds: <code>entity_name</code>, <code>occupancy</code>, <code>t12_vintage</code> (0.5% NOI tolerance), <code>t12_footing</code>, <code>unit_mix</code> (slide 2 follows the rent roll). Stored on the packet; rendered later as <code>conflicts.md</code>.',
    steps: [
      ['Compare', 'Entity strings, NOI windows, expense footing, unit-mix codes.'],
      ['Keep both', 'Each value carries its locator. No preference.'],
      ['Hand off', 'The list rides on the packet to the conflicts note.'],
    ],
    cond: [
      { q: 'Who at RC Investment is the named reviewer of conflicts.md?' },
    ] },

  { id: 'F', code: 'F', name: 'House format', short: 'FORMAT', group: 'sup',
    gx: 7.8, gy: -0.6, w: 4, d: 2, h: 20, kind: 'slab',
    one: 'Midtown Grove, slimmed to the slides the folder can actually fill.',
    what: 'The house deck is 17×11 landscape. We build 16:9 so it opens in PowerPoint and Google Slides. Brand green band, League Spartan with an Arial fallback, nav strip, italic SOURCES line. Returns, comps, terms and team pages from the full source are out of scope for this POC.',
    how: '<code>references/format_guide.md</code>, sampled from <em>Midtown Grove — Preliminary Investment Summary</em>. Palette <code>#0A4E44</code> / <code>#006F46</code> / <code>#A7BFBC</code>. Canvas 13.333″ × 7.5″. T12 expense order is copied from p. 15. Unit mix is the one POC override: four columns, not seven.',
    steps: [
      ['Canvas', '16:9, not the original 17×11, so reviewers can open it.'],
      ['Type', 'Ask for League Spartan Bold; fall back to Arial, which body already uses.'],
      ['Order', 'Cover, asset, rent roll, T12, budget, location, optional photos.'],
    ],
    cond: [
      { q: 'Seven-column unit mix like Midtown Grove p. 8?', r: 'POC overrides to four columns: unit type, size (SF), in-place rent, market rent (format_guide.md).' },
      { q: 'Build at the original 17×11 in?', r: 'No. 13.333×7.5 (16:9) so it opens in PowerPoint and Google Slides (format_guide.md).' },
    ] },

  { id: 'K', code: 'K', name: 'Compiler', short: 'COMPILER', group: 'sup',
    gx: 15.2, gy: 2.5, w: 2, d: 2, h: 40, kind: 'box',
    one: 'Renders the packet as a deck. No arithmetic beyond formatting.',
    what: 'Every figure on every slide is read straight out of the packet. A placeholder field prints as [NOT IN SOURCE] rather than disappearing, so a gap stays visible. After save, the .pptx zip is rewritten with a 1980-01-01 timestamp and sorted members so two runs hash the same.',
    how: '<code>scripts/om/compile_deck.py</code> (python-pptx). Slides: cover, asset, rent roll, T12, budget, market, photos if ≥4 survive. Photo pages default <code>{cover: [3], asset: [1,2], area: [9,8], gallery: [11,13,6,14,10]}</code>, overridable with <code>--config</code>. <code>canonicalise()</code> freezes the zip.',
    steps: [
      ['Read packet', 'v() prints the value or the placeholder.'],
      ['Lay out', 'Cover band + seal; interiors get the nav strip and ALL-CAPS headers.'],
      ['Freeze', 'Rewrite the zip with fixed timestamps and member order.'],
    ],
    cond: [
      { q: 'LLM-write the market narrative?', r: 'No. Broker prose only; contaminated sidebar captures are dropped before they reach the packet (extract_pdf.py).' },
      { q: 'Photo page always present?', r: 'Only when enough photographs survive selection (slide_photos, min_photos=4).' },
    ] },

  { id: 'V', code: 'V', name: 'Verify', short: 'VERIFY', group: 'sup',
    gx: 15.2, gy: 5.5, w: 2, d: 2, h: 48, kind: 'gate',
    one: 'Two gates: every slide figure traces to the packet, and a rebuild is byte-identical.',
    what: 'This is the rule made mechanical. A fabricated $7,450,000 on any slide fails the build. Page furniture and SOURCE: footers are ignored. Magnitude is compared, not typesetting — $2.5M and 2500000 are the same figure. Conflicts do not fail the gate; invented numbers do.',
    how: '<code>scripts/om/verify.py</code>. <code>trace()</code> tokenises slide text against <code>packet_numbers()</code>. <code>determinism()</code> rebuilds into a temp path and compares SHA-256. <code>write_conflicts()</code> emits the reviewer note. run.py treats a failed gate as “the deck was written but should not be sent”.',
    steps: [
      ['Trace', 'Every numeric token on every slide must have a packet ancestor.'],
      ['Rebuild', 'Run compile_deck.py again into scratch; hashes must match.'],
      ['Note', 'Write conflicts.md from packet.conflicts plus [NOT IN SOURCE] fields.'],
    ],
    cond: [
      { q: 'What happens if a slide shows $7,450,000 with no packet ancestor?', r: 'verify.py fails. The deck was written but should not be sent (run.py, 2026-09-06).' },
    ] },

  { id: 'O', code: 'O', name: 'Deck', short: 'DECK', group: 'sup',
    gx: 15.0, gy: 8.3, w: 2, d: 2, h: 44, kind: 'screen',
    one: 'The 5–6 slide offering memorandum in RC Investment’s format.',
    what: 'Cover with broker photo and RC seal; then asset summary, rent roll, trailing-12, full-year budget, location and market; photos only when enough survive. A reader who sees [NOT IN SOURCE] is looking at a gap in the folder, not a generator guess.',
    how: '<code>&lt;out&gt;/&lt;name&gt;.pptx</code> from <code>compile_deck.py</code>. Default basename <code>offering_memorandum</code>. 13.333″ × 7.5″, brand green <code>#0A4E44</code>. The cover places the seal contained in a square with a drop shadow — never a backing disc, never independent width and height.',
    steps: [
      ['Cover', 'Full-bleed photo, green band, property name, seal.'],
      ['Five interiors', 'Asset, rent roll, T12, budget, location.'],
      ['Optional photos', 'Gallery slide if four keepers remain.'],
    ],
    cond: [] },

  { id: 'N', code: 'N', name: 'Conflicts note', short: 'NOTE', group: 'sup',
    gx: 11.5, gy: 10.6, w: 2, d: 2, h: 36, kind: 'screen',
    one: 'The reviewer-facing list of disagreements and missing fields.',
    what: 'Ships beside the deck. Each conflict is a heading, a sentence, and the locators. A second section lists every [NOT IN SOURCE] field. The decision stays with whoever is reviewing the deal. Today a folder full of conflicts still passes verify, as long as no figure was invented.',
    how: '<code>&lt;out&gt;/conflicts.md</code> from <code>verify.write_conflicts</code>. Locators render as <code>file → sheet!cell</code> or <code>file → p. N</code>. Placeholder walk uses field labels (“Payroll”) rather than array indexes.',
    steps: [
      ['Conflicts', 'One section per kind, both readings, locators.'],
      ['Not in source', 'Walk the packet for placeholder fields.'],
      ['Hand to reviewer', 'Written next to the deck; not attached inside the .pptx.'],
    ],
    cond: [
      { q: 'Do conflicts fail the build, or only accompany the deck? (Today they accompany.)' },
    ] },

  { id: 'G', code: 'G', name: 'Extra slides', short: 'EXTRA SLIDES', group: 'off', ghost: true,
    gx: 18.5, gy: 0.2, w: 2, d: 2, h: 34, kind: 'box',
    one: 'Later: returns, comps, terms and team — the rest of Midtown Grove.',
    what: 'The source deck continues into capitalisation, underwriting assumptions, sales comps, rent comps, investment terms, portfolio and people. The POC stops where the deal folder stops being a reliable fill. These pages are designed for, not switched on.',
    how: 'Documented as out of scope in <code>references/format_guide.md</code> § What the POC changes. No compiler functions exist for them.',
    steps: [
      ['Not built', 'No slide_* functions, no packet keys, no verify coverage.'],
    ],
    cond: [
      { q: 'When do extra Midtown Grove slides switch on?', to: 'Out of scope for the POC; ghosted until a later milestone.' },
    ] },
];

export const FLOWS = [
  { id: 'run', name: 'One deal', hops: [
    ['D', 'R', 'deal folder', { folder: '/deals/Urbana', submarket: 'Camelback' }, 'yx'],
    ['R', 'I', 'classify', { skip_dotfiles: true }, 'xy'],
    ['I', 'R', 'manifest', { broker_om: 'Urbana OM.pdf', rent_roll: 'RR.xlsx', t12: 'T12.xlsx' }, 'yx'],
    ['R', 'X', 'extract', { stages: ['excel', 'pdf', 'photos', 'seal'] }, 'xy'],
    ['X', 'B', 'extracts', { excel: 'excel.json', pdf: 'pdf.json', photos: 18 }, 'yx'],
    ['B', 'P', 'packet', { deal: 'Urbana', fields: 'sourced or [NOT IN SOURCE]' }, 'xy'],
    ['B', 'C', 'disagreements', { kinds: ['entity_name', 't12_vintage'] }, 'yx'],
    ['C', 'P', 'both readings', { t12_noi: 412301.22, budget_historical_t12: 378000 }, 'xy'],
    ['P', 'K', 'packet.json', { only_input: true }, 'yx'],
    ['F', 'K', 'house format', { canvas: '13.333x7.5', rent_roll_cols: 4 }, 'xy'],
    ['K', 'O', 'pptx', { slides: 6, name: 'urbana_om.pptx' }, 'yx'],
    ['K', 'V', 'deck', { path: 'out/urbana_om.pptx' }, 'xy'],
    ['V', 'O', 'PASS', { trace: 'ok', sha256: 'byte-identical' }, 'yx'],
    ['V', 'N', 'conflicts.md', { conflicts: 2, not_in_source: 4 }, 'xy'],
  ] },
  { id: 'fail', name: 'Invented figure', hops: [
    ['K', 'V', 'deck with $7,450,000', { token: '$7,450,000', ancestor: null }, 'xy'],
    ['V', 'O', 'FAIL — do not send', { orphans: [['slide 1', '$7,450,000']] }, 'yx'],
  ] },
];

export const CH = [
  { id: 'you', title: 'Folder and deck', reveal: ['D', 'O'],
    lede: `Strip everything away and this is the system: a deal folder in, an offering memorandum out.`,
    story: `<p>Point it at a folder. It returns a 5–6 slide RC Investment deck. Naming the files does not matter. <mark>The broker package is required</mark>; anything else missing still builds, with the gap visible on the slide.</p>`,
    flow: [
      ['D', 'O', 'run', { folder: '/deals/Urbana', out: './out', name: 'urbana_om' }],
    ] },
  { id: 'run', title: 'The runner', reveal: ['R'],
    lede: `One command runs every stage in order and stops at the first failure.`,
    story: `<p>The runner is not a service and not a chat. It is <code>python3 scripts/om/run.py</code>. <mark>A bad extract never reaches a slide</mark> because later stages do not run.</p>`,
    flow: [
      ['D', 'R', 'deal folder', { folder: '/deals/Urbana' }],
      ['R', 'O', 'deck', { name: 'urbana_om.pptx' }],
    ] },
  { id: 'class', title: 'Classifying', reveal: ['I'],
    lede: `Files are named by what their first pages say, never by what they are called.`,
    story: `<p>An “offering memorandum” with exclusive advisors is the broker package. RC’s own prior deck is the template, used for the seal. A workbook whose header is Unit / BD-BA / Sqft / Rent is the rent roll. <mark>Folder naming does not matter.</mark></p>`,
    flow: [
      ['D', 'R', 'deal folder', { folder: '/deals/Urbana' }],
      ['R', 'I', 'classify', { by: 'MIME + first pages' }],
      ['I', 'R', 'manifest', { broker_om: 'Urbana OM.pdf' }],
    ] },
  { id: 'read', title: 'Reading sources', reveal: ['X'],
    lede: `Four extractors pull facts with locators. None of them guess.`,
    story: `<p>Excel is last-displayed values, not formulas. PDF grids are read by position, because line-based extraction splices “14 2 / NUMBER OF UNITS NUMBER OF BUILDINGS”. Photographs are scored and de-duplicated. The seal is a stencil on the brand band, so the page is rendered and the band keyed out. <mark>Every figure carries a cell or a page.</mark></p>`,
    flow: [
      ['R', 'X', 'extract', { stages: ['excel', 'pdf', 'photos', 'seal'] }],
      ['X', 'R', 'work files', { excel: 'excel.json', pdf: 'pdf.json' }],
    ] },
  { id: 'pack', title: 'The packet', reveal: ['B', 'P'],
    lede: `The binder is the brain: sourced value, or [NOT IN SOURCE]. No third state.`,
    story: `<p>Extracts become one structure the compiler is allowed to read. Absence is marked here, in one place. A mean rent within a unit type is allowed because it is the deck’s own presentation of source cells, and it records them. <mark>If it is not in the packet, it must not appear on a slide.</mark></p>`,
    flow: [
      ['X', 'B', 'extracts', { excel: 'excel.json', pdf: 'pdf.json' }],
      ['B', 'P', 'packet', { rule: '{value, source} | {placeholder}' }],
    ] },
  { id: 'disagree', title: 'When sources disagree', reveal: ['C'],
    lede: `They will. Both readings are kept. Nothing is blended.`,
    story: `<p>Urbana’s folder named the ownership entity three ways and held two trailing-12 windows whose NOI differed by $34k. Occupancy on the rent roll is not the broker’s vacancy factor. <mark>The decision stays with whoever is reviewing the deal.</mark></p>`,
    flow: [
      ['B', 'C', 'disagreements', { entity_name: 3, t12_vintage: '$34k NOI' }],
      ['C', 'P', 'both readings', { reconcile: false }],
    ] },
  { id: 'format', title: 'House format', reveal: ['F', 'K'],
    lede: `Midtown Grove, rebuilt at 16:9, slimmed to the slides the folder can fill.`,
    story: `<p>Brand green, nav strip, italic SOURCES line. The compiler prints the packet — it does not calculate a cap rate. Placeholders print as <code>[NOT IN SOURCE]</code> instead of vanishing. After save, the zip is frozen so two runs hash the same. <mark>No arithmetic beyond formatting.</mark></p>`,
    flow: [
      ['P', 'K', 'packet.json', { only_input: true }],
      ['F', 'K', 'house format', { canvas: '16:9', cols: 4 }],
      ['K', 'O', 'pptx', { slides: 6 }],
    ] },
  { id: 'gate', title: 'The gate', reveal: ['V', 'N'],
    lede: `A fabricated number fails the run. A disagreement does not — it is written down.`,
    story: `<p>verify.py walks every numeric token on every slide and fails if one has no ancestor in the packet. Then it rebuilds the deck and compares SHA-256. Beside the deck it writes the conflicts note. <mark>The deck may exist on disk and still must not be sent.</mark></p>`,
    flow: [
      ['K', 'V', 'deck', { path: 'out/urbana_om.pptx' }],
      ['V', 'O', 'PASS', { trace: 'ok', sha256: 'byte-identical' }],
      ['V', 'N', 'conflicts.md', { conflicts: 2, not_in_source: 4 }],
    ] },
  { id: 'later', title: 'Later', reveal: ['G'],
    lede: `Designed for, not switched on: the rest of the Midtown Grove deck.`,
    story: `<p>Returns, comps, terms, team. The source has them. This POC does not, because the deal folder is not a reliable fill for them yet. <mark>The map keeps the ghost so the omission is a decision, not a forgetting.</mark></p>`,
    flow: [
      ['G', 'K', 'not built', { slides: ['returns', 'comps', 'terms', 'team'] }],
    ] },
  { id: 'all', title: 'The whole system', reveal: [],
    lede: `Everything at once, for free exploration.`,
    story: `<p>Choose which flow runs (bottom left): one deal, or an invented figure that fails the gate. Hover anything; click to pin; → goes inside. The <mark>Open questions</mark> tab lists every question by ID.</p>`,
    flow: null },
];

export const HOW_HTML = `<div class="eyebrow">RC OM · v0</div><h1 class="t">How it's built</h1><div class="sub">a folder-in, deck-out pipeline with two gates</div>
<p>Python 3.10 CLI. No LLM on numbers. No web search. The packet is the only thing the compiler reads.</p>
<h3 class="sec">Filesystem</h3>
<pre>scripts/om/
  run.py ingest.py extract.py extract_pdf.py
  extract_images.py extract_logo.py
  bind.py compile_deck.py verify.py
references/format_guide.md
&lt;out&gt;/  &lt;name&gt;.pptx  packet.json  conflicts.md  work/</pre>
<h3 class="sec">The rule</h3>
<p>No figure reaches a slide unless a cell or a PDF page states it. <code>verify.py</code> walks every numeric token and fails the run if one has no ancestor in <code>packet.json</code>. A rebuild from the same packet must be byte-identical.</p>
<h3 class="sec">Locked</h3>
<p>Classify by content. Never invent a number. Four-column rent roll. Surface conflicts — do not reconcile them.</p>`;
