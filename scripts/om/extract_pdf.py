"""
Stage 3a - PDF extraction.

Two jobs, both locator-bearing:

  facts   asset specs and construction/mechanical detail from the broker package
  market  headline metrics and narrative from the broker package's market
          section and from any standalone market report in the folder

Every value records the source PDF and the 1-based page it was read from. A
label with no match in the source is left out entirely -- the binder is what
turns absence into [NOT IN SOURCE], so that decision lives in one place.

Nothing here reaches the open web.

Usage:  python3 extract_pdf.py <manifest.json> <out_dir>
"""
import json
import re
import sys
from pathlib import Path

import pdfplumber


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def pages_text(path: Path):
    with pdfplumber.open(str(path)) as pdf:
        return [norm(p.extract_text() or "") for p in pdf.pages]


def cite(path: Path, page: int):
    return {"file": path.name, "page": page}


def first(pattern, pages, path, flags=re.I, group=1, cast=None):
    """Search pages in order; return the first hit with its page locator."""
    rx = re.compile(pattern, flags)
    for i, t in enumerate(pages):
        m = rx.search(t)
        if m:
            v = m.group(group).strip()
            if cast:
                try:
                    v = cast(v)
                except (ValueError, TypeError):
                    continue
            return {"value": v, "source": cite(path, i + 1)}
    return None


def money(s):
    return int(re.sub(r"[^\d]", "", s))


# Acronyms that legitimately appear inside broker prose.
_OK_CAPS = {"MSA", "SF", "US", "USA", "AZ", "TX", "CA", "AI", "GDP", "HOA",
            "LLC", "LP", "REIT", "NOI", "ASU", "TMC", "I", "A", "II", "III"}


def clean_prose(hit):
    """Reject a narrative capture that swallowed sidebar or callout text.

    Broker layouts run a display callout beside body copy, and text extraction
    splices the two into one line -- which is how a paragraph about the Phoenix
    MSA ends up containing the word AMAZON. A stray all-caps token that is not a
    known acronym means the capture is contaminated, so it is dropped rather
    than published with the artefact in it.
    """
    if not hit:
        return None
    for tok in re.findall(r"\b[A-Z][A-Z’'&/-]{2,}\b", hit["value"]):
        if tok.strip("’'&/-") not in _OK_CAPS:
            return None
    return hit


# --- stat grids ------------------------------------------------------------
# A broker "property details" page is a grid of big numbers with a small caption
# under each one. Line-based extraction shuffles those into "14 2 / NUMBER OF
# UNITS NUMBER OF BUILDINGS", so read them by position instead: find the caption,
# then take the token sitting directly above it in the same column.

_WORDS = {}


def _words(path: Path):
    key = str(path)
    if key not in _WORDS:
        with pdfplumber.open(str(path)) as pdf:
            _WORDS[key] = [p.extract_words(use_text_flow=False,
                                           keep_blank_chars=False)
                           for p in pdf.pages]
    return _WORDS[key]


def _lines(words, tol=3.0):
    """Group a page's words into visual lines, each sorted left to right.

    pdfplumber's flat word order interleaves a sidebar with the body copy, so a
    caption's tokens are only reliably adjacent within its own line.
    """
    out = []
    for w in sorted(words, key=lambda w: (round(w["bottom"], 1), w["x0"])):
        if out and abs(out[-1][-1]["bottom"] - w["bottom"]) <= tol:
            out[-1].append(w)
        else:
            out.append([w])
    for line in out:
        line.sort(key=lambda w: w["x0"])
    return out


def _label_spans(words, label):
    """Every occurrence of a caption on a page, as (x0, x1, top)."""
    toks = label.upper().split()
    lines = _lines(words)

    def runs(line, max_gap=45.0):
        """Split a visual line into horizontally contiguous phrases, so a
        sidebar caption is not treated as adjacent to the body copy beside it."""
        out = []
        for w in line:
            if out and w["x0"] - out[-1][-1]["x1"] <= max_gap:
                out[-1].append(w)
            else:
                out.append([w])
        return out

    def overlaps(a, b):
        return min(a[-1]["x1"], b[-1]["x1"]) - max(a[0]["x0"], b[0]["x0"]) > -20

    all_runs = [r for line in lines for r in runs(line)]
    candidates = list(all_runs)
    # Captions that wrap onto a second line ("Phoenix / Unemployment Rate*").
    # Pair on geometry, not on list adjacency: an unrelated line from another
    # column can sort between the two halves of one caption.
    for a in all_runs:
        for b in all_runs:
            gap = b[0]["bottom"] - a[0]["bottom"]
            if 0 < gap <= 24 and overlaps(a, b):
                candidates.append(a + b)

    for span_words in candidates:
        ups = [w["text"].upper() for w in span_words]
        for i in range(len(ups) - len(toks) + 1):
            if ups[i:i + len(toks)] == toks:
                span = span_words[i:i + len(toks)]
                yield (min(w["x0"] for w in span),
                       max(w["x1"] for w in span),
                       min(w["top"] for w in span))


def _value_line_above(words, lx0, lx1, ltop, max_gap):
    """The caption's value: the nearest text line above it in the same column.

    Grid cells are left-aligned as often as centred, so a candidate qualifies on
    either -- sharing the caption's left edge, or spanning its centre.
    """
    cx = (lx0 + lx1) / 2

    def in_column(w):
        return abs(w["x0"] - lx0) <= 15 or (w["x0"] - 12 <= cx <= w["x1"] + 12)

    best = None
    for w in words:
        # +3 rather than -1: a big figure's descender box often overlaps the
        # cap-height of the caption sitting immediately beneath it.
        if w["bottom"] > ltop + 3 or ltop - w["bottom"] > max_gap:
            continue
        if not in_column(w):
            continue
        if best is None or w["bottom"] > best["bottom"]:
            best = w
    if best is None:
        return None
    # A value can run across neighbouring words ("707 SF", "$3,100,000").
    line = [w for w in words
            if abs(w["bottom"] - best["bottom"]) < 3
            and lx0 - 20 <= w["x0"] <= lx1 + 20]
    line.sort(key=lambda w: w["x0"])
    return " ".join(w["text"] for w in line).strip() or best["text"].strip()


def stat_above_label(path: Path, label: str, cast=None, max_gap: float = 90.0):
    """Numeric stat sitting above its caption in a broker stat grid."""
    for pno, words in enumerate(_words(path)):
        for lx0, lx1, ltop in _label_spans(words, label):
            text = _value_line_above(words, lx0, lx1, ltop, max_gap)
            if not text or not re.search(r"\d", text):
                continue
            v = text
            if cast:
                try:
                    v = cast(text)
                except (ValueError, TypeError):
                    continue
            return {"value": v, "source": cite(path, pno + 1)}
    return None


def label_beside(path: Path, label: str, max_gap: float = 140.0):
    """Same geometry for a caption whose value is a word, not a number."""
    for pno, words in enumerate(_words(path)):
        for lx0, lx1, ltop in _label_spans(words, label):
            text = _value_line_above(words, lx0, lx1, ltop, max_gap)
            if text:
                return {"value": text, "source": cite(path, pno + 1)}
    return None


# --- asset facts -----------------------------------------------------------

def extract_facts(path: Path) -> dict:
    pages = pages_text(path)
    f = {}

    f["address"] = first(r"(\d+\s+[NSEW]\.?\s+\d+(?:ST|ND|RD|TH)\s+ST[^|]*)\|\s*"
                         r"(?:PHOENIX|[A-Z ]+),?\s*[A-Z]{2}", pages, path)
    f["city_state_zip"] = first(r"\|\s*([A-Z][A-Za-z ]+,\s*[A-Z]{2}\s*\d{5})", pages, path)
    f["county"] = label_beside(path, "COUNTY")
    f["units"] = stat_above_label(path, "NUMBER OF UNITS", cast=lambda s: int(money(s)))
    f["buildings"] = stat_above_label(path, "NUMBER OF BUILDINGS",
                                      cast=lambda s: int(money(s)))
    f["year_built"] = stat_above_label(path, "YEAR BUILT / RENOVATED") \
        or stat_above_label(path, "YEAR BUILT/RENOVATED") \
        or stat_above_label(path, "YEAR BUILT")
    f["avg_unit_sf"] = stat_above_label(path, "AVERAGE UNIT SIZE", cast=money)
    f["rentable_sf"] = stat_above_label(path, "RENTABLE AREA", cast=money) \
        or stat_above_label(path, "NET RENTABLE AREA", cast=money)
    f["list_price"] = stat_above_label(path, "LIST PRICE", cast=money) \
        or first(r"List Price\s+(\$[\d,]+)", pages, path, cast=money)
    f["price_per_unit"] = stat_above_label(path, "PRICE PER UNIT", cast=money)
    f["price_per_sf"] = stat_above_label(
        path, "PRICE PER SQUARE FOOT",
        cast=lambda s: float(re.sub(r"[^\d.]", "", s))) \
        or first(r"Price per Square Foot\s+\$([\d,.]+)", pages, path, cast=float)

    # Construction and mechanical, as written in the narrative.
    specs = {
        "construction": r"(block construction|wood frame|reinforced concrete|"
                        r"masonry|steel frame)",
        "roof": r"((?:pitched|flat)[a-z ]*?(?:asphalt shingle|tpo|foam|tile|shingle)"
                r"[a-z ]*roofs?)",
        "plumbing": r"((?:copper|pex|pvc|cast iron|galvanized)[a-z /,]*plumbing)",
        "sewer": r"((?:abs|pvc|cast iron|clay)[a-z ]*sewer lines?)",
        "metering": r"(individually metered for [a-z ]+|individually metered)",
        "windows": r"(new dual pane windows|dual pane windows)",
    }
    f["specs"] = {}
    for key, pat in specs.items():
        hit = first(pat, pages, path)
        if hit:
            f["specs"][key] = hit

    # Broker unit mix, kept for cross-checking the rent roll -- never merged
    # into it.
    mix = []
    rx = re.compile(r"^(Studio|\d\s*Bd?r?m?\s*/\s*\d(?:\.\d)?\s*Bath[A-Za-z \-]*)\s+"
                    r"(\d+)\s+(\d{3,4})\s+\$([\d,]+)", re.I)
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            for line in (page.extract_text() or "").splitlines():
                m = rx.match(line.strip())
                if m:
                    mix.append({"unit_description": norm(m.group(1)),
                                "units": int(m.group(2)),
                                "sqft": int(m.group(3)),
                                "proforma_rent": money(m.group(4)),
                                "source": cite(path, i + 1)})
    f["broker_unit_mix"] = mix

    # Advisors / disclaimer date give the package its vintage.
    f["package_date"] = first(r"since the date of preparation ([A-Z][a-z]+ \d{4})",
                              pages, path)
    f["brokerage"] = first(r"([A-Z][A-Za-z&.\-]{2,24})\s*\([^)]*Agent[^)]*\)\s*"
                           r"has been engaged", pages, path, flags=0)
    return f


# --- market ---------------------------------------------------------------

# Market-report and broker demographic tiles are the same shape as the property
# stat grid: a big figure with its caption underneath. Read them by position --
# line-based regex splices the sidebar into the body copy on these pages.
MARKET_METRICS = [
    ("vacancy_rate",      "Vacancy Rate"),
    ("net_absorption",    "Net Absorption, units"),
    ("asking_rent",       "Asking Rent, Per Unit"),
    ("employment",        "Phoenix Employment"),
    ("unemployment_rate", "Phoenix Unemployment Rate*"),
    ("household_growth",  "Phoenix Household Growth Rate*"),
]

DEMOGRAPHICS = [
    ("total_population",        "Total Population"),
    ("median_household_income", "Median Household Income"),
    ("average_age",             "Average Age"),
    ("median_net_worth",        "Median Net Worth"),
    ("unemployment",            "Unemployment"),
    ("median_home_value",       "Median Home Value"),
]

_FIGURE = re.compile(r"^[\$]?[\d,.]+[KMB%]?$")


def _tile(path: Path, caption: str, max_gap: float = 60.0):
    """A headline figure above its caption; rejected unless it reads as one."""
    hit = stat_above_label(path, caption, max_gap=max_gap)
    if hit and _FIGURE.match(str(hit["value"]).strip()):
        return hit
    return None


def submarket_row(path: Path, name: str):
    """Pull one submarket line out of the report's market-statistics table."""
    rx = re.compile(rf"^{re.escape(name)}\s+([\d,]+)\s+(\S+)\s+(\S+)\s+([\d,]+)\s+"
                    rf"([\d,\-]+)\s+([\d.]+%)\s+(-?[\d,]+)\s+\$([\d,]+)\s+(-?[\d.]+%)")
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            for line in (page.extract_text() or "").splitlines():
                m = rx.match(line.strip())
                if m:
                    return {
                        "submarket": name,
                        "inventory_units": int(m.group(1).replace(",", "")),
                        "under_construction": int(m.group(4).replace(",", "")),
                        "ytd_net_absorption": m.group(5),
                        "vacancy_rate": m.group(6),
                        "vacancy_change_bps": int(m.group(7).replace(",", "")),
                        "avg_asking_rent": int(m.group(8).replace(",", "")),
                        "yoy_rent_growth": m.group(9),
                        "source": cite(path, i + 1),
                    }
    return None


def extract_market(report: Path | None, broker: Path | None, submarket=None) -> dict:
    out = {"metrics": {}, "demographics": {}, "narrative": [], "submarket": None}

    if report:
        rpages = pages_text(report)
        for key, caption in MARKET_METRICS:
            hit = _tile(report, caption)
            if hit:
                out["metrics"][key] = hit
        out["report_title"] = first(r"(MARKETBEAT .*?(?:Q[1-4] \d{4}))", rpages, report) \
            or first(r"(MULTIFAMILY Q[1-4] \d{4})", rpages, report)
        if submarket:
            out["submarket"] = submarket_row(report, submarket)

    if broker:
        bpages = pages_text(broker)
        for key, caption in DEMOGRAPHICS:
            hit = _tile(broker, caption)
            if hit:
                out["demographics"][key] = hit
        out["msa_overview"] = clean_prose(first(
            r"(The Phoenix Metropolitan Area \(Phoenix MSA\)[^.]*\.[^.]*\.)",
            bpages, broker))
        out["neighborhood"] = clean_prose(first(
            r"(Urbana @ 39th is located in one of the hottest rental neighborhoods"
            r"[^.]*\.[^.]*\.)", bpages, broker))
        out["employment_node"] = clean_prose(first(
            r"(Long considered Phoenix.s financial district[^.]*\.)", bpages, broker))
        out["hospitality"] = clean_prose(first(
            r"(Just two blocks north of the community is The Global Ambassador[^.]*\.)",
            bpages, broker))
    return out


# --- driver ---------------------------------------------------------------

def main():
    manifest = json.loads(Path(sys.argv[1]).read_text())
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    submarket = sys.argv[3] if len(sys.argv) > 3 else None

    by_role = {}
    for f in manifest["files"]:
        by_role.setdefault(f["role"], []).append(Path(f["path"]))

    broker = (by_role.get("broker_om") or [None])[0]
    report = (by_role.get("market_report") or [None])[0]

    result = {
        "facts": extract_facts(broker) if broker else {},
        "market": extract_market(report, broker, submarket),
        "sources": {"broker_om": broker.name if broker else None,
                    "market_report": report.name if report else None},
    }
    (out_dir / "pdf.json").write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result, indent=2, default=str)[:5000])


if __name__ == "__main__":
    main()
