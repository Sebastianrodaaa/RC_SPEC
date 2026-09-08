"""
End-to-end: deal folder in, OM deck out.

    python3 run.py <deal_folder> <out_dir> [--submarket Camelback]
                   [--name urbana_om] [--config layout.json] [--keep-work]

Runs every stage in order and stops at the first failure, so a bad extract
never reaches a slide:

    ingest -> excel -> pdf -> photos -> seal -> bind -> compile -> verify

Writes into <out_dir>:
    <name>.pptx       the deck
    conflicts.md      where the sources disagree, with locators
    packet.json       the DealPacket every figure came from
    work/             intermediate extracts and harvested photos
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(argv, label):
    print(f"\n== {label}")
    r = subprocess.run([sys.executable, *argv], capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.rstrip())
    if r.returncode != 0:
        print(r.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(f"{label} failed (exit {r.returncode})")
    return r


def find_role(manifest, role):
    for f in manifest["files"]:
        if f["role"] == role:
            return Path(f["path"])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("out")
    ap.add_argument("--submarket", default=None,
                    help="submarket name to pull from the market report's "
                         "statistics table, e.g. Camelback")
    ap.add_argument("--name", default="offering_memorandum")
    ap.add_argument("--config", default=None,
                    help="JSON overriding which broker pages photos come from")
    ap.add_argument("--keep-work", action="store_true")
    a = ap.parse_args()

    folder = Path(a.folder).resolve()
    out = Path(a.out).resolve()
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)

    run([str(HERE / "ingest.py"), str(folder), str(work)], "1. ingest")
    manifest = json.loads((work / "manifest.json").read_text())

    broker = find_role(manifest, "broker_om")
    template = find_role(manifest, "template_om")
    if broker is None:
        raise SystemExit("no broker package found in the folder")

    run([str(HERE / "extract.py"), str(work / "manifest.json"), str(work)],
        "2. excel")

    pdf_argv = [str(HERE / "extract_pdf.py"), str(work / "manifest.json"),
                str(work)]
    if a.submarket:
        pdf_argv.append(a.submarket)
    run(pdf_argv, "3. pdf")

    run([str(HERE / "extract_images.py"), str(broker), str(work)], "4. photos")

    seal_png = work / "rc_seal_white.png"
    if template:
        run([str(HERE / "extract_logo.py"), str(template), str(seal_png),
             "--page", "1", "--ink", "white"], "5. seal")
    else:
        print("\n== 5. seal\n  skipped — no template OM in the folder")

    bind_argv = [str(HERE / "bind.py"), str(work)]
    if a.submarket:
        bind_argv += ["--submarket", a.submarket]
    run(bind_argv, "6. bind")

    deck = out / f"{a.name}.pptx"
    compile_argv = [str(HERE / "compile_deck.py"), str(work / "packet.json"),
                    str(deck), "--photos", str(work / "photos")]
    if seal_png.exists():
        compile_argv += ["--seal", str(seal_png)]
    if a.config:
        compile_argv += ["--config", a.config]
    run(compile_argv, "7. compile")

    shutil.copy(work / "packet.json", out / "packet.json")

    rebuild = " ".join([sys.executable, str(HERE / "compile_deck.py"),
                        f'"{work / "packet.json"}"', "{out}",
                        "--photos", f'"{work / "photos"}"']
                       + (["--seal", f'"{seal_png}"'] if seal_png.exists() else [])
                       + (["--config", f'"{a.config}"'] if a.config else []))
    r = subprocess.run(
        [sys.executable, str(HERE / "verify.py"), str(work / "packet.json"),
         str(deck), "--out", str(out), "--rebuild", rebuild],
        capture_output=True, text=True)
    print("\n== 8. verify")
    print(r.stdout.rstrip())
    if r.returncode != 0:
        print(r.stderr.rstrip(), file=sys.stderr)
        raise SystemExit("verification failed — the deck was written but should "
                         "not be sent")

    if not a.keep_work:
        print(f"\n(work files kept at {work} — pass --keep-work to silence "
              f"this note)")
    print(f"\ndeck:      {deck}")
    print(f"conflicts: {out / 'conflicts.md'}")
    print(f"packet:    {out / 'packet.json'}")


if __name__ == "__main__":
    main()
