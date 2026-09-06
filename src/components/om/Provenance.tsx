import { X } from "lucide-react";
import type { Pin } from "./types";

export function Provenance({ pin, onClose }: { pin: Pin; onClose: () => void }) {
  const { field, label } = pin;
  return (
    <div className="border-t border-brass/25 bg-ink-2 px-5 py-4 text-paper md:border-t-0 md:border-l">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] tracking-[0.2em] uppercase text-brass">Provenance</p>
          <h3 className="font-display text-xl">{label}</h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex size-11 items-center justify-center rounded-md hover:bg-ink-3"
          aria-label="Close provenance"
        >
          <X className="size-4" />
        </button>
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        <div>
          <dt className="text-[11px] tracking-[0.16em] uppercase text-stone">Value</dt>
          <dd className="font-display text-lg text-brass">
            {field.value == null ? field.placeholder : String(field.value)}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.16em] uppercase text-stone">File</dt>
          <dd>{field.source.file}</dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.16em] uppercase text-stone">Locator</dt>
          <dd className="font-mono text-brass">{field.source.locator}</dd>
        </div>
        {field.source.snippet ? (
          <div>
            <dt className="text-[11px] tracking-[0.16em] uppercase text-stone">Snippet</dt>
            <dd className="text-paper/80">“{field.source.snippet}”</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}
