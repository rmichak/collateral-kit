/**
 * Rasterise every `.page` of a collateral HTML file to PNG.
 *
 * This exists to make the visual check cheap and therefore actually done.
 * A PDF that renders without errors can still be wrong — text overflowing its
 * box, a scrim too weak to carry the headline, an image cropped through a face.
 * Look at these before anything ships.
 *
 * Usage: node scripts/proof.mjs <file.html> [--scale 2] [--out <dir>]
 */
import { existsSync, mkdirSync } from "node:fs";
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

function parseArgs(argv) {
  const files = [];
  const opts = { scale: 1.5, out: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--scale") opts.scale = Number(argv[++i]);
    else if (argv[i] === "--out") opts.out = argv[++i];
    else files.push(argv[i]);
  }
  return { files, opts };
}

async function main() {
  const { files, opts } = parseArgs(process.argv.slice(2));
  if (files.length === 0) {
    console.error("usage: node scripts/proof.mjs <file.html> [--scale 2] [--out dir]");
    process.exit(2);
  }
  const exe = CHROME_CANDIDATES.find((p) => existsSync(p));
  if (!exe) throw new Error("No Chrome/Chromium found. Set CHROME_PATH.");

  const puppeteer = (await import("puppeteer-core")).default;
  const browser = await puppeteer.launch({
    executablePath: exe,
    headless: true,
    args: ["--no-first-run", "--allow-file-access-from-files", "--font-render-hinting=none"],
    ignoreDefaultArgs: ["--enable-automation"],
  });

  try {
    for (const input of files) {
      const abs = path.resolve(input);
      const stem = path.basename(abs).replace(/\.html?$/i, "");
      const outDir = opts.out ? path.resolve(opts.out) : path.join(path.dirname(abs), "proof");
      mkdirSync(outDir, { recursive: true });

      const page = await browser.newPage();
      await page.setViewport({ width: 816, height: 1056, deviceScaleFactor: opts.scale });
      await page.goto(`file://${abs}`, { waitUntil: "networkidle2" });
      await page.evaluate(() => document.fonts.ready);

      const handles = await page.$$(".page");
      if (handles.length === 0) console.error(`  ! ${stem}: no .page elements found`);
      for (let i = 0; i < handles.length; i++) {
        const out = path.join(outDir, `${stem}-p${String(i + 1).padStart(2, "0")}.png`);
        await handles[i].screenshot({ path: out });
        console.log(`  proof ${path.relative(process.cwd(), out)}`);
      }
      await page.close();
    }
  } finally {
    await Promise.race([browser.close().catch(() => {}), new Promise((r) => setTimeout(r, 5000))]);
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
