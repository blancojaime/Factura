// Convierte los manuales (Markdown simple) a .docx con docx-js.
// Uso: node md2docx.js ../MANUAL_USUARIO.md ../MANUAL_USUARIO.docx "SIC-MUNI - Manual de Usuario"
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, LevelFormat, BorderStyle, Footer, PageNumber, PageBreak, TabStopType
} = require('docx');

const [,, inFile, outFile, footerTitle] = process.argv;
const lines = fs.readFileSync(inFile, 'utf8').replace(/\r\n/g, '\n').split('\n');
const FONT = 'Calibri', MONO = 'Consolas', BLUE = '1F4E79', GRAY = 'F2F2F2', TOTAL = 9360;

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const tok = m[0];
    if (tok.startsWith('**')) out.push(new TextRun({ text: tok.slice(2, -2), bold: true, font: FONT, ...base }));
    else out.push(new TextRun({ text: tok.slice(1, -1), font: MONO, size: (base.size || 22) - 2, shading: { type: ShadingType.CLEAR, fill: 'EDEDED' }, color: base.color }));
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  if (!out.length) out.push(new TextRun({ text: '', font: FONT, ...base }));
  return out;
}

const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const borders = { top: border, bottom: border, left: border, right: border };

function buildTable(rows) {
  const cells = rows.map(r => r.replace(/^\|/, '').replace(/\|\s*$/, '').split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, '|')));
  const header = cells[0];
  const body = cells.slice(2); // salta fila separadora
  const n = header.length;
  const maxLen = header.map((_, i) => Math.max(...[header[i], ...body.map(r => r[i] || '')].map(t => t.replace(/[`*]/g, '').length)));
  let w = maxLen.map(l => Math.min(Math.max(l, 8), 60));
  const sum = w.reduce((a, b) => a + b, 0);
  let widths = w.map(x => Math.max(900, Math.round(x / sum * TOTAL)));
  const diff = TOTAL - widths.reduce((a, b) => a + b, 0);
  widths[widths.indexOf(Math.max(...widths))] += diff;
  const mkCell = (txt, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: head ? { type: ShadingType.CLEAR, fill: BLUE } : undefined,
    children: [new Paragraph({ spacing: { after: 0 }, children: runs(txt, head ? { bold: true, color: 'FFFFFF', size: 19 } : { size: 19 }) })]
  });
  return new Table({
    width: { size: TOTAL, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: header.map((t, i) => mkCell(t, i, true)) }),
      ...body.map(r => new TableRow({ cantSplit: true, children: Array.from({ length: n }, (_, i) => mkCell(r[i] || '', i, false)) }))
    ]
  });
}

const children = [];
const numberingConfigs = [{
  reference: 'bullets',
  levels: [0, 1, 2].map(l => ({ level: l, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540 + l * 360, hanging: 270 } } } }))
}];
let olCount = 0;
const toc = [];

let i = 0;
// Portada: primer H1 + líneas hasta el primer '---'
let title = '', subs = [];
while (i < lines.length && !lines[i].startsWith('# ')) i++;
title = lines[i].slice(2).trim(); i++;
while (i < lines.length && lines[i].trim() !== '---') { if (lines[i].trim()) subs.push(lines[i].trim()); i++; }
i++;
children.push(new Paragraph({ spacing: { before: 3200, after: 240 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: title, bold: true, size: 56, color: BLUE, font: FONT })] }));
subs.forEach((s, k) => children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
  children: [new TextRun({ text: s, size: k === 0 ? 30 : 22, color: k === 0 ? '404040' : '7F7F7F', font: FONT })] })));
children.push(new Paragraph({ children: [new PageBreak()] }));

// Contenido (lista estática de secciones)
const h2s = lines.filter(l => l.startsWith('## ')).map(l => l.slice(3).trim());
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: 'Contenido', font: FONT })] }));
h2s.forEach(h => children.push(new Paragraph({ spacing: { after: 60 }, indent: { left: 360 }, children: [new TextRun({ text: h, font: FONT, size: 22 })] })));
children.push(new Paragraph({ children: [new PageBreak()] }));

while (i < lines.length) {
  const line = lines[i];
  if (!line.trim() || line.trim() === '---') { i++; continue; }
  if (line.startsWith('```')) {
    const code = []; i++;
    while (i < lines.length && !lines[i].startsWith('```')) { code.push(lines[i]); i++; }
    i++;
    code.forEach((c, k) => children.push(new Paragraph({ spacing: { after: 0 },
      shading: { type: ShadingType.CLEAR, fill: GRAY },
      border: { left: { style: BorderStyle.SINGLE, size: 12, color: BLUE, space: 6 } },
      children: [new TextRun({ text: c.length ? c : ' ', font: MONO, size: 18 })] })));
    children.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    continue;
  }
  if (line.startsWith('## ')) { children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: false, children: [new TextRun({ text: line.slice(3).trim(), font: FONT })] })); i++; continue; }
  if (line.startsWith('### ')) { children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: line.slice(4).trim(), font: FONT })] })); i++; continue; }
  if (line.startsWith('#### ')) { children.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: line.slice(5).trim(), font: FONT })] })); i++; continue; }
  if (line.startsWith('|')) {
    const rows = [];
    while (i < lines.length && lines[i].startsWith('|')) { rows.push(lines[i]); i++; }
    children.push(buildTable(rows));
    children.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
    continue;
  }
  if (line.startsWith('> ')) {
    const q = [];
    while (i < lines.length && lines[i].startsWith('> ')) { q.push(lines[i].slice(2)); i++; }
    children.push(new Paragraph({ spacing: { before: 80, after: 160 },
      shading: { type: ShadingType.CLEAR, fill: 'E8F1FA' },
      border: { left: { style: BorderStyle.SINGLE, size: 18, color: BLUE, space: 8 } },
      indent: { left: 200 }, children: runs(q.join(' '), { size: 21 }) }));
    continue;
  }
  let m;
  if ((m = line.match(/^(\s*)- (.*)$/))) {
    const lvl = Math.min(2, Math.floor(m[1].length / 2));
    children.push(new Paragraph({ numbering: { reference: 'bullets', level: lvl }, spacing: { after: 60 }, children: runs(m[2]) }));
    i++; continue;
  }
  if ((m = line.match(/^(\s*)\d+\. (.*)$/))) {
    const ref = 'ol' + (++olCount);
    numberingConfigs.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] });
    while (i < lines.length && (m = lines[i].match(/^(\s*)\d+\. (.*)$/))) {
      children.push(new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60 }, children: runs(m[2]) }));
      i++;
      // sub-bullets pertenecen a la lista
      while (i < lines.length && /^\s+- /.test(lines[i])) {
        const mm = lines[i].match(/^(\s*)- (.*)$/);
        children.push(new Paragraph({ numbering: { reference: 'bullets', level: 1 }, spacing: { after: 40 }, children: runs(mm[2]) }));
        i++;
      }
    }
    children.push(new Paragraph({ spacing: { after: 80 }, children: [] }));
    continue;
  }
  children.push(new Paragraph({ spacing: { after: 140 }, children: runs(line.trim()) }));
  i++;
}

const doc = new Document({
  creator: 'SIC-MUNI', title: footerTitle,
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, color: BLUE, font: FONT }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0, keepNext: true } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, color: '2E75B6', font: FONT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 23, bold: true, color: '404040', font: FONT }, paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2, keepNext: true } }
    ]
  },
  numbering: { config: numberingConfigs },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, right: 1440, bottom: 1300, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF', space: 4 } },
      children: [new TextRun({ text: footerTitle, size: 17, color: '7F7F7F', font: FONT }),
                 new TextRun({ text: '\tPágina ', size: 17, color: '7F7F7F', font: FONT }),
                 new TextRun({ children: [PageNumber.CURRENT], size: 17, color: '7F7F7F', font: FONT })] })] }) },
    children
  }]
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(outFile, b); console.log('OK', outFile, b.length); });
