// Utilidades de captura compartidas (Playwright). Las imágenes se guardan en tools/manuales/img/
const { chromium } = require(process.env.PW || '/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
const IMG = path.join(__dirname, 'img') + '/';
const B = process.env.BASE || 'http://127.0.0.1:8080';
const PW = 'Demo12345';
let browser;
async function launch() { browser = await chromium.launch(); return browser; }
async function marcar(p, marks) {
  await p.evaluate((ms) => { ms.forEach(([sel, n, txt]) => {
    let els = Array.from(document.querySelectorAll(sel)); if (txt) els = els.filter(e => e.textContent.includes(txt)); const el = els[0]; if (!el) return;
    const r = el.getBoundingClientRect(), x = r.left + scrollX, y = r.top + scrollY;
    const b = document.createElement('div'); b.style.cssText = `position:absolute;left:${x - 3}px;top:${y - 3}px;width:${r.width + 6}px;height:${r.height + 6}px;border:3px solid #e03131;border-radius:6px;pointer-events:none;z-index:99999`;
    const c = document.createElement('div'); c.textContent = n; c.style.cssText = `position:absolute;left:${Math.max(2, x - 14)}px;top:${Math.max(2, y - 14)}px;width:28px;height:28px;border-radius:50%;background:#e03131;color:#fff;font:700 16px sans-serif;display:flex;align-items:center;justify-content:center;z-index:100000;pointer-events:none;box-shadow:0 1px 3px rgba(0,0,0,.5)`;
    b.dataset.marca = c.dataset.marca = '1'; document.body.append(b, c); }); }, marks || []);
}
async function shot(p, name, o = {}) {
  await p.waitForLoadState('domcontentloaded'); await p.waitForTimeout(300);
  if (o.marks) await marcar(p, o.marks);
  const h = await p.evaluate(() => document.documentElement.scrollHeight);
  const y = o.fondo ? Math.max(0, h - (o.alto || 900)) : (o.y || 0);
  await p.screenshot({ path: `${IMG}${name}.jpg`, type: 'jpeg', quality: 82, fullPage: true, clip: { x: 0, y, width: 1200, height: Math.min(h - y, o.alto || 900) } });
  await p.evaluate(() => document.querySelectorAll('[data-marca]').forEach(e => e.remove()));
  console.log('  img', name);
}
async function shotEl(p, sel, name, o = {}) {
  await p.waitForTimeout(500); if (o.marks) await marcar(p, o.marks);
  const el = p.locator(sel).nth(o.nth || 0); const bb = await el.boundingBox(); const pad = 12;
  await p.screenshot({ path: `${IMG}${name}.jpg`, type: 'jpeg', quality: 85, fullPage: true, clip: { x: Math.max(0, bb.x - pad), y: Math.max(0, bb.y - pad), width: bb.width + 2 * pad, height: Math.min(bb.height + 2 * pad, o.alto || 4000) } });
  await p.evaluate(() => document.querySelectorAll('[data-marca]').forEach(e => e.remove())); console.log('  img', name);
}
async function ses(base, login, pass = PW) {
  const c = await browser.newContext({ viewport: { width: 1200, height: 800 } }); const p = await c.newPage(); p.setDefaultTimeout(15000);
  await p.route(/cdnjs/, r => r.abort()); p.on('dialog', d => d.accept()); p.on('pageerror', e => console.log('pageerror', e.message)); p.base = base || B;
  if (login) { await p.goto(p.base + '/index.php?r=auth/login', { waitUntil: 'domcontentloaded' }); await p.fill('[name=login]', login); await p.fill('[name=password]', pass); await p.click('button.btn.primary'); await p.waitForLoadState('domcontentloaded'); }
  return p;
}
const go = (p, r) => p.goto(`${p.base}/index.php?r=${r}`, { waitUntil: 'domcontentloaded' });
const optLabel = async (p, sel, txt) => p.locator(`${sel} option`, { hasText: txt }).first().textContent();
const pdf = async (p, file) => { await p.waitForTimeout(600); await p.pdf({ path: file, format: 'Letter', printBackground: true, preferCSSPageSize: true }); };
const close = async () => browser && browser.close();
module.exports = { launch, ses, go, shot, shotEl, marcar, optLabel, pdf, close, fs, path, IMG, B, PW, dir: __dirname };
