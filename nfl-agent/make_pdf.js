// Render reports/DATE-nfl-props.html to a PDF with every pick expanded.
// Usage: node make_pdf.js reports/2026-11-22-nfl-props.html
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const src = path.resolve(process.argv[2]);
  const out = src.replace(/\.html$/, '.pdf');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + src, { waitUntil: 'networkidle' }).catch(() => {});
  await page.evaluate(() => document.querySelectorAll('details').forEach(d => (d.open = true)));
  await page.emulateMedia({ media: 'print', colorScheme: 'light' });
  await page.pdf({ path: out, format: 'Letter', printBackground: true,
    margin: { top: '0.5in', bottom: '0.5in', left: '0.5in', right: '0.5in' } });
  await browser.close();
  console.log('wrote', out);
})();
