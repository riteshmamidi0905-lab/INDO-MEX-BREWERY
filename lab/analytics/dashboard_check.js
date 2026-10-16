// Screenshot + basic accessibility/network check for the static dashboard. node analytics/dashboard_check.js
// CHROMIUM_PATH=/opt/pw-browsers/chromium/... ; playwright from /home/user/riteshmamidi0905-lab.github.io/node_modules
const path = require('path'), fs = require('fs');
const { chromium } = require('/home/user/riteshmamidi0905-lab.github.io/node_modules/playwright');
(async () => {
  const file = path.resolve(__dirname, '../results/analytics/dashboard.html');
  const exe = process.env.CHROMIUM_PATH || undefined;
  const browser = await chromium.launch({ executablePath: exe });
  const out = { views: [] };
  for (const [name, vp, scheme] of [['desktop-light', { width: 1280, height: 900 }, 'light'], ['phone-light', { width: 375, height: 800 }, 'light'], ['desktop-dark', { width: 1280, height: 900 }, 'dark']]) {
    const ctx = await browser.newContext({ viewport: vp, colorScheme: scheme });
    const page = await ctx.newPage(); const requests = [];
    page.on('request', r => { if (!r.url().startsWith('file://')) requests.push(r.url()); });
    await page.goto('file://' + file);
    const m = await page.evaluate(() => ({ scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth, h1: document.querySelectorAll('h1').length, svgs: document.querySelectorAll('svg[role=img]').length,
      svgLabelled: [...document.querySelectorAll('svg[role=img]')].every(s => s.getAttribute('aria-label')), tables: document.querySelectorAll('table caption').length, lang: document.documentElement.lang }));
    await page.screenshot({ path: path.resolve(__dirname, `../results/analytics/dashboard_${name}.png`), fullPage: true });
    out.views.push({ name, ...m, horizontalScroll: m.scrollW > m.innerW, externalRequests: requests });
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(path.resolve(__dirname, '../results/analytics/dashboard_check.json'), JSON.stringify(out, null, 1) + '\n');
  console.log(JSON.stringify(out, null, 1));
})();
