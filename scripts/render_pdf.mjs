/**
 * Print collateral HTML to PDF with headless Chrome.
 *
 * These pages own their own `@page { margin: 0 }` and are laid out full-bleed,
 * so `preferCSSPageSize` is on and no header/footer templates are applied.
 * Local file access is enabled because the HTML references staged fonts and
 * images as relative paths beside it.
 *
 * Usage: node scripts/render_pdf.mjs <file.html> [more.html ...]
 */
import { existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  process.env.PUPPETEER_EXECUTABLE_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);

function chromeExecutable() {
  const found = CHROME_CANDIDATES.find((p) => existsSync(p));
  if (!found) {
    throw new Error(
      "No Chrome/Chromium found. Install Google Chrome, or set CHROME_PATH to the binary."
    );
  }
  return found;
}

async function main() {
  const inputs = process.argv.slice(2);
  if (inputs.length === 0) {
    console.error("usage: node scripts/render_pdf.mjs <file.html> [...]");
    process.exit(2);
  }

  const puppeteer = (await import("puppeteer-core")).default;
  const browser = await puppeteer.launch({
    executablePath: chromeExecutable(),
    headless: true,
    args: [
      "--no-first-run",
      "--no-default-browser-check",
      "--allow-file-access-from-files",
      "--font-render-hinting=none",
    ],
    ignoreDefaultArgs: ["--enable-automation"],
  });

  try {
    for (const input of inputs) {
      const abs = path.resolve(input);
      if (!existsSync(abs)) {
        console.error(`  ! missing ${input}`);
        process.exitCode = 1;
        continue;
      }
      const page = await browser.newPage();
      const failures = [];
      page.on("requestfailed", (req) => failures.push(req.url()));
      await page.goto(`file://${abs}`, { waitUntil: "networkidle2" });
      await page.evaluate(() => document.fonts.ready);
      const out = abs.replace(/\.html?$/i, ".pdf");
      await page.pdf({ path: out, printBackground: true, preferCSSPageSize: true });
      await page.close();
      if (failures.length) {
        console.error(`  ! ${failures.length} asset(s) failed to load in ${path.basename(abs)}:`);
        for (const url of failures.slice(0, 5)) console.error(`      ${url}`);
        process.exitCode = 1;
      }
      console.log(`  rendered ${path.basename(out)}`);
    }
  } finally {
    await Promise.race([
      browser.close().catch(() => {}),
      new Promise((r) => setTimeout(r, 5000)),
    ]);
    try {
      const proc = browser.process();
      if (proc && proc.exitCode === null) proc.kill("SIGKILL");
    } catch {}
  }
}

main().catch((err) => {
  console.error(`error: ${err.message}`);
  process.exit(1);
});
