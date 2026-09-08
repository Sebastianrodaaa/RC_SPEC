"""
Stage 7 - Verify.

Two checks, both of which must pass before a deck goes out:

  trace   Every numeric token that appears on a slide is present in the
          DealPacket. A figure on a slide with no packet ancestor is, by
          definition, invented -- this is the check that catches it.
  hashes  The generator is a pure function of the packet: run it twice from a
          clean state and the .pptx bytes must match.

Also writes conflicts.md -- the reviewer-facing list of places the sources
disagree, with the cell and page references to settle each one.

Usage:  python3 verify.py <packet.json> <deck.pptx> [--rebuild CMD] [--out DIR]
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pptx import Presentation

# Tokens that are page furniture or source citations, not asserted figures.
IGNORE = re.compile(
    r"^(?:q[1-4]|20\d\d|p\.?|pp\.?|rows?|row|columns?|column|sheet|sheet1|"
    r"[a-z]{1,2}\d{1,4}|[a-z])$", re.I)


def numeric_tokens(text: str):
    """Figures a reader would take as an assertion about the deal."""
    out = []
    # (?:\.\d+)? rather than \.?\d* so a sentence-ending full stop is not
    # swallowed into the figure -- "2026." must tokenise as "2026", or it
    # stops matching the year rule below and reads as an unsourced number.
    for tok in re.findall(r"-?\$?\d[\d,]*(?:\.\d+)?%?[KMB]?", text):
        clean = tok.strip()
        if IGNORE.match(clean):
            continue
        out.append(clean)
    return out


def canonical(tok: str):
    """Compare figures by magnitude, not by how they happen to be typeset."""
    t = tok.replace("$", "").replace(",", "").replace("%", "").strip()
    mult = 1.0
    if t and t[-1] in "KMB":
        mult = {"K": 1e3, "M": 1e6, "B": 1e9}[t[-1]]
        t = t[:-1]
    try:
        return round(float(t) * mult, 2)
    except ValueError:
        return None


# Locators, filenames and hashes are metadata about where a figure came from,
# not figures. Walking them would put stray integers like the 18 in "H18" into
# the known set and blunt the whole check.
META_KEYS = {"source", "derived", "photos", "ahash", "xref", "file", "sheet",
             "cell", "page", "note", "columns", "cells", "sources", "w", "h",
             "aspect", "stddev", "colours", "source_file", "header_row",
             "source_pdf", "placeholder"}


def packet_numbers(node, acc):
    """Every number the packet asserts, in every form it could be shown."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in META_KEYS:
                continue
            packet_numbers(v, acc)
    elif isinstance(node, list):
        for v in node:
            packet_numbers(v, acc)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        acc.add(round(float(node), 2))
        acc.add(round(float(node)))
        acc.add(round(float(node) / 1000, 1))       # 12741 shown as 12.7K
        acc.add(round(float(node) / 1e6, 1))        # 2500000 shown as 2.5M
    elif isinstance(node, str):
        for tok in numeric_tokens(node):
            c = canonical(tok)
            if c is not None:
                acc.add(c)
                acc.add(round(c))
    return acc


def slide_text(deck: Path):
    prs = Presentation(str(deck))
    out = []
    for i, slide in enumerate(prs.slides, 1):
        parts = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue
            # The citation footer is locators, not assertions: "p. 20" and
            # "row 28" are where a figure came from, not a figure.
            if text.upper().startswith(("SOURCE:", "SOURCES:")):
                continue
            parts.append(text)
        out.append((i, "\n".join(parts)))
    return out


def trace(packet_path: Path, deck: Path):
    packet = json.loads(packet_path.read_text())
    known = packet_numbers(packet, set())
    # Derived presentations the deck is allowed to compute from packet values.
    for r in packet.get("rent_roll", {}).get("rows", []):
        known.add(float(r.get("units") or 0))
        known.add(float(r.get("vacant") or 0))
    known.add(float(packet.get("rent_roll", {}).get("total_units") or 0))

    orphans = []
    for n, text in slide_text(deck):
        for tok in numeric_tokens(text):
            c = canonical(tok)
            if c is None:
                continue
            # Exact match only. The packet side already carries every
            # representation the deck is allowed to print, so loosening this
            # comparison is the same as switching the check off.
            if c in known:
                continue
            orphans.append((n, tok))
    return orphans, len(known)


def sha256(path: Path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def determinism(rebuild_cmd: str, deck: Path):
    """Rebuild into a scratch path and compare hashes."""
    if not rebuild_cmd:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        second = Path(tmp) / "rebuild.pptx"
        cmd = rebuild_cmd.replace("{out}", str(second))
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr.strip()[:500]}
        return {"ok": sha256(second) == sha256(deck),
                "first": sha256(deck), "second": sha256(second)}


def write_conflicts(packet_path: Path, out: Path):
    packet = json.loads(packet_path.read_text())
    lines = ["# Source conflicts — " + packet["deal"]["name"], "",
             "Places the deal folder disagrees with itself. Nothing below was "
             "reconciled, averaged, or chosen between; both readings are shown "
             "with the cell or page that states them, so the decision stays "
             "with the reviewer.", ""]
    if not packet.get("conflicts"):
        lines.append("_No conflicts detected._")
    for c in packet.get("conflicts", []):
        lines += [f"## {c['kind'].replace('_', ' ').title()}", "",
                  c["summary"], ""]
        for v in c["values"]:
            s = v["source"]
            if "cell" in s:
                loc = f"`{s['file']}` → `{s['sheet']}!{s['cell']}`"
            elif "page" in s:
                loc = f"`{s['file']}` → p. {s['page']}"
            else:
                loc = s.get("note", "")
            lines.append(f"- **{v['name']}** — {loc}")
        lines.append("")

    placeholders = []

    def walk(node, path):
        if isinstance(node, dict):
            if node.get("placeholder"):
                placeholders.append((path, node.get("note", "")))
                return
            # A list entry that names itself reads better as its own label than
            # as an array index: "Payroll", not "lines[1]".
            label = node.get("label") or node.get("unit_type")
            for k, v in node.items():
                if k == "label":
                    continue
                child = f"{path}.{k}" if path else k
                if label and isinstance(v, dict):
                    child = f"{path.rsplit('[', 1)[0]} → {label} → {k}" \
                        if "[" in path else f"{path}.{k}"
                walk(v, child)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(packet, "")
    if placeholders:
        lines += ["## Not in source", "",
                  "Fields the deck marks `[NOT IN SOURCE]` because no file in "
                  "the folder states them:", ""]
        for path, note in placeholders:
            lines.append(f"- `{path}`" + (f" — {note}" if note else ""))
        lines.append("")
    out.write_text("\n".join(lines))
    return len(packet.get("conflicts", [])), len(placeholders)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("packet")
    ap.add_argument("deck")
    ap.add_argument("--rebuild", default=None,
                    help="shell command that rebuilds the deck; {out} is "
                         "substituted with a scratch path")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()

    packet_path, deck = Path(a.packet), Path(a.deck)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    orphans, known = trace(packet_path, deck)
    print(f"trace: {known} distinct figures in the packet")
    if orphans:
        print(f"  FAIL — {len(orphans)} slide figures with no packet ancestor:")
        for n, tok in orphans[:40]:
            print(f"    slide {n}: {tok}")
    else:
        print("  PASS — every figure on every slide traces to the packet")

    det = determinism(a.rebuild, deck)
    if det is None:
        print("determinism: skipped (no --rebuild given)")
    elif det.get("error"):
        print(f"determinism: ERROR — {det['error']}")
    elif det["ok"]:
        print(f"  PASS — rebuild is byte-identical ({det['first'][:16]}…)")
    else:
        print(f"  FAIL — {det['first'][:16]}… vs {det['second'][:16]}…")

    n_conf, n_ph = write_conflicts(packet_path, out_dir / "conflicts.md")
    print(f"conflicts.md: {n_conf} conflicts, {n_ph} [NOT IN SOURCE] fields")

    ok = not orphans and (det is None or det.get("ok"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
