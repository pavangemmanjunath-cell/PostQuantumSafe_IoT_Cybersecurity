/* Render the hand-drawn SVG figures of docs/release-3/figures to PDF (vector) and 2× PNG (for Word) with the
 * Playwright Chromium bundled in frontend/.
 *
 *   node scripts/svg_to_pdf.cjs            (run from the repository root after `cd frontend && npm ci`)
 */
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require(path.join(__dirname, "..", "frontend", "node_modules", "playwright"));

const FIGURES = [
  ["fig1_evaluation_design.svg", 1400, 800],
  ["fig2_threat_model.svg", 1400, 760],
];
const DIR = path.join(__dirname, "..", "docs", "release-3", "figures");

(async () => {
  const browser = await chromium.launch();
  try {
    for (const [name, w, h] of FIGURES) {
      const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
      await page.goto(pathToFileURL(path.join(DIR, name)).href);
      const pdf = path.join(DIR, name.replace(/\.svg$/, ".pdf"));
      await page.pdf({ path: pdf, width: `${w}px`, height: `${h}px`, printBackground: true, pageRanges: "1" });
      const png = path.join(DIR, name.replace(/\.svg$/, ".png"));
      await page.screenshot({ path: png, fullPage: false });
      await page.close();
      console.log("written:", pdf, "and", png);
    }
  } finally {
    await browser.close();
  }
})();
