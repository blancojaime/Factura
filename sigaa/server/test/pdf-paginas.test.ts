import { describe, it, expect } from 'vitest';
import { PdfDoc } from '../src/pdf/builder.js';

const paginas = (b: Buffer) => (b.toString('latin1').match(/\/Type \/Page[^s]/g) ?? []).length;
const cab = { entidad: 'ENTIDAD DE PRUEBA', subtitulo: '', unidad: '', gestion: 2026 } as any;

describe('PDF: sin hojas en blanco de más', () => {
  it('un documento corto tiene exactamente 1 página', async () => {
    const pdf = new PdfDoc({ titulo: 'Documento corto', header: cab } as any);
    pdf.parrafo('Contenido de una sola hoja.');
    expect(paginas(await pdf.buffer())).toBe(1);
  });
  it('un documento horizontal corto también', async () => {
    const pdf = new PdfDoc({ titulo: 'Horizontal', landscape: true, header: cab } as any);
    pdf.parrafo('Contenido.');
    expect(paginas(await pdf.buffer())).toBe(1);
  });
  it('un documento largo tiene tantas páginas como contenido, sin duplicarlas', async () => {
    const pdf = new PdfDoc({ titulo: 'Largo', header: cab } as any);
    for (let i = 0; i < 120; i++) pdf.parrafo(`Línea ${i}`);
    const n = paginas(await pdf.buffer());
    expect(n).toBeGreaterThan(1);
    expect(n).toBeLessThan(8);
  });
});
