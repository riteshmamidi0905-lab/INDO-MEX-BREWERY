// Lighthouse (real Chromium, local static server). Records category scores; SEO is expected to be limited because pages are noindex.
import { spawn } from "child_process"; import http from "http"; import fs from "fs"; import path from "path"; import { fileURLToPath } from "url";
import lighthouse from "lighthouse"; import * as chromeLauncher from "chrome-launcher";
const here = path.dirname(fileURLToPath(import.meta.url)); const dist = path.join(here, "..", "dist");
const types = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2", ".avif": "image/avif", ".webp": "image/webp", ".jpg": "image/jpeg" };
const srv = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split("?")[0]); if (p === "/") p = "/index.html"; const f = path.join(dist, p);
  if (!f.startsWith(dist) || !fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r); });
await new Promise(r => srv.listen(0, r)); const base = `http://127.0.0.1:${srv.address().port}`;
const chrome = await chromeLauncher.launch({ chromePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", chromeFlags: ["--headless=new", "--no-sandbox"] });
const out = { date: new Date().toISOString(), tool: "lighthouse " + (JSON.parse(fs.readFileSync(path.join(here, "node_modules/lighthouse/package.json"))).version), runs: {} };
for (const pg of ["index.html", "food.html", "beer.html", "space.html", "pairings.html", "labs.html", "investor.html"]) for (const form of ["mobile", "desktop"]) {
  const cfg = form === "desktop" ? { extends: "lighthouse:default", settings: { formFactor: "desktop", screenEmulation: { mobile: false, width: 1350, height: 940, deviceScaleFactor: 1, disabled: false }, throttling: { rttMs: 40, throughputKbps: 10240, cpuSlowdownMultiplier: 1 } } } : undefined;
  const r = await lighthouse(`${base}/${pg}`, { port: chrome.port, output: "json", logLevel: "error", onlyCategories: ["performance", "accessibility", "best-practices", "seo"] }, cfg);
  const c = r.lhr.categories, a = r.lhr.audits;
  out.runs[`${pg}:${form}`] = { performance: Math.round(c.performance.score * 100), accessibility: Math.round(c.accessibility.score * 100), bestPractices: Math.round(c["best-practices"].score * 100), seo: Math.round(c.seo.score * 100), lcpMs: Math.round(a["largest-contentful-paint"].numericValue), cls: +a["cumulative-layout-shift"].numericValue.toFixed(3), tbtMs: Math.round(a["total-blocking-time"].numericValue), transferKB: Math.round(a["total-byte-weight"].numericValue / 1024) };
}
await chrome.kill(); srv.close();
fs.writeFileSync(path.join(here, "results/lighthouse.json"), JSON.stringify(out, null, 1)); console.log(JSON.stringify(out.runs, null, 1));
