import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Download, Info } from "lucide-react";
import { deal } from "@/data/deal";
import { cn } from "@/lib/utils";
import { Provenance } from "./Provenance";
import { SpecPanel } from "./SpecPanel";
import { renderSlide, SLIDES } from "./slides";
import type { Pin } from "./types";

export function Deck({
  exportMode = false,
  slideId,
}: {
  exportMode?: boolean;
  slideId?: string;
}) {
  const initial = Math.max(
    0,
    SLIDES.findIndex((s) => s.id === slideId),
  );
  const [index, setIndex] = useState(initial === -1 ? 0 : initial);
  const [pin, setPin] = useState<Pin | null>(null);
  const [spec, setSpec] = useState(false);
  const slide = SLIDES[index] ?? SLIDES[0];

  useEffect(() => {
    if (!slideId) return;
    const i = SLIDES.findIndex((s) => s.id === slideId);
    if (i >= 0) setIndex(i);
  }, [slideId]);

  useEffect(() => {
    if (exportMode) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        setIndex((i) => Math.min(SLIDES.length - 1, i + 1));
        setPin(null);
      } else if (e.key === "ArrowLeft") {
        setIndex((i) => Math.max(0, i - 1));
        setPin(null);
      } else if (e.key >= "1" && e.key <= "6") {
        setIndex(Number(e.key) - 1);
        setPin(null);
      } else if (e.key === "Escape") {
        setPin(null);
        setSpec(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [exportMode]);

  function go(i: number) {
    setIndex(i);
    setPin(null);
  }

  if (exportMode) {
    return (
      <div className="h-screen w-screen overflow-hidden bg-ink">
        <div className="om-stage export relative">{renderSlide(slide.id, () => {})}</div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-x-hidden bg-ink text-paper">
      <header className="flex items-center justify-between gap-3 border-b border-brass/15 px-4 py-3 md:px-6">
        <div className="min-w-0">
          <p className="font-display text-lg tracking-[0.28em] text-brass md:text-xl">RC</p>
          <p className="truncate text-[11px] tracking-[0.18em] uppercase text-stone">
            {deal.deal} · sourced generation
          </p>
        </div>
        <nav className="hidden items-center gap-1 md:flex" aria-label="Slides">
          {SLIDES.map((s, i) => (
            <button
              key={s.id}
              type="button"
              onClick={() => go(i)}
              className={cn(
                "min-h-11 px-3 text-[11px] tracking-[0.16em] uppercase transition-colors",
                i === index ? "text-brass" : "text-stone hover:text-paper",
              )}
            >
              <span className="text-brass">{s.kicker}</span>
              <span className="ml-1.5">{s.title}</span>
            </button>
          ))}
        </nav>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setSpec((v) => !v)}
            className={cn(
              "flex min-h-11 items-center gap-2 px-3 text-[11px] tracking-[0.16em] uppercase",
              spec ? "text-brass" : "text-stone hover:text-paper",
            )}
          >
            <Info className="size-4" />
            Spec
          </button>
          <a
            href="/Urbana_OM.pptx"
            download
            className="flex min-h-11 items-center gap-2 px-3 text-[11px] tracking-[0.16em] uppercase text-stone hover:text-paper"
          >
            <Download className="size-4" />
            PPTX
          </a>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-1 items-start justify-center p-3 md:items-center md:p-6">
          <div className="om-stage relative w-full max-w-[1200px] overflow-hidden rounded-lg shadow-[0_24px_80px_rgba(0,0,0,0.45)] ring-1 ring-brass/20">
            {renderSlide(slide.id, setPin)}
            <button
              type="button"
              className="absolute top-1/2 left-1 z-10 hidden size-11 -translate-y-1/2 items-center justify-center text-brass/80 hover:text-brass md:flex"
              onClick={() => go(Math.max(0, index - 1))}
              aria-label="Previous slide"
            >
              <ChevronLeft />
            </button>
            <button
              type="button"
              className="absolute top-1/2 right-1 z-10 hidden size-11 -translate-y-1/2 items-center justify-center text-brass/80 hover:text-brass md:flex"
              onClick={() => go(Math.min(SLIDES.length - 1, index + 1))}
              aria-label="Next slide"
            >
              <ChevronRight />
            </button>
          </div>
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-brass/15 px-4 py-3 md:hidden">
          <button
            type="button"
            className="flex size-11 items-center justify-center"
            onClick={() => go(Math.max(0, index - 1))}
            aria-label="Previous slide"
          >
            <ChevronLeft />
          </button>
          <p className="text-[11px] tracking-[0.18em] uppercase text-brass">
            {slide.kicker} {slide.title}
          </p>
          <button
            type="button"
            className="flex size-11 items-center justify-center"
            onClick={() => go(Math.min(SLIDES.length - 1, index + 1))}
            aria-label="Next slide"
          >
            <ChevronRight />
          </button>
        </div>
        {pin ? (
          <div className="border-t border-brass/20 md:mx-auto md:mb-4 md:w-full md:max-w-[1200px] md:border md:border-brass/20">
            <Provenance pin={pin} onClose={() => setPin(null)} />
          </div>
        ) : null}
      </div>

      {spec ? (
        <div className="fixed inset-0 z-30 flex justify-end bg-ink/50">
          <div className="h-full w-full max-w-md shadow-2xl">
            <SpecPanel onClose={() => setSpec(false)} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
