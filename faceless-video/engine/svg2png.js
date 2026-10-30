// Renders SVG files to PNG with the preinstalled Chromium.
// Usage: node svg2png.js in1.svg out1.png [in2.svg out2.png ...]
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (let i = 0; i < args.length; i += 2) {
    const svg = fs.readFileSync(args[i], 'utf8');
    const m = svg.match(/viewBox="0 0 (\d+) (\d+)"/);
    const [w, h] = m ? [+m[1], +m[2]] : [1600, 1200];
    await page.setViewportSize({ width: w, height: h });
    await page.setContent(`<html><body style="margin:0;background:#000">${svg}</body></html>`);
    await page.screenshot({ path: args[i + 1], clip: { x: 0, y: 0, width: w, height: h } });
  }
  await browser.close();
})();
