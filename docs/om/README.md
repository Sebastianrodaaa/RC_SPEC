# RC OM — design set

The interactive map and the text twin are generated from one data file. Edit that file; rebuild; do not hand-edit the outputs.

| File | Role | Edit it? |
|---|---|---|
| `atlas/data.mjs` | Single source of truth: structures, flows, chapters, decisions, questions, prose | Yes |
| `atlas/template.html` + `atlas/build.mjs` | Rendering + generator | Presentation only |
| `atlas.html` | Built atlas | No (generated) |
| `SYSTEM.md` | Built text twin | No (generated) |
| `CONTEXT.md` | Glossary (domain-modeling convention) | By hand |
| `adr/` | Hard-to-reverse decisions | By hand |

```bash
node docs/om/atlas/build.mjs
```

Then open `docs/om/atlas.html` from a static server (not `file://` — fonts and scripts may not load).
