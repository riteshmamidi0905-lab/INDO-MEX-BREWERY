// Visual regression: screenshots every page at six widths, compares with a local baseline (website/qa/.baseline, git-ignored) using pixelmatch.
// First run (or --update) writes the baseline. Exit 1 if any page differs by more than the threshold.
import { chromium } from "playwright-core"; import fs from "fs"; import path from "path"; import http from "http"; import { fileURLToPath } from "url";
import { PNG } from "pngjs"; import pixelmatch from "pixelmatch";
const here = path.dirname(fileURLToPath(import.meta.url)); const dist = path.join(here, "..", "dist"); const bdir = path.join(here, ".baseline"); fs.mkdirSync(bdir, { recursive: true });
const update = process.argv.includes("--update"); const types = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2", ".avif": "image/avif", ".webp": "image/webp", ".jpg": "image/jpeg" };
const srv = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split("?")[0]); if (p === "/") p = "/index.html"; const f = path.join(dist, p); if (!f.startsWith(dist) || !fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r); });
await new Promise(r => srv.listen(0, r)); const base = `http://127.0.0.1:${srv.address().port}`;
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
const pages = fs.readdirSync(dist).filter(f => f.endsWith(".html")); const widths = [320, 390, 768, 1280, 1440, 1920]; let diffs = [], made = 0, same = 0;
for (const w of widths) { const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, colorScheme: "dark", reducedMotion: "reduce" });
  for (const pg of pages) { const page = await ctx.newPage(); await page.goto(`${base}/${pg}`, { waitUntil: "load" }); await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } scrollTo(0, 0); }); await page.waitForTimeout(300);
    const buf = await page.screenshot({ fullPage: true }); await page.close(); const f = path.join(bdir, `${pg}-${w}.png`);
    if (update || !fs.existsSync(f)) { fs.writeFileSync(f, buf); made++; continue; }
    const a = PNG.sync.read(fs.readFileSync(f)), b = PNG.sync.read(buf);
    if (a.width !== b.width || a.height !== b.height) { diffs.push(`${pg}@${w}: size ${a.width}x${a.height} -> ${b.width}x${b.height}`); continue; }
    const n = pixelmatch(a.data, b.data, null, a.width, a.height, { threshold: 0.1 }); if (n / (a.width * a.height) > 0.001) diffs.push(`${pg}@${w}: ${n} px differ (${(100 * n / (a.width * a.height)).toFixed(2)}%)`); else same++; }
  await ctx.close(); }
await browser.close(); srv.close();
console.log(`baseline written: ${made}; unchanged: ${same}; changed: ${diffs.length}`); diffs.forEach(d => console.log("DIFF", d)); process.exit(diffs.length ? 1 : 0);
