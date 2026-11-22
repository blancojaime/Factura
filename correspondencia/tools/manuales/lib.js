// Mini-biblioteca para generar los manuales (.docx) con docx-js. Índice estático en 2 pasadas (igual en Word y PDF).
const D = require('/opt/node-tools/node_modules/docx'); const fs = require('fs'), path = require('path'); const { execSync } = require('child_process');
const IMG = path.join(__dirname, 'img') + '/';
const COL = { azul: '16457A', gris: '555555', claro: 'EAF1F8' };
const runs = (t, o = {}) => String(t).split(/(\*\*[^*]+\*\*)/).filter(Boolean).map(s => s.startsWith('**') ? new D.TextRun({ text: s.slice(2, -2), bold: true, ...o }) : new D.TextRun({ text: s, ...o }));
const content = []; // acumulador
const api = {
  h1: t => content.push(['h1', t]), h2: t => content.push(['h2', t]), h3: t => content.push(['h3', t]), p: t => content.push(['p', t]),
  ul: a => content.push(['ul', a]), ol: a => content.push(['ol', a]), note: (k, t) => content.push(['note', k, t]),
  img: (f, c, w) => content.push(['img', f, c, w]), table: (h, r, w) => content.push(['table', h, r, w]), pb: () => content.push(['pb']),
  check: (items) => content.push(['check', items]),
};
function imgSize(f, maxW) { const [w, h] = execSync(`identify -format "%w %h" "${IMG + f}"`).toString().split(' ').map(Number); const W = Math.min(maxW || 600, 600); return { width: W, height: Math.round(W * h / w) }; }
const NOTE = { tip: ['💡 Consejo', 'E8F5E9', '2E7D32'], warn: ['⚠ Cuidado', 'FFF4E5', 'C25E00'], info: ['ℹ Recuerde', 'E8F1FB', '16457A'], ok: ['✔ Resultado esperado', 'EAF7EE', '1F6F3D'] };
const bdr = { style: D.BorderStyle.SINGLE, size: 4, color: 'BBBBBB' }; const bds = { top: bdr, bottom: bdr, left: bdr, right: bdr };
function build(cfg, tocPages) {
  const kids = []; let ol = 0; const heads = [];
  const num = (ref, inst) => ({ numbering: { reference: ref, level: 0 } });
  // portada
  kids.push(new D.Paragraph({ spacing: { before: 2400 }, alignment: D.AlignmentType.CENTER, children: [new D.TextRun({ text: cfg.entidad, size: 28, color: COL.gris })] }));
  kids.push(new D.Paragraph({ spacing: { before: 600, after: 200 }, alignment: D.AlignmentType.CENTER, children: [new D.TextRun({ text: cfg.titulo, size: 60, bold: true, color: COL.azul })] }));
  kids.push(new D.Paragraph({ alignment: D.AlignmentType.CENTER, spacing: { after: 400 }, children: [new D.TextRun({ text: cfg.subtitulo, size: 30, color: COL.gris })] }));
  if (cfg.portada) kids.push(new D.Paragraph({ alignment: D.AlignmentType.CENTER, spacing: { after: 300 }, children: [new D.ImageRun({ type: 'jpg', data: fs.readFileSync(IMG + cfg.portada), transformation: imgSize(cfg.portada, 520) })] }));
  kids.push(new D.Paragraph({ alignment: D.AlignmentType.CENTER, children: [new D.TextRun({ text: `Versión ${cfg.version} · ${cfg.fecha}`, size: 24, bold: true })] }));
  kids.push(new D.Paragraph({ alignment: D.AlignmentType.CENTER, spacing: { before: 200 }, children: [new D.TextRun({ text: cfg.lema, size: 20, italics: true, color: COL.gris })] }));
  kids.push(new D.Paragraph({ children: [new D.PageBreak()] }));
  // índice
  kids.push(new D.Paragraph({ spacing: { after: 200 }, children: [new D.TextRun({ text: 'Contenido', size: 36, bold: true, color: COL.azul })] }));
  const tocIdx = kids.length;
  const tocSlot = [];
  kids.push(new D.Paragraph({ children: [new D.PageBreak()] }));
  let fig = 0;
  for (const it of content) {
    const [k] = it;
    if (k === 'h1') { heads.push([1, it[1]]); kids.push(new D.Paragraph({ heading: D.HeadingLevel.HEADING_1, pageBreakBefore: heads.filter(h => h[0] === 1).length > 1, children: [new D.TextRun(it[1])] })); }
    else if (k === 'h2') { heads.push([2, it[1]]); kids.push(new D.Paragraph({ heading: D.HeadingLevel.HEADING_2, children: [new D.TextRun(it[1])] })); }
    else if (k === 'h3') kids.push(new D.Paragraph({ heading: D.HeadingLevel.HEADING_3, children: [new D.TextRun(it[1])] }));
    else if (k === 'p') kids.push(new D.Paragraph({ spacing: { after: 120, line: 300 }, children: runs(it[1]) }));
    else if (k === 'ul') it[1].forEach(t => kids.push(new D.Paragraph({ numbering: { reference: 'bul', level: 0 }, spacing: { after: 60 }, children: runs(t) })));
    else if (k === 'ol') { ol++; it[1].forEach(t => kids.push(new D.Paragraph({ numbering: { reference: 'ol' + ol, level: 0 }, spacing: { after: 80 }, children: runs(t) }))); }
    else if (k === 'note') { const [tt, bg, fg] = NOTE[it[1]]; kids.push(new D.Table({ width: { size: 9360, type: D.WidthType.DXA }, columnWidths: [9360], rows: [new D.TableRow({ children: [new D.TableCell({ width: { size: 9360, type: D.WidthType.DXA }, shading: { fill: bg, type: D.ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 140, right: 140 }, borders: { top: { style: D.BorderStyle.NONE }, bottom: { style: D.BorderStyle.NONE }, right: { style: D.BorderStyle.NONE }, left: { style: D.BorderStyle.SINGLE, size: 24, color: fg } }, children: [new D.Paragraph({ children: [new D.TextRun({ text: tt + ': ', bold: true, color: fg }), ...runs(it[2])] })] })] })] })); kids.push(new D.Paragraph({ spacing: { after: 80 }, children: [] })); }
    else if (k === 'img') { fig++; kids.push(new D.Paragraph({ alignment: D.AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 }, children: [new D.ImageRun({ type: it[1].endsWith('png') ? 'png' : 'jpg', data: fs.readFileSync(IMG + it[1]), transformation: imgSize(it[1], it[3]) })] })); kids.push(new D.Paragraph({ alignment: D.AlignmentType.CENTER, spacing: { after: 160 }, children: [new D.TextRun({ text: `Figura ${fig}. ${it[2]}`, italics: true, size: 18, color: COL.gris })] })); }
    else if (k === 'table') { const [, h, rows, w] = it; const tot = 9360; const ws = w || h.map(() => Math.floor(tot / h.length)); const cell = (t, i, head) => new D.TableCell({ width: { size: ws[i], type: D.WidthType.DXA }, borders: bds, margins: { top: 60, bottom: 60, left: 90, right: 90 }, shading: head ? { fill: COL.azul, type: D.ShadingType.CLEAR } : undefined, children: [new D.Paragraph({ children: runs(t, head ? { bold: true, color: 'FFFFFF', size: 19 } : { size: 19 }) })] }); kids.push(new D.Table({ width: { size: ws.reduce((a, b) => a + b, 0), type: D.WidthType.DXA }, columnWidths: ws, rows: [new D.TableRow({ tableHeader: true, children: h.map((t, i) => cell(t, i, true)) }), ...rows.map(r => new D.TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i)) }))] })); kids.push(new D.Paragraph({ spacing: { after: 120 }, children: [] })); }
    else if (k === 'check') it[1].forEach(t => kids.push(new D.Paragraph({ spacing: { after: 70 }, indent: { left: 360, hanging: 360 }, children: [new D.TextRun({ text: '☐  ', size: 26 }), ...runs(t)] })));
    else if (k === 'pb') kids.push(new D.Paragraph({ children: [new D.PageBreak()] }));
  }
  // índice estático
  const toc = heads.filter(h => h[0] <= 2).map(([lv, t]) => new D.Paragraph({ tabStops: [{ type: D.TabStopType.RIGHT, position: 9360, leader: D.LeaderType.DOT }], indent: { left: lv === 2 ? 360 : 0 }, spacing: { after: lv === 1 ? 60 : 20, before: lv === 1 ? 100 : 0 }, children: [new D.TextRun({ text: t, bold: lv === 1, size: lv === 1 ? 22 : 20 }), new D.TextRun({ text: '\t' + ((tocPages && tocPages[t]) || '0'), size: 20 })] }));
  kids.splice(tocIdx, 0, ...toc);
  const nb = (ref) => ({ reference: ref, levels: [{ level: 0, format: D.LevelFormat.DECIMAL, text: '%1.', alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] });
  const doc = new D.Document({
    creator: 'Sistema de Correspondencia', title: cfg.titulo,
    styles: { default: { document: { run: { font: 'Arial', size: 22 } } }, paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 36, bold: true, color: COL.azul, font: 'Arial' }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 28, bold: true, color: '1F5FA0', font: 'Arial' }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 24, bold: true, color: '333333', font: 'Arial' }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2, keepNext: true } }] },
    numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: D.LevelFormat.BULLET, text: '•', alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }, ...Array.from({ length: 400 }, (_, i) => nb('ol' + (i + 1)))] },
    sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1260, right: 1440, bottom: 1260, left: 1440 } } },
      footers: { default: new D.Footer({ children: [new D.Paragraph({ alignment: D.AlignmentType.CENTER, children: [new D.TextRun({ text: `${cfg.titulo} · v${cfg.version} · Página `, size: 16, color: '777777' }), new D.TextRun({ children: [D.PageNumber.CURRENT], size: 16, color: '777777' })] })] }) },
      children: kids }] });
  return { doc, heads };
}
async function generar(cfg, out) {
  const pack = async (pages) => { const { doc, heads } = build(cfg, pages); fs.writeFileSync(out, await D.Packer.toBuffer(doc)); return heads; };
  let heads = await pack(null);
  const pdfOf = () => { execSync(`soffice --headless --convert-to pdf --outdir "${path.dirname(out)}" "${out}" >/dev/null 2>&1`); return out.replace(/\.docx$/, '.pdf'); };
  const pageMap = (pdf) => { const n = Number(execSync(`pdfinfo "${pdf}" | grep Pages | awk '{print $2}'`).toString()); const map = {}; const txt = []; for (let i = 1; i <= n; i++) txt.push(execSync(`pdftotext -f ${i} -l ${i} -layout "${pdf}" -`).toString()); let start = 0; txt.forEach((t, i) => { if ((t.match(/\.{4,}/g) || []).length >= 5) start = i + 1; }); // salta portada e índice
    let from = 0; for (const [, t] of heads) { for (let i = Math.max(from, start); i < n; i++) { if (txt[i].replace(/\s+/g, ' ').includes(t.replace(/\s+/g, ' '))) { map[t] = i + 1; from = i; break; } } } return { map, n }; };
  let pdf = pdfOf(); let { map } = pageMap(pdf); await pack(map); pdf = pdfOf(); ({ map } = pageMap(pdf)); await pack(map); pdf = pdfOf();
  const n = execSync(`pdfinfo "${pdf}" | grep Pages | awk '{print $2}'`).toString().trim(); console.log('OK', out, n, 'páginas');
}
module.exports = { ...api, generar, content };
