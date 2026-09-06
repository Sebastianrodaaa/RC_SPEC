import { createFileRoute } from "@tanstack/react-router";
import { Deck } from "@/components/om/Deck";

type Search = {
  export?: boolean;
  slide?: string;
};

export const Route = createFileRoute("/")({
  validateSearch: (raw: Record<string, unknown>): Search => ({
    export:
      raw.export === "1" ||
      raw.export === 1 ||
      raw.export === true ||
      raw.export === "true",
    slide: typeof raw.slide === "string" ? raw.slide : undefined,
  }),
  component: Home,
});

function Home() {
  const search = Route.useSearch();
  return <Deck exportMode={Boolean(search.export)} slideId={search.slide} />;
}
