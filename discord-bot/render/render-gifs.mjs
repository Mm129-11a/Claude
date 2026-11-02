// Renders every mascot animation to assets/<name>.gif with headless Chromium.
// Usage: npm run render
import { createRequire } from 'node:module';
import gifenc from 'gifenc';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

// Playwright is resolved like require() does (works with a global install too).
const { chromium } = createRequire(import.meta.url)('playwright');
const { GIFEncoder, quantize, applyPalette } = gifenc;

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(here, '..', 'assets');
mkdirSync(outDir, { recursive: true });
const FPS = 20;

const html = `<!doctype html><html><body style="margin:0;background:#000">
<script>${readFileSync(path.join(here, '..', 'node_modules', 'three', 'build', 'three.min.js'), 'utf8')}</script>
<script>${readFileSync(path.join(here, 'mascot.js'), 'utf8')}</script></body></html>`;

const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
const page = await browser.newPage();
page.on('pageerror', e => { console.error(e); process.exitCode = 1; });
await page.setContent(html);
const names = process.argv.slice(2).length ? process.argv.slice(2) : await page.evaluate(() => window.ANIM_NAMES);

for (const name of names) {
  const { width, height, count } = await page.evaluate(([n, f]) => window.animInfo(n, f), [name, FPS]);
  const delay = Math.round(1000 / FPS);
  const frames = [];
  for (let i = 0; i < count; i++) {
    const b64 = await page.evaluate(([n, k, f]) => window.renderFrame(n, k, f), [name, i, FPS]);
    frames.push(new Uint8Array(Buffer.from(b64, 'base64')));
  }
  const gif = GIFEncoder();
  // One shared palette (sampled from a few frames) keeps colours steady.
  const picks = frames.filter((_, i) => i % Math.max(1, Math.floor(frames.length / 6)) === 0);
  const sample = new Uint8Array(picks.length * width * height * 4);
  picks.forEach((f, i) => sample.set(f, i * width * height * 4));
  const palette = quantize(sample, 256);
  for (const f of frames) {
    gif.writeFrame(applyPalette(f, palette), width, height, { palette, delay });
  }
  gif.finish();
  writeFileSync(path.join(outDir, `${name}.gif`), gif.bytes());
  console.log(`${name}.gif  ${frames.length} frames  ${(gif.bytes().length / 1024).toFixed(0)} KB`);
}
await browser.close();
