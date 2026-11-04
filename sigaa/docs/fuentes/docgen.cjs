/* Generador de manuales: node docgen.cjs contenido.json "Pie de página"  → .docx y .pdf junto al JSON (rutas en el JSON) */
const fs = require('fs'), path = require('path');
const D = require('/opt/node-tools/node_modules/docx');
const { chromium } = require('/opt/node-tools/node_modules/playwright-core');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType, ImageRun, Footer, PageNumber, BorderStyle, PageBreak } = D;
const [, , jsonPath, pie = 'SIGAA'] = process.argv;
const PLAIN = !!process.env.PLAIN, NOPDF = !!process.env.NOPDF;
const C = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
const IMG = path.join(__dirname, 'img') + '/';
const out = path.resolve(path.dirname(path.resolve(jsonPath)), '..', C.out);
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const inl = (s) => esc(s).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\*([^*]+)\*/g, '<i>$1</i>').replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\[\[([^\]]+)\]\]/g, '<mark>$1</mark>');
const AZ = '1F3A5F';
// ───── HTML
let h = `<html><head><meta charset="utf-8"><style>
@page{size:A4;margin:16mm 15mm}
body{font-family:"Liberation Sans",Arial,sans-serif;font-size:10.5pt;line-height:1.4;color:#1b2330}
h1{font-size:18pt;color:#${AZ};border-bottom:2px solid #${AZ};padding-bottom:3px;margin:18px 0 8px;page-break-after:avoid}
h2{font-size:13pt;color:#${AZ};margin:14px 0 5px;page-break-after:avoid}
p{margin:4px 0 6px} ul,ol{margin:3px 0 8px 20px;padding-left:6px} li{margin:2px 0}
table{border-collapse:collapse;width:100%;margin:6px 0 10px} tr{page-break-inside:avoid}
td,th{border:1px solid #8a94a3;padding:3px 6px;font-size:9.5pt;vertical-align:top} th{background:#dde6f0;text-align:left}
code{font-family:"Liberation Mono",monospace;background:#eef1f5;padding:0 3px;font-size:9.5pt}
.note{border-left:5px solid var(--c);background:#f5f7fa;padding:6px 10px;margin:8px 0;page-break-inside:avoid} .note b.t{display:block;color:var(--c)}
.fig{text-align:center;margin:8px 0 10px;page-break-inside:avoid} .fig img{max-width:100%;max-height:140mm;border:1px solid #b9c2cf;border-radius:3px} .fig.s img{max-width:70%} .cap{font-size:8.8pt;color:#566174}
.cover{height:240mm;page-break-after:always;display:flex;flex-direction:column;justify-content:center;border-left:10px solid #${AZ};padding-left:14mm} .cover h1{font-size:30pt;border:0;margin:0 0 6px} .cover .sub{font-size:14pt;color:#566174;margin-bottom:14mm}
.cover p{font-size:11pt;max-width:150mm}
.pb{page-break-before:always}
mark{background:#fff2a8;padding:0 2px}
.mem{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #4f7a1e;padding-bottom:6px;margin-bottom:14px}.mem img{height:22mm}
.sig{margin-top:34px;text-align:center;page-break-inside:avoid}.sig .l{border-top:1px solid #333;width:230px;margin:0 auto 4px}.sigs{display:flex;justify-content:space-around;gap:20px}
.al-r{text-align:right}.al-c{text-align:center}.al-j{text-align:justify}
.logos{display:flex;gap:24px;align-items:center;margin-bottom:12mm}.logos img{height:26mm}
</style></head><body>`;
const NOTE = { ok: '17693F', warn: 'A85A0B', '': '1F4E8C' };
const B = C.bloques;
for (const b of B) {
  switch (b.t) {
    case 'membrete': h += `<div class="mem">${(b.logos || []).map((l) => `<img src="data:image/jpeg;base64,${fs.readFileSync(IMG + l).toString('base64')}">`).join('')}</div>`; break;
    case 'sig': h += `<div class="sigs">${b.firmas.map((f) => `<div class="sig"><div class="l"></div>${f.map((x, i) => i === 0 ? `<b>${esc(x)}</b>` : `<div>${esc(x)}</div>`).join('')}</div>`).join('')}</div>`; break;
    case 'cover': h += `<div class="cover">${b.logos ? `<div class="logos">${b.logos.map((l) => `<img src="data:image/jpeg;base64,${fs.readFileSync(IMG + l).toString('base64')}">`).join('')}</div>` : ''}<h1>${esc(b.title)}</h1><div class="sub">${esc(b.sub)}</div>${(b.lines || []).map((l) => `<p>${inl(l)}</p>`).join('')}</div>`; break;
    case 'h1': h += `<h1 ${b.pb ? 'class="pb"' : ''}>${esc(b.x)}</h1>`; break;
    case 'h2': h += `<h2>${esc(b.x)}</h2>`; break;
    case 'p': h += `<p class="${b.align ? 'al-' + b.align : ''}">${inl(b.x)}</p>`; break;
    case 'ul': h += `<ul>${b.items.map((i) => `<li>${inl(i)}</li>`).join('')}</ul>`; break;
    case 'ol': h += `<ol>${b.items.map((i) => `<li>${inl(i)}</li>`).join('')}</ol>`; break;
    case 'table': h += `<table><tr>${b.head.map((x) => `<th>${inl(x)}</th>`).join('')}</tr>${b.rows.map((r) => `<tr>${r.map((x) => `<td>${inl(x)}</td>`).join('')}</tr>`).join('')}</table>`; break;
    case 'img': h += `<div class="fig ${b.size || ''}"><img src="data:image/jpeg;base64,${fs.readFileSync(IMG + b.src).toString('base64')}"><div class="cap">${inl(b.cap || '')}</div></div>`; break;
    case 'note': h += `<div class="note" style="--c:#${NOTE[b.kind || '']}">${b.title ? `<b class="t">${esc(b.title)}</b>` : ''}${inl(b.x)}</div>`; break;
  }
}
h += '</body></html>';
fs.writeFileSync(out + '.html', h);
// ───── DOCX
const runs = (s, o = {}) => {
  const parts = []; const re = /\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*|\[\[([^\]]+)\]\]/g; let last = 0, m;
  while ((m = re.exec(s))) { if (m.index > last) parts.push(new TextRun({ text: s.slice(last, m.index), ...o })); parts.push(new TextRun(m[1] ? { text: m[1], bold: true, ...o } : m[2] ? { text: m[2], font: 'Courier New', ...o } : m[3] ? { text: m[3], italics: true, ...o } : { text: m[4], highlight: 'yellow', ...o })); last = re.lastIndex; }
  if (last < s.length) parts.push(new TextRun({ text: s.slice(last), ...o })); return parts;
};
const cell = (x, head, w) => new TableCell({ width: { size: w, type: WidthType.PERCENTAGE }, shading: head ? { type: ShadingType.CLEAR, fill: 'DDE6F0' } : undefined, margins: { top: 40, bottom: 40, left: 80, right: 80 }, children: [new Paragraph({ children: runs(String(x), { size: 19, bold: head }) })] });
const kids = [];
const nums = [];
const dim = (f) => require('child_process').execSync(`identify -format "%w %h" "${IMG + f}"`).toString().split(' ').map(Number);
const imgRun = (f, h) => { const [w0, h0] = dim(f); return new ImageRun({ data: fs.readFileSync(IMG + f), transformation: { width: Math.round(h * w0 / h0), height: h }, type: 'jpg' }); };
const ALIGN = { r: AlignmentType.RIGHT, c: AlignmentType.CENTER, j: AlignmentType.JUSTIFIED };
for (const b of B) {
  switch (b.t) {
    case 'cover': if (PLAIN) break; if (b.logos) kids.push(new Paragraph({ spacing: { before: 600, after: 200 }, children: b.logos.flatMap((l, i) => [imgRun(l, 70), new TextRun({ text: '        ' })]) })); kids.push(new Paragraph({ spacing: { before: b.logos ? 1200 : 2600 }, children: [new TextRun({ text: b.title, bold: true, size: 56, color: AZ })] }), new Paragraph({ spacing: { after: 400 }, children: [new TextRun({ text: b.sub, size: 28, color: '566174' })] }), ...(b.lines || []).map((l) => new Paragraph({ spacing: { after: 120 }, children: runs(l, { size: 22 }) })), new Paragraph({ children: [new PageBreak()] })); break;
    case 'h1': kids.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, pageBreakBefore: !!b.pb, children: [new TextRun({ text: b.x, bold: true, size: 34, color: AZ })] })); break;
    case 'h2': kids.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 80 }, children: [new TextRun({ text: b.x, bold: true, size: 26, color: AZ })] })); break;
    case 'p': kids.push(new Paragraph({ spacing: { after: 100 }, alignment: b.align ? ALIGN[b.align[0]] : undefined, children: runs(b.x, { size: 21 }) })); break;
    case 'membrete': { const nb = { top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' } }; kids.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, borders: { ...nb, insideHorizontal: nb.top, insideVertical: nb.top }, rows: [new TableRow({ children: (b.logos || []).map((l, i, a) => new TableCell({ borders: nb, width: { size: Math.floor(100 / a.length), type: WidthType.PERCENTAGE }, children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT, children: [imgRun(l, 62)] })] })) })] }), new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: '4F7A1E', space: 4 } }, spacing: { after: 200 }, children: [] })); break; }
    case 'sig': { const nb = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }; kids.push(new Paragraph({ text: '', spacing: { before: 500 } }), new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, borders: { top: nb, bottom: nb, left: nb, right: nb, insideHorizontal: nb, insideVertical: nb }, rows: [new TableRow({ cantSplit: true, children: b.firmas.map((f) => new TableCell({ borders: { top: nb, bottom: nb, left: nb, right: nb }, width: { size: Math.floor(100 / b.firmas.length), type: WidthType.PERCENTAGE }, children: [new Paragraph({ alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 6, color: '333333', space: 4 } }, children: [new TextRun({ text: f[0], bold: true, size: 20 })] }), ...f.slice(1).map((x) => new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: x, size: 19 })] }))] })) })] })); break; }
    case 'ul': for (const i of b.items) kids.push(PLAIN ? new Paragraph({ indent: { left: 420, hanging: 260 }, spacing: { after: 40 }, children: [new TextRun({ text: '•  ', size: 21 }), ...runs(i, { size: 21 })] }) : new Paragraph({ bullet: { level: 0 }, spacing: { after: 40 }, children: runs(i, { size: 21 }) })); break;
    case 'ol': b.items.forEach((i, k) => kids.push(new Paragraph({ indent: { left: 420, hanging: 320 }, spacing: { after: 50 }, children: [new TextRun({ text: `${k + 1}.  `, bold: true, size: 21 }), ...runs(i, { size: 21 })] }))); break;
    case 'table': { const w = Math.floor(100 / b.head.length); kids.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: [new TableRow({ tableHeader: true, children: b.head.map((x) => cell(x, true, w)) }), ...b.rows.map((r) => new TableRow({ cantSplit: true, children: r.map((x) => cell(x, false, w)) }))] }), new Paragraph({ text: '' })); break; }
    case 'img': if (PLAIN) break; { const buf = fs.readFileSync(IMG + b.src); const dim = require('child_process').execSync(`identify -format "%w %h" "${IMG + b.src}"`).toString().split(' ').map(Number); let w = b.size === 's' ? 420 : 600; let hh = dim[1] * w / dim[0]; if (hh > 520) { w = w * 520 / hh; hh = 520; } kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80 }, children: [new ImageRun({ data: buf, transformation: { width: Math.round(w), height: Math.round(hh) }, type: 'jpg' })] }), new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 140 }, children: [new TextRun({ text: b.cap || '', italics: true, size: 17, color: '566174' })] })); break; }
    case 'note': { const col = NOTE[b.kind || '']; kids.push(new Paragraph({ spacing: { before: 80, after: 120 }, indent: { left: 200 }, border: { left: { style: BorderStyle.SINGLE, size: 24, color: col, space: 8 } }, shading: { type: ShadingType.CLEAR, fill: 'F5F7FA' }, children: [...(b.title ? [new TextRun({ text: b.title + '. ', bold: true, color: col, size: 21 })] : []), ...runs(b.x, { size: 21 })] })); break; }
  }
}
const doc = new Document({ sections: [{ properties: { page: { margin: { top: 900, bottom: 900, left: 900, right: 900 } } }, footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: pie + ' · Página ', size: 16, color: '566174' }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: '566174' })] })] }) }, children: kids }] });
(async () => {
  fs.writeFileSync(out + '.docx', await Packer.toBuffer(doc));
  if (NOPDF) { fs.unlinkSync(out + '.html'); console.log('ok (solo docx)', out); return; }
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox'] });
  const p = await b.newPage(); await p.goto('file://' + out + '.html'); await p.waitForTimeout(800);
  await p.pdf({ path: out + '.pdf', format: 'A4', margin: { top: '16mm', bottom: '17mm', left: '15mm', right: '15mm' }, printBackground: true, displayHeaderFooter: true, headerTemplate: '<span></span>', footerTemplate: `<div style="font-size:8px;color:#566174;width:100%;text-align:center;font-family:Arial">${pie} · Página <span class="pageNumber"></span> de <span class="totalPages"></span></div>` });
  await b.close(); fs.unlinkSync(out + '.html'); console.log('ok', out);
})();
