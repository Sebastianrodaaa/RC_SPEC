import { cn } from "@/lib/utils";

/** Official RC lockup. Exact brand PNG — never redrawn, never stretched. */
export function RcCoverLogo({ className }: { className?: string }) {
  return (
    <img
      src="/brand/RC-Logo_Green_White.png"
      alt="RC Investment Properties"
      width={1500}
      height={600}
      className={cn("om-cover-logo", className)}
    />
  );
}

const NAV = [
  "Location",
  "Building",
  "Unit Details",
  "Financials",
  "Market",
  "Photos",
] as const;

export function GoldNav({ active }: { active: (typeof NAV)[number] }) {
  return (
    <nav className="hidden flex-wrap items-center gap-x-[0.85cqw] text-[clamp(0.55rem,0.95cqw,0.78rem)] tracking-[0.14em] uppercase text-brass md:flex">
      {NAV.map((item, i) => (
        <span key={item} className="flex items-center gap-[0.85cqw]">
          {i > 0 ? <span className="text-brass/40">|</span> : null}
          <span className={item === active ? "text-brass" : "text-brass/55"}>{item}</span>
        </span>
      ))}
    </nav>
  );
}

export function SlideFooter({
  n,
  light = false,
}: {
  n: number;
  light?: boolean;
}) {
  return (
    <div
      className={
        "flex shrink-0 items-end justify-between px-[2.2cqw] py-[1.05cqh] " +
        (light ? "text-stone" : "text-paper/70")
      }
    >
      <p className="text-[0.78cqw] tracking-[0.18em] uppercase">Confidential</p>
      <p className="font-display text-[1.05cqw] text-brass">{n}</p>
    </div>
  );
}