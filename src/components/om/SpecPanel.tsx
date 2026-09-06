import { deal } from "@/data/deal";
import { money } from "@/lib/utils";
import { X } from "lucide-react";

const PIPELINE = [
  { n: "01", title: "Ingest", body: "Folder classified by MIME and role — no filenames hardcoded in the skill." },
  { n: "02", title: "Parse", body: "Excel via openpyxl cell grid. PDFs via layout + embedded photos. Zero LLM." },
  { n: "03", title: "Bind", body: "Asset facts and market quotes mapped to page locators. Missing fields are placeholders." },
  { n: "04", title: "Canonicalize", body: "pandas-style aggregation for unit mix. T12 totals copied from Total cells, not recomputed." },
  { n: "05", title: "Compile", body: "Branded 16:9 deck + native PPTX. Speaker-equivalent: click any figure." },
  { n: "06", title: "Verify", body: `Hash ${deal.contentHash} · two consecutive runs identical · ${deal.conflicts.length} conflicts logged.` },
];

export function SpecPanel({ onClose }: { onClose: () => void }) {
  return (
    <aside className="flex h-full flex-col overflow-hidden border-l border-brass/20 bg-ink-2">
      <div className="flex items-center justify-between border-b border-brass/15 px-5 py-4">
        <div>
          <p className="text-[11px] tracking-[0.2em] uppercase text-brass">Skill · v{deal.skillVersion}</p>
          <h2 className="font-display text-2xl text-paper">How this deck was made</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex size-11 items-center justify-center rounded-md text-paper hover:bg-ink-3"
          aria-label="Close spec"
        >
          <X className="size-5" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-5 text-sm leading-relaxed text-paper/80">
        <p>
          Extract-then-compile. Numbers never pass through a language model. Two clean runs
          produced content hash <span className="font-mono text-brass">{deal.contentHash}</span>.
        </p>

        <ol className="mt-6 space-y-4">
          {PIPELINE.map((step) => (
            <li key={step.n} className="grid grid-cols-[2.2rem_1fr] gap-3">
              <span className="font-display text-xl text-brass">{step.n}</span>
              <div>
                <p className="font-medium text-paper">{step.title}</p>
                <p className="text-stone">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <h3 className="mt-8 font-display text-xl text-paper">Source map</h3>
        <ul className="mt-3 space-y-2 text-stone">
          {deal.slides.map((s) => (
            <li key={s.id}>
              <span className="text-paper">{s.title}.</span> {s.sources.join(" · ")}
            </li>
          ))}
        </ul>

        <h3 className="mt-8 font-display text-xl text-paper">Conflicts (not silently resolved)</h3>
        <ul className="mt-3 space-y-3">
          {deal.conflicts.map((c) => (
            <li key={c.id} className="border border-brass/15 bg-ink px-3 py-2">
              <p className="text-[11px] tracking-[0.16em] uppercase text-brass">{c.severity}</p>
              <p className="mt-1 text-paper/85">{c.text}</p>
            </li>
          ))}
        </ul>

        <h3 className="mt-8 font-display text-xl text-paper">Placeholders</h3>
        <p className="mt-2 text-stone">
          HVAC type, T12 marketing, and T12 admin are not in those source files. They render as
          marked gaps rather than invented numbers. Budget slide carries promotion ({money(2500, 0)}{" "}
          historical) and administration ({money(0, 0)} historical / {money(2910, 0)} budget).
        </p>

        <h3 className="mt-8 font-display text-xl text-paper">Format guide</h3>
        <p className="mt-2 text-stone">
          Midtown Grove pattern: navy field, brass RC mark, serif display, bullets not paragraphs,
          photography throughout, unit mix aggregated, T12 then budget, then location. Six slides.
          Pixel-perfect brand fidelity is out of scope; Michael and Bradley should recognize the
          structure.
        </p>
      </div>
    </aside>
  );
}
