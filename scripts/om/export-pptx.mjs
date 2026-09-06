#!/usr/bin/env node
/**
 * Rasterize the 16:9 OM slides and compile a PPTX that matches the on-screen deck
 * (and therefore the Midtown Grove visual language), not an Office-default table dump.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { chromium } from "playwright";

const BASE = process.env.OM_EXPORT_URL || "http://127.0.0.1:8080";
const OUT_DIR = "/workspace/public/om-export";
const PPTX = "/workspace/public/Urbana_OM.pptx";
const SLIDES = ["asset", "rent", "t12", "budget", "market", "photos"];

mkdirSync(OUT_DIR, { recursive: true });

const browser = await chromium.launch({ args: ["--ignore-certificate-errors"] });
const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
});

const files = [];
for (const id of SLIDES) {
  const url = `${BASE}/?export=true&slide=${id}`;
  await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  const dest = `${OUT_DIR}/${id}.png`;
  await page.screenshot({ path: dest, type: "png" });
  files.push(dest);
  console.log("shot", id, dest);
}

await browser.close();

const py = `
from pptx import Presentation
from pptx.util import Inches, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pathlib import Path

files = ${JSON.stringify(files)}
dest = Path(${JSON.stringify(PPTX)})
prs = Presentation()
prs.slide_width = Inches(13.333333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]
for f in files:
    s = prs.slides.add_slide(blank)
    s.shapes.add_picture(f, Emu(0), Emu(0), prs.slide_width, prs.slide_height)
prs.save(str(dest))
print("wrote", dest, "slides", len(files))
`;
writeFileSync("/tmp/assemble_pptx.py", py);
const r = spawnSync("python3", ["/tmp/assemble_pptx.py"], { encoding: "utf8" });
if (r.status !== 0) {
  console.error(r.stdout, r.stderr);
  process.exit(r.status || 1);
}
console.log(r.stdout.trim());
