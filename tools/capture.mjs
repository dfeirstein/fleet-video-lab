// Full-page screenshot. No npm install: node >= 22 (global WebSocket) + the installed Chrome.
// usage: node tools/capture.mjs <page.html|url> <out.png> <viewport-w> <viewport-h>
// Use it to proof a card, an end frame or a storyboard page at 1:1 before it goes into the cut.
// Chrome: $CHROME, else the default macOS / Linux install path.
if (process.argv.length < 6 || process.argv.includes('--help')) {
  console.log('usage: node tools/capture.mjs <page.html|url> <out.png> <viewport-w> <viewport-h>  (set CHROME to the browser binary)');
  process.exit(process.argv.includes('--help') ? 0 : 1);
}
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
const [src, out, W, H] = process.argv.slice(2);
const CEILING = 16384; // Chrome's capture ceiling; past it a render is not trustworthy.
const url = /^[a-z]+:\/\//.test(src) ? src : 'file://' + resolve(src);
const die = (m) => { console.error('CAPTURE FAILED: ' + m); process.exit(1); };
const nap = (ms) => new Promise((r) => setTimeout(r, ms));
// An isolated profile: Chrome writes DevToolsActivePort into it, and Browser.close below
// must never reach the user's own browser.
const dir = mkdtempSync(join(tmpdir(), 'fleet-capture-'));
const chrome = process.env.CHROME || (process.platform === 'darwin'
  ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : 'google-chrome');
spawn(chrome,
  ['--headless', '--remote-debugging-port=0', `--user-data-dir=${dir}`, '--hide-scrollbars',
    `--window-size=${W},${H}`, '--force-device-scale-factor=1', '--no-first-run',
    '--no-default-browser-check', '--run-all-compositor-stages-before-draw', 'about:blank'],
  { stdio: 'ignore' });
let port, wsPath;
for (let i = 0; i < 150 && !port; i++) {
  await nap(100);
  if (!existsSync(join(dir, 'DevToolsActivePort'))) continue;
  const [p, w] = readFileSync(join(dir, 'DevToolsActivePort'), 'utf8').split('\n');
  if (p && w) { port = p.trim(); wsPath = w.trim(); }
}
if (!port) die('Chrome never opened a DevTools port');
const ws = new WebSocket(`ws://127.0.0.1:${port}${wsPath}`);
await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(); }).catch(() => die('no DevTools socket'));
let n = 0; const calls = new Map(); const waits = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (calls.has(m.id)) { calls.get(m.id)(m.result || {}); calls.delete(m.id); }
  for (let i = waits.length - 1; i >= 0; i--) if (waits[i].m === m.method) { waits[i].ok(); waits.splice(i, 1); }
};
const cmd = (method, params, sessionId) => new Promise((ok) => {
  const id = ++n; calls.set(id, ok);
  ws.send(JSON.stringify({ id, method, params: params || {}, ...(sessionId ? { sessionId } : {}) }));
});
const evt = (m, ms) => Promise.race([new Promise((ok) => waits.push({ m, ok })), nap(ms)]);
const tgt = await cmd('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await cmd('Target.attachToTarget', { targetId: tgt.targetId, flatten: true });
await cmd('Page.enable', {}, sessionId);
// Headless Chrome on macOS will not size a window under 500px wide, so a 390px --window-size lays the page out at 500
// and the capture crops it. Pin the layout viewport to the requested size.
await cmd('Emulation.setDeviceMetricsOverride', { width: Number(W), height: Number(H), deviceScaleFactor: 1, mobile: false }, sessionId);
const loaded = evt('Page.loadEventFired', 30000);
await cmd('Page.navigate', { url }, sessionId);
await loaded;
await nap(3000); // the settle: fonts, entrance animations, a big base64 hero
const { cssContentSize: page } = await cmd('Page.getLayoutMetrics', {}, sessionId);
if (!page) die('Chrome reported no layout metrics');
const full = Math.ceil(page.height);
const wide = Math.ceil(page.width) > Number(W);
const height = Math.min(full, CEILING);
const shot = await cmd('Page.captureScreenshot',
  { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: Number(W), height, scale: 1 } }, sessionId);
await cmd('Browser.close'); // Chrome exits over the protocol, never by signal
if (!shot.data) die('Chrome returned no image');
writeFileSync(out, Buffer.from(shot.data, 'base64'));
// Trust the FILE, not the request: re-read the PNG header and fail loudly on any mismatch,
// so a silent truncation can never be handed over as a finished render.
const png = readFileSync(out);
const got = [png.readUInt32BE(16), png.readUInt32BE(20)];
if (got[0] !== Number(W) || got[1] !== height) die(`wrote ${got[0]}x${got[1]}, expected ${W}x${height}`);
if (wide) console.error(`WARNING: content is ${Math.ceil(page.width)}px wide at a ${W}px viewport (horizontal overflow).`);
console.log(`${out}: ${got[0]}x${got[1]} (page ${Math.ceil(page.width)}x${full}, viewport ${W}x${H})`);
if (full > CEILING) {
  console.error(`TRUNCATED: the page is ${full}px tall, past Chrome's ${CEILING}px capture ceiling; ` +
    `only the top ${CEILING}px is in this render. SAY SO in your final message and name what is missing.`);
  process.exit(2);
}
