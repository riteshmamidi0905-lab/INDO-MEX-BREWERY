// Real browser QA: overflow, axe (WCAG 2.2 AA), page weight, CLS/LCP, console errors, no-JS render.
import { chromium } from "playwright-core";
import fs from "fs"; import path from "path"; import http from "http";
import { fileURLToPath } from "url";
const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(here, "..", process.env.NASHA_DIST || "dist");
const axeSrc = fs.readFileSync(path.join(here, "node_modules/axe-core/axe.min.js"), "utf8");
const types = { ".html":"text/html", ".css":"text/css", ".js":"text/javascript", ".woff2":"font/woff2", ".txt":"text/plain" };
const srv = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split("?")[0]); if (p === "/") p = "/index.html";
  const f = path.join(dist, p); if (!f.startsWith(dist) || !fs.existsSync(f)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r); });
await new Promise(r => srv.listen(0, r)); const base = `http://127.0.0.1:${srv.address().port}`;
const pages = fs.readdirSync(dist).filter(f => f.endsWith(".html"));
const widths = [320, 390, 768, 1280, 1440, 1920];
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
import crypto from "crypto";
const distHash = crypto.createHash("sha256").update(fs.readdirSync(dist).filter(f => /\.(html|css|js)$/.test(f)).sort().map(f => fs.readFileSync(path.join(dist, f))).reduce((a, b) => Buffer.concat([a, b]), Buffer.alloc(0))).digest("hex").slice(0, 16);
const out = { distHash, date: new Date().toISOString(), pages: {}, summary: {}, slow: {}, imagesBlocked: {} };
const reqs = new Set();
for (const pg of pages) {
  const rec = { overflow: {}, axe: {}, console: [], bytes: 0, requests: [], perf: {}, noJs: {} };
  for (const scheme of ["dark", "light"]) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: scheme });
    const page = await ctx.newPage();
    page.on("console", m => { if (["error", "warning"].includes(m.type())) rec.console.push(m.text()); });
    page.on("pageerror", e => rec.console.push("pageerror " + e.message));
    page.on("request", r => { if (!r.url().startsWith(base)) rec.console.push("EXTERNAL REQUEST " + r.url()); });
    await page.addInitScript(() => { window.__cls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: "layout-shift", buffered: true });
      window.__lcp = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lcp = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); });
    let bytes = 0; page.on("response", async r => { try { const b = await r.body(); bytes += b.length; if (scheme === "dark") rec.requests.push(r.url().replace(base, "")); } catch {} });
    await page.goto(`${base}/${pg}`, { waitUntil: "networkidle" });
    if (scheme === "dark") rec.initialBytes = bytes;
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); });
    await page.waitForTimeout(3000);
    await page.addScriptTag({ content: axeSrc });
    const res = await page.evaluate(() => axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"] } }));
    rec.axe[scheme] = { violations: res.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, sample: v.nodes[0]?.html?.slice(0, 140), why: v.nodes[0]?.failureSummary?.slice(0, 200) })), passes: res.passes.length, incomplete: res.incomplete.map(i => i.id), incompleteDetail: res.incomplete.filter(i => i.id === "color-contrast").flatMap(i => i.nodes.map(n => ({ target: n.target.join(" "), reason: (n.any[0] && n.any[0].data && n.any[0].data.messageKey) || (n.any[0] && n.any[0].message) || "" }))).slice(0, 40) };
    if (scheme === "dark") { rec.bytes = bytes; rec.perf = await page.evaluate(() => ({ cls: Number(window.__cls.toFixed(4)), lcp_ms: Math.round(window.__lcp) })); }
    await ctx.close();
  }
  for (const w of widths) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } }); const page = await ctx.newPage();
    await page.goto(`${base}/${pg}`, { waitUntil: "networkidle" });
    rec.overflow[w] = await page.evaluate(() => ({ scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth }));
    rec.overflow[w].ok = rec.overflow[w].scrollW <= rec.overflow[w].clientW;
    await ctx.close();
  }
  { const ctx = await browser.newContext({ javaScriptEnabled: false }); const page = await ctx.newPage(); await page.goto(`${base}/${pg}`);
    rec.noJs = await page.evaluate(() => ({ h1: document.querySelectorAll("h1").length, textLen: document.body.innerText.length, hiddenFilters: [...document.querySelectorAll("[data-filter-group]")].every(e => getComputedStyle(e).display === "none"), items: document.querySelectorAll("[data-item]").length, visibleItems: [...document.querySelectorAll("[data-item]")].filter(e => e.offsetParent !== null).length }));
    await ctx.close(); }
  { const ctx = await browser.newContext({ viewport: { width: 390, height: 800 }, reducedMotion: "reduce" }); const page = await ctx.newPage(); await page.goto(`${base}/${pg}`);
    rec.reducedMotion = await page.evaluate(() => [...document.querySelectorAll(".glow,.steam")].every(e => getComputedStyle(e).animationName === "none")); await ctx.close(); }
  out.pages[pg] = rec;
}
// Slow connection (CDP, about 1.6 Mbps down, 150 ms RTT) on the home page: time to hero image decoded
{ const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } }); const page = await ctx.newPage(); const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.enable"); await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  const t0 = Date.now(); await page.goto(`${base}/index.html`, { waitUntil: "load" });
  await page.waitForFunction(() => { const i = document.querySelector(".fig-hero img, .hero img"); return i && i.complete && i.naturalWidth > 0; }, null, { timeout: 30000 });
  const ms = Date.now() - t0; const used = await page.evaluate(() => document.querySelector(".fig-hero img, .hero img").currentSrc);
  out.slow = { profile: "1.6 Mbps, 150 ms RTT, 390px viewport", heroReadyMs: ms, heroSrc: used.replace(base, "") }; await ctx.close(); }
// Image failure: block all images, check layout holds and alt text is present
for (const pg of ["index.html", "court.html"]) { const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } }); const page = await ctx.newPage();
  await page.route(/\.(avif|webp|jpg)$/, r => r.abort()); await page.goto(`${base}/${pg}`, { waitUntil: "load" });
  out.imagesBlocked[pg] = await page.evaluate(() => ({ imgs: document.querySelectorAll("figure img").length, withAlt: [...document.querySelectorAll("figure img")].filter(i => i.alt && i.alt.length > 20).length, overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, h1: !!document.querySelector("h1") })); await ctx.close(); }
// Manual-review aids run in a real browser: focus visibility of every focusable element, WCAG 1.4.12 text spacing, 200% zoom reflow
out.manual = { focus: {}, textSpacing: {}, zoom200: {} };
for (const pg of pages) { const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } }); const page = await ctx.newPage(); await page.goto(`${base}/${pg}`, { waitUntil: "load" });
  const els = await page.$$('a[href], button:not([disabled]), input, [tabindex]:not([tabindex="-1"])'); let total = 0, bad = []; 
  for (const el of els) { if (!(await el.isVisible())) continue; total++; await el.focus(); const ok = await el.evaluate(e => { const s = getComputedStyle(e); const f = e.matches(":focus-visible"); return { f, outline: s.outlineStyle !== "none" && parseFloat(s.outlineWidth) >= 2 }; }); if (!ok.outline) bad.push(await el.evaluate(e => e.outerHTML.slice(0, 80))); }
  out.manual.focus[pg] = { focusable: total, withoutVisibleOutline: bad.length, sample: bad.slice(0, 3) };
  await page.addStyleTag({ content: "*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-bottom:2em!important}" });
  out.manual.textSpacing[pg] = await page.evaluate(() => ({ overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth })); await ctx.close();
  const c2 = await browser.newContext({ viewport: { width: 640, height: 400 } }); const p2 = await c2.newPage(); await p2.goto(`${base}/${pg}`, { waitUntil: "load" });
  out.manual.zoom200[pg] = await p2.evaluate(() => ({ overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth })); await c2.close(); }
// Keyboard test on food page (filter removed in Sprint 24: Core 5 only)
{ const ctx = await browser.newContext({ viewport: { width: 390, height: 800 } }); const page = await ctx.newPage(); await page.goto(`${base}/food.html`);
  const total = await page.locator("article, .card").count();
  await page.keyboard.press("Tab"); const first = await page.evaluate(() => document.activeElement.className || document.activeElement.tagName);
  out.interaction = { total, firstTab: first, firstTabIsSkipLink: first === "skip" }; await ctx.close(); }
await browser.close(); srv.close();
const allAxe = Object.values(out.pages).flatMap(p => Object.values(p.axe).flatMap(a => a.violations));
out.summary = { pages: pages.length, axeViolations: allAxe.length, overflowFailures: Object.values(out.pages).flatMap(p => Object.entries(p.overflow).filter(([, v]) => !v.ok)).length,
  maxBytes: Math.max(...Object.values(out.pages).map(p => p.bytes)), maxInitialBytes: Math.max(...Object.values(out.pages).map(p => p.initialBytes)), homeInitialBytes: out.pages["index.html"].initialBytes, maxCls: Math.max(...Object.values(out.pages).map(p => p.perf.cls)), maxLcpMs: Math.max(...Object.values(out.pages).map(p => p.perf.lcp_ms)),
  consoleIssues: Object.values(out.pages).flatMap(p => p.console).length };
fs.writeFileSync(path.join(here, `results/${process.env.NASHA_RESULTS || "latest"}.json`), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out.summary), JSON.stringify(out.interaction));
for (const [pg, p] of Object.entries(out.pages)) for (const [s, a] of Object.entries(p.axe)) for (const v of a.violations) console.log(pg, s, v.id, v.impact, v.nodes, v.sample, "|", v.why);
