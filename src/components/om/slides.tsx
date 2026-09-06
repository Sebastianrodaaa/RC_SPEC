import type { ReactNode } from "react";
import { deal } from "@/data/deal";
import { money } from "@/lib/utils";
import { Figure, Missing } from "./Figure";
import { GoldNav, RcCoverLogo, SlideFooter } from "./chrome";
import type { Pin, Sourced } from "./types";

const a = deal.asset;
const rr = deal.rentRoll;
const photos = deal.photos;

export const SLIDES = [
  { id: "asset", kicker: "01", title: "Cover" },
  { id: "rent", kicker: "02", title: "Unit Details" },
  { id: "t12", kicker: "03", title: "T12" },
  { id: "budget", kicker: "04", title: "Budget" },
  { id: "market", kicker: "05", title: "Market" },
  { id: "photos", kicker: "06", title: "Photos" },
] as const;

export function renderSlide(id: string, onPin: (p: Pin) => void) {
  switch (id) {
    case "asset":
      return <SlideAsset onPin={onPin} />;
    case "rent":
      return <SlideRent onPin={onPin} />;
    case "t12":
      return <SlideT12 onPin={onPin} />;
    case "budget":
      return <SlideBudget onPin={onPin} />;
    case "market":
      return <SlideMarket onPin={onPin} />;
    case "photos":
      return <SlidePhotos onPin={onPin} />;
    default:
      return <SlideAsset onPin={onPin} />;
  }
}

export function SlideAsset({ onPin }: { onPin: (p: Pin) => void }) {
  const hero = photos.find((p) => p.role === "hero") ?? photos[0];
  const kpis: { label: string; field: Sourced; display: ReactNode }[] = [
    { label: "Units", field: a.unitCount, display: String(a.unitCount.value) },
    {
      label: "Built / renovated",
      field: a.yearBuilt,
      display: `${a.yearBuilt.value} / ${a.yearRenovated.value}`,
    },
    { label: "Net rentable", field: a.nra, display: `${a.nra.value?.toLocaleString()} SF` },
    {
      label: "Price / unit",
      field: a.pricePerUnit,
      display: money(a.pricePerUnit.value, 0),
    },
  ];
  return (
    <article className="relative flex h-full flex-col overflow-hidden bg-ink text-paper">
      <img
        src={hero.src}
        alt={hero.caption}
        className="absolute inset-0 h-full w-full object-cover"
        crossOrigin="anonymous"
      />
      <div className="absolute inset-0 bg-linear-to-r from-ink/70 via-ink/20 to-transparent" />
      <div className="absolute inset-0 bg-linear-to-t from-ink from-[18%] via-ink/65 via-[42%] to-ink/10" />
      <RcCoverLogo />
      <div className="relative z-2 mt-auto px-[2.6cqw]">
        <p className="text-[clamp(0.65rem,1.05cqw,0.85rem)] tracking-[0.28em] uppercase text-brass">
          Offering memorandum
        </p>
        <h1 className="om-display mt-[0.5cqh] text-[clamp(2.4rem,6.2cqw,5.4rem)] text-brass">
          {a.name.value}
        </h1>
        <div className="om-rule mt-[1.1cqh] w-[7cqw]" />
        <Figure field={a.address} label="Address" onPin={onPin} className="mt-[1cqh]">
          <p className="text-[clamp(0.75rem,1.2cqw,1.05rem)] tracking-[0.16em] uppercase text-paper">
            {a.address.value}
          </p>
        </Figure>
        <p className="mt-[0.6cqh] max-w-[52cqw] text-[clamp(0.75rem,1.1cqw,0.95rem)] text-paper/80">
          Boutique 14-unit courtyard community, fully renovated, in Citrus Acres / Arcadia Lite.
        </p>
        <div className="mt-[2.2cqh] flex flex-wrap gap-x-[2.4cqw] gap-y-[0.8cqh] pb-[0.4cqh]">
          {kpis.map((s) => (
            <Figure key={s.label} field={s.field} label={s.label} onPin={onPin} className="min-w-0">
              <p className="truncate font-display text-[clamp(0.95rem,1.7cqw,1.4rem)] text-brass">
                {s.display}
              </p>
              <p className="truncate text-[0.68cqw] tracking-[0.16em] uppercase text-paper/70">
                {s.label}
              </p>
            </Figure>
          ))}
        </div>
      </div>
      <div className="relative z-2">
        <SlideFooter n={1} />
      </div>
    </article>
  );
}

export function SlideRent({ onPin }: { onPin: (p: Pin) => void }) {
  return (
    <article className="relative flex h-full flex-col overflow-hidden bg-paper text-ink">
      <header className="shrink-0 px-[2.2cqw] pt-[1.6cqh]">
        <GoldNav active="Unit Details" />
      </header>
      <div className="min-h-0 flex-1 px-[2.2cqw] pt-[1.2cqh]">
        <h2 className="font-display text-[clamp(1.6rem,3.1cqw,2.5rem)] italic text-brass">
          Unit Details
        </h2>
        <table className="om-table mg mt-[1.2cqh]">
          <thead>
            <tr>
              <th>Unit description</th>
              <th className="num">Square feet</th>
              <th className="num">In-place rent</th>
              <th className="num">Market rent</th>
            </tr>
          </thead>
          <tbody>
            {rr.mix.map((row) => (
              <tr key={row.unitType}>
                <td>
                  {row.unitType}
                  <span className="ml-[0.5cqw] text-stone">({row.count})</span>
                </td>
                <td className="num">{row.sf.toLocaleString()}</td>
                <td className="num">
                  <Figure field={row.inPlaceAvg} label={`${row.unitType} in-place`} onPin={onPin}>
                    {money(row.inPlaceAvg.value, 0)}
                  </Figure>
                </td>
                <td className="num">
                  <Figure field={row.marketAvg} label={`${row.unitType} market`} onPin={onPin}>
                    {money(row.marketAvg.value, 0)}
                  </Figure>
                </td>
              </tr>
            ))}
            <tr className="total">
              <td>Total ({rr.unitCount.value} units)</td>
              <td className="num">
                <Figure field={rr.totalSf} label="Total SF" onPin={onPin}>
                  {rr.totalSf.value.toLocaleString()}
                </Figure>
              </td>
              <td className="num">
                <Figure field={rr.inPlaceGpr} label="In-place GPR" onPin={onPin}>
                  {money(rr.inPlaceGpr.value, 0)}
                </Figure>
              </td>
              <td className="num">
                <Figure field={rr.marketGpr} label="Market GPR" onPin={onPin}>
                  {money(rr.marketGpr.value, 0)}
                </Figure>
              </td>
            </tr>
          </tbody>
        </table>
        <p className="mt-[0.9cqh] text-[0.9cqw] text-stone">
          <Figure field={rr.occupancy} label="Occupancy" onPin={onPin}>
            {rr.occupancy.source.snippet}
          </Figure>
          {" · "}
          {rr.asOf} · in-place is occupied average; total row is monthly GPR
        </p>
      </div>
      <SlideFooter n={2} light />
    </article>
  );
}

function t12Display(line: (typeof deal.t12.lines)[number]) {
  if (line.value == null) return <Missing text="NOT IN T12" />;
  return money(line.value, 0);
}

export function SlideT12({ onPin }: { onPin: (p: Pin) => void }) {
  const lines = deal.t12.lines;
  const courtyard = photos.find((p) => p.role === "courtyard") ?? photos[1];
  const noi = lines.find((l) => l.role === "noi");
  const income = lines.find((l) => l.label === "Total operating income");
  const margin =
    noi?.value && income?.value ? `${((noi.value / income.value) * 100).toFixed(1)}%` : "—";
  return (
    <article className="relative flex h-full flex-col overflow-hidden bg-paper text-ink">
      <header className="shrink-0 px-[2.2cqw] pt-[1.6cqh]">
        <GoldNav active="Financials" />
      </header>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-[1.8cqw] px-[2.2cqw] pt-[1.2cqh] md:grid-cols-[1.15fr_0.85fr]">
        <div className="min-h-0">
          <p className="text-[0.8cqw] tracking-[0.22em] uppercase text-brass">
            Trailing 12 · {String(deal.t12.period).replace("Period Range: ", "")}
          </p>
          <h2 className="font-display text-[clamp(1.6rem,3.1cqw,2.5rem)] italic text-brass">T12</h2>
          <table className="om-table mg dense mt-[1cqh]">
            <tbody>
              {lines.map((line) => (
                <tr key={line.label} className={line.role === "total" || line.role === "noi" ? "total" : ""}>
                  <td>{line.label}</td>
                  <td className="num">
                    <Figure field={line} label={line.label} onPin={onPin}>
                      {t12Display(line)}
                    </Figure>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex min-h-0 flex-col gap-[1.2cqh]">
          <div className="relative min-h-0 flex-1 overflow-hidden">
            <img
              src={courtyard.src}
              alt={courtyard.caption}
              className="h-full w-full object-cover object-center"
              crossOrigin="anonymous"
            />
          </div>
          <div className="shrink-0 bg-paper-2 px-[1.4cqw] py-[1.2cqh]">
            <p className="font-display text-[clamp(1.4rem,2.6cqw,2.1rem)] text-brass">
              <Figure field={noi!} label="NOI" onPin={onPin}>
                {money(noi?.value, 0)}
              </Figure>
            </p>
            <p className="text-[0.72cqw] tracking-[0.16em] uppercase text-stone">NOI · {margin} margin</p>
            <p className="mt-[0.6cqh] text-[0.78cqw] text-stone">
              {deal.t12.basis} · {deal.t12.entity}
            </p>
          </div>
        </div>
      </div>
      <SlideFooter n={3} light />
    </article>
  );
}

export function SlideBudget({ onPin }: { onPin: (p: Pin) => void }) {
  const lines = deal.budget.lines;
  const pick = (label: string) => lines.find((l) => l.label === label);
  const callouts = [
    { label: "Income", line: pick("Total income") },
    { label: "Controllable", line: pick("Total controllable expenses") },
    { label: "Uncontrollable", line: pick("Total uncontrollable expenses") },
    { label: "NOI", line: pick("Net operating income") },
  ];
  const vintage = deal.conflicts.find((c) => c.id === "t12-vs-budget-hist");
  return (
    <article className="relative flex h-full flex-col overflow-hidden bg-paper text-ink">
      <header className="shrink-0 px-[2.2cqw] pt-[1.6cqh]">
        <GoldNav active="Financials" />
      </header>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-[1.8cqw] px-[2.2cqw] pt-[1.2cqh] md:grid-cols-[1.25fr_0.75fr]">
        <div>
          <p className="text-[0.8cqw] tracking-[0.22em] uppercase text-brass">
            {deal.budget.sheet} · prepared {String(deal.budget.prepared).slice(0, 10)}
          </p>
          <h2 className="font-display text-[clamp(1.6rem,3.1cqw,2.5rem)] italic text-brass">
            2026 budget vs historical
          </h2>
          <table className="om-table mg dense mt-[1cqh]">
            <thead>
              <tr>
                <th></th>
                <th className="num">Historical</th>
                <th className="num">Budget</th>
                <th className="num">Δ</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => {
                const total = line.label.startsWith("Total") || line.label.startsWith("Net");
                return (
                  <tr key={line.label} className={total ? "total" : ""}>
                    <td>{line.label}</td>
                    <td className="num">
                      <Figure field={line.historical} label={`${line.label} hist`} onPin={onPin}>
                        {money(line.historical.value, 0)}
                      </Figure>
                    </td>
                    <td className="num">
                      <Figure field={line.budget} label={`${line.label} budget`} onPin={onPin}>
                        {money(line.budget.value, 0)}
                      </Figure>
                    </td>
                    <td className="num">{money(line.variance, 0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="flex flex-col gap-[1cqh]">
          {callouts.map((c) => (
            <div key={c.label} className="bg-paper-2 px-[1.3cqw] py-[1cqh]">
              <p className="text-[0.68cqw] tracking-[0.16em] uppercase text-stone">{c.label}</p>
              <p className="font-display text-[clamp(1.2rem,2.2cqw,1.8rem)] text-brass">
                {c.line ? money(c.line.variance, 0) : "—"}
              </p>
            </div>
          ))}
          {vintage ? <p className="text-[0.78cqw] leading-snug text-stone">{vintage.text}</p> : null}
        </div>
      </div>
      <SlideFooter n={4} light />
    </article>
  );
}

export function SlideMarket({ onPin }: { onPin: (p: Pin) => void }) {
  const aerial = photos.find((p) => p.role === "aerial") ?? photos[0];
  const kpis = [
    { label: "Vacancy", value: "11.6%", field: deal.market.bullets[4] },
    { label: "Asking rent", value: "$1,592", field: deal.market.bullets[5] },
    { label: "Household income", value: "$97,400", field: deal.market.bullets[2] },
    { label: "Jobs added", value: "+20,500", field: deal.market.bullets[0] },
  ];
  return (
    <article className="relative flex h-full flex-col overflow-hidden bg-ink text-paper">
      <img
        src={`${aerial.src}?v=6`}
        alt={aerial.caption}
        className="absolute inset-0 h-full w-full object-cover object-top"
        crossOrigin="anonymous"
      />
      <div className="absolute inset-0 bg-ink/55" />
      <header className="relative z-2 px-[2.2cqw] pt-[1.6cqh]">
        <GoldNav active="Market" />
      </header>
      <div className="relative z-2 mt-auto px-[2.6cqw]">
        <p className="text-[0.8cqw] tracking-[0.22em] uppercase text-brass">
          Phoenix · Cushman Q2 2026
        </p>
        <h2 className="om-display mt-[0.4cqh] text-[clamp(1.8rem,3.6cqw,2.8rem)] text-brass">
          Location and market
        </h2>
        <ul className="mt-[1.4cqh] max-w-[62cqw] space-y-[0.7cqh] text-[clamp(0.72rem,1.15cqw,0.95rem)] text-paper/90">
          {deal.market.bullets.slice(0, 6).map((b) => (
            <li key={b.text}>
              <Figure field={b} label={b.text.slice(0, 24)} onPin={onPin}>
                {b.text}
              </Figure>
            </li>
          ))}
        </ul>
        <div className="mt-[2cqh] mb-[0.4cqh] flex flex-wrap gap-x-[2.2cqw] gap-y-[0.8cqh]">
          {kpis.map((k) => (
            <Figure key={k.label} field={k.field} label={k.label} onPin={onPin}>
              <p className="font-display text-[clamp(1rem,1.8cqw,1.45rem)] text-brass">{k.value}</p>
              <p className="text-[0.68cqw] tracking-[0.16em] uppercase text-paper/70">{k.label}</p>
            </Figure>
          ))}
        </div>
      </div>
      <div className="relative z-2">
        <SlideFooter n={5} />
      </div>
    </article>
  );
}

export function SlidePhotos({ onPin }: { onPin: (p: Pin) => void }) {
  const mosaic = [
    photos.find((p) => p.role === "hero"),
    photos.find((p) => p.role === "courtyard"),
    photos.find((p) => p.role === "kitchen"),
    photos.find((p) => p.role === "aerial"),
  ].filter(Boolean);
  return (
    <article className="relative flex h-full flex-col overflow-hidden bg-paper text-ink">
      <header className="shrink-0 px-[2.2cqw] pt-[1.6cqh]">
        <GoldNav active="Photos" />
      </header>
      <div className="flex min-h-0 flex-1 items-center px-[2.2cqw] py-[1.2cqh]">
        <div className="grid w-full grid-cols-2 gap-[0.8cqw]">
          {mosaic.map((p) => (
            <figure key={p!.src} className="relative aspect-video overflow-hidden">
              <img
                src={`${p!.src}?v=6`}
                alt={p!.caption}
                className="h-full w-full object-cover object-center"
                crossOrigin="anonymous"
              />
            </figure>
          ))}
        </div>
      </div>
      <SlideFooter n={6} light />
    </article>
  );
}
