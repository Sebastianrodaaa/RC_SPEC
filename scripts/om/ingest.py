"""
Stage 1 - Ingest.

Classify every file in a deal folder by MIME + first-page role, never by filename.
Emits a manifest JSON that later stages consume.

Usage:  python3 ingest.py <deal_folder> <out_dir>
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

# --- role signatures -------------------------------------------------------
# Each rule: (role, weight, regex tested against normalised first-pages text
#             or against sheet names for workbooks)
PDF_RULES = [
    ("template_om", 3, r"preliminary investment summary|quick glance|net to limited partners"),
    ("template_om", 2, r"investment terms.*holding term|carried interest/promote"),
    ("broker_om", 3, r"offering memorandum|exclusive advisors|exclusively (listed|represent)"),
    ("broker_om", 2, r"table of\s*contents.*executive summary.*property overview"),
    ("market_report", 3, r"marketbeat|market ?report|research report|q[1-4]\s*20\d\d"),
    ("market_report", 2, r"vacancy rate.*asking rent.*net absorption"),
    ("spec", 3, r"objective|success criteria|out of scope|poc"),
]

XL_RULES = [
    ("rent_roll", 3, r"rent ?roll"),
    ("t12", 3, r"t-?12|trailing|profit (and|&) loss|income statement"),
    ("budget", 3, r"budget|proforma|pro ?forma"),
]

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}
XL_EXT = {".xlsx", ".xlsm", ".xltx", ".xls"}
DOC_EXT = {".docx", ".doc"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).lower()


def _pdf_first_pages_text(path: Path, n: int = 4) -> str:
    try:
        import pdfplumber
        out = []
        with pdfplumber.open(str(path)) as pdf:
            npages = len(pdf.pages)
            for i in range(min(n, npages)):
                out.append(pdf.pages[i].extract_text() or "")
        return "\n".join(out), npages
    except Exception:
        return "", 0


def _pdf_full_text(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:
        return ""


def _xl_sheetnames(path: Path):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        names = list(wb.sheetnames)
        wb.close()
        return names
    except Exception:
        return []


def _docx_text(path: Path) -> str:
    try:
        import docx
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    except Exception:
        return ""


def _mime(path: Path) -> str:
    try:
        r = subprocess.run(["file", "--mime-type", "-b", str(path)],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except Exception:
        return ""


def _score(rules, text):
    hits = {}
    for role, weight, pat in rules:
        if re.search(pat, text):
            hits[role] = hits.get(role, 0) + weight
    return hits


def classify(path: Path) -> dict:
    ext = path.suffix.lower()
    mime = _mime(path)
    rec = {"path": str(path), "name": path.name, "mime": mime,
           "bytes": path.stat().st_size, "role": "unknown", "evidence": {}}

    if mime == "application/pdf" or ext == ".pdf":
        head, npages = _pdf_first_pages_text(path)
        text = _norm(head)
        hits = _score(PDF_RULES, text)
        # A template OM and a broker OM can both say "offering memorandum".
        # The template is the one that carries RC's own investment-terms language.
        if not hits:
            full = _norm(_pdf_full_text(path))
            hits = _score(PDF_RULES, full)
        rec["pages"] = npages
        if hits:
            rec["role"] = max(hits.items(), key=lambda kv: kv[1])[0]
            rec["evidence"] = hits
        else:
            rec["role"] = "pdf_other"

    elif ext in XL_EXT:
        sheets = _xl_sheetnames(path)
        text = _norm(" ".join(sheets) + " " + path.stem)
        hits = _score(XL_RULES, text)
        rec["sheets"] = sheets
        if hits:
            rec["role"] = max(hits.items(), key=lambda kv: kv[1])[0]
            rec["evidence"] = hits
        else:
            rec["role"] = "workbook_other"

    elif ext in DOC_EXT:
        text = _norm(_docx_text(path))
        hits = _score(PDF_RULES, text)
        rec["role"] = "spec" if hits.get("spec") else "doc_other"

    elif ext in IMAGE_EXT or mime.startswith("image/"):
        rec["role"] = "photo"

    return rec


def main():
    folder = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in folder.rglob("*")
                   if p.is_file() and not p.name.startswith("."))
    manifest = {"folder": str(folder), "files": [classify(p) for p in files]}

    by_role = {}
    for f in manifest["files"]:
        by_role.setdefault(f["role"], []).append(f["name"])
    manifest["by_role"] = by_role

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(by_role, indent=2))


if __name__ == "__main__":
    main()
