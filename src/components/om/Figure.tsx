import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { Pin, Sourced } from "./types";

export function Figure({
  field,
  label,
  children,
  className,
  onPin,
}: {
  field: Sourced;
  label: string;
  children: ReactNode;
  className?: string;
  onPin: (pin: Pin) => void;
}) {
  const missing = field.value == null;
  return (
    <button
      type="button"
      onClick={() => onPin({ label, field })}
      className={cn(
        "rounded-sm text-left transition-colors duration-150",
        "hover:bg-brass/10 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brass",
        missing && "decoration-danger/60",
        className,
      )}
      title={`Source: ${field.source.file} · ${field.source.locator}`}
    >
      {children}
    </button>
  );
}

export function Missing({ text }: { text: string }) {
  return <span className="ph">[{text}]</span>;
}
