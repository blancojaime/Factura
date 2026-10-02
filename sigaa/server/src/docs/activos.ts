/** Documentos PDF de Activos Fijos: solicitud, memorándum de comisión, acta de conformidad, formulario de ingreso, asignación, ficha, movimientos y stickers. */
import PDFDocument from 'pdfkit';
import fs from 'node:fs';
import path from 'node:path';
import type { Db } from '../core/context.js';
import { fail, NotFound } from '../core/errors.js';
import { fmtDate, fmt2, literal, num, txt, today } from '../core/util.js';
import { cfgAll } from '../core/services.js';
import { PdfDoc, loadHeader } from '../pdf/builder.js';
import { obtenerActivo, obtenerAsignacion, obtenerIngresoAF, obtenerSolicitud } from '../modules/activos/service.js';
import { registrarDoc } from './types.js';

export const FOTOS_DIR = () => process.env.SIGAA_FOTOS_DIR || path.resolve(process.cwd(), 'data/fotos');

const nuevo = async (db: Db, titulo: string, nro?: string, subtitulo?: string, landscape = false) => new PdfDoc({ titulo, nro, subtitulo, landscape, header: await loadHeader(db, 'UnidadAF') });

registrarDoc(
  {
    id: 'af-solicitud', nombre: 'Solicitud de activos fijos', modulo: 'af', ref: 'Nº solicitud (SOL-…)',
    async build(db, nro) {
      const s = await obtenerSolicitud(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Solicitud de activos fijos', nro, `Estado: ${s.estado}`);
      pdf.kv([['Fecha', fmtDate(s.fecha)], ['Unidad solicitante', s.unidad], ['Funcionario solicitante', s.funcionario], ['Cargo', s.cargo], ['Aprobado por DAF', s.aprobado_daf], ['Acta(s) de asignación', s.nro_acta], ['Justificación', s.justificacion]]);
      pdf.espacio(4).tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Cuenta contable', w: 3 }, { header: 'Activo solicitado', w: 4 }, { header: 'Cantidad', w: 1, num: 'int' }, { header: 'Saldo en almacén', w: 1.2, num: 'int' }], s.items.map((x: any) => [x.item, x.cuenta, x.descripcion, x.cantidad, x.saldo]));
      pdf.firmas([{ nombre: s.funcionario, cargo: s.cargo, rol: 'SOLICITANTE' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo. DAF' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'af-memo-comision', nombre: 'Memorándum de designación de comisión de recepción', modulo: 'af', ref: 'Nº ingreso (ING-…)',
    async build(db, nro) {
      const i = await obtenerIngresoAF(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Memorándum de designación de comisión de recepción', i.nro_memo || nro);
      pdf.kv([['Lugar y fecha', `${c.Municipio}, ${fmtDate(i.fecha)}`], ['A', [i.comision1, i.comision2].filter(Boolean).join('\n')], ['De', `${c.NombreMAE} — ${c.CargoMAE}`], ['Referencia', `Designación de comisión de recepción — ${i.tipo_doc} ${txt(i.nro_doc)}`]], 1);
      pdf.parrafo(`Mediante el presente se les designa como COMISIÓN DE RECEPCIÓN de los bienes adquiridos mediante ${i.tipo_doc} Nº ${txt(i.nro_doc)} del proveedor ${txt(i.proveedor)}, debiendo verificar el cumplimiento de las especificaciones técnicas y suscribir el Acta de Conformidad.`);
      pdf.tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Descripción', w: 5 }, { header: 'Cantidad', w: 1, num: 'int' }], i.items.map((x: any) => [x.item, x.descripcion, x.cantidad]));
      pdf.firmas([{ nombre: c.NombreMAE, cargo: c.CargoMAE, rol: 'MÁXIMA AUTORIDAD EJECUTIVA' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'af-acta-conformidad', nombre: 'Acta de conformidad de recepción', modulo: 'af', ref: 'Nº ingreso (ING-…)',
    async build(db, nro) {
      const i = await obtenerIngresoAF(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Acta de conformidad de recepción de activos fijos', nro);
      pdf.parrafo(`En ${c.Municipio}, ${fmtDate(i.fecha)}, la comisión de recepción designada mediante ${txt(i.nro_memo) || 'memorándum'} verificó los bienes entregados por ${txt(i.proveedor)} (NIT ${txt(i.nit)}), con ${i.tipo_doc} Nº ${txt(i.nro_doc)} y factura ${txt(i.factura)}, y los recibe a su entera CONFORMIDAD.`);
      pdf.tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Descripción', w: 5 }, { header: 'Cant.', w: 0.8, num: 'int' }, { header: 'P. unit. (Bs)', w: 1.1, num: 'money' }, { header: 'Total (Bs)', w: 1.1, num: 'money' }], i.items.map((x: any) => [x.item, x.descripcion, x.cantidad, x.precio_unit, x.total]), { totales: ['', 'TOTAL', '', '', i.total] });
      pdf.parrafo(`Son: ${literal(num(i.total))}`, { bold: true, align: 'left' });
      pdf.firmas([{ nombre: i.comision1, rol: 'COMISIÓN DE RECEPCIÓN' }, { nombre: i.comision2, rol: 'COMISIÓN DE RECEPCIÓN' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'af-form-ingreso', nombre: 'Formulario de ingreso a almacén de activos fijos (con códigos)', modulo: 'af', ref: 'Nº ingreso (ING-…)',
    async build(db, nro) {
      const i = await obtenerIngresoAF(db, nro);
      const acts = await db('af_activos').where({ nro_ingreso: nro }).orderBy('codigo');
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Formulario de ingreso a almacén de activos fijos', nro, `Estado: ${i.estado}`, true);
      pdf.kv([['Fecha de recepción', fmtDate(i.fecha)], ['Tipo de ingreso', i.tipo_doc], ['Nº OC / contrato', i.nro_doc], ['Preventivo', i.preventivo], ['Proveedor', i.proveedor], ['NIT', i.nit], ['Factura', i.factura], ['Memorándum de comisión', i.nro_memo], ['Unidad', i.unidad], ['Fuente de financiamiento', i.fuente_fin], ['Observaciones', i.observaciones]]);
      pdf.seccion('Detalle del ingreso').tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Cuenta', w: 2.5 }, { header: 'Auxiliar', w: 2 }, { header: 'Descripción', w: 3.5 }, { header: 'Cant.', w: 0.7, num: 'int' }, { header: 'P. unit.', w: 1, num: 'money' }, { header: 'Total', w: 1.1, num: 'money' }, { header: 'Codificados', w: 0.9, num: 'int' }], i.items.map((x: any) => [x.item, x.cuenta, x.auxiliar, x.descripcion, x.cantidad, x.precio_unit, x.total, x.cant_codif]), { totales: ['', '', '', 'TOTAL', '', '', i.total, ''] });
      if (acts.length) pdf.seccion('Códigos asignados').tabla([{ header: 'Código', w: 1.5 }, { header: 'Descripción', w: 4 }, { header: 'Estado', w: 1 }, { header: 'Valor Bs', w: 1, num: 'money' }], acts.map((a: any) => [a.codigo, `${a.auxiliar} - ${a.descripcion}`, a.estado, a.valor]));
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }, { nombre: c.NombreCON, cargo: c.CargoCON, rol: 'CONTABILIDAD' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo. DAF' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'af-asignacion', nombre: 'Formulario de salida / acta de asignación de activos', modulo: 'af', ref: 'Nº acta (ASG-…)',
    async build(db, nro) {
      const a = await obtenerAsignacion(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Formulario de salida — Acta de asignación de activos fijos', nro, undefined, true);
      pdf.kv([['Fecha', fmtDate(a.fecha)], ['Solicitud', a.nro_sol], ['Servidor público', a.funcionario], ['CI', a.ci], ['Cargo', a.cargo], ['Unidad', a.unidad], ['Observaciones', a.observaciones]]);
      pdf.parrafo('El servidor público recibe los activos fijos detallados, se compromete a su custodia, buen uso y a no trasladarlos sin autorización del Responsable de Activos Fijos (Reglamento de Manejo de Bienes).', { size: 8.5 });
      pdf.tabla([{ header: 'Código', w: 1.5 }, { header: 'Auxiliar', w: 2 }, { header: 'Descripción', w: 3.5 }, { header: 'Marca', w: 1.2 }, { header: 'Modelo', w: 1.2 }, { header: 'Serie', w: 1.2 }, { header: 'Estado', w: 0.9 }, { header: 'Valor Bs', w: 1.1, num: 'money' }], a.activos.map((x: any) => [x.codigo, x.auxiliar, x.descripcion, x.marca, x.modelo, x.serie, x.estado, x.valor]), { totales: ['TOTAL', '', '', '', '', '', '', a.valor] });
      pdf.parrafo(`Son: ${literal(num(a.valor))}`, { bold: true, align: 'left' });
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'ENTREGA' }, { nombre: a.funcionario, cargo: a.cargo, rol: 'RECIBE CONFORME' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo. DAF' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'af-salida-sin-existencia', nombre: 'Formulario de salida con leyenda SIN EXISTENCIA', modulo: 'af', ref: 'Nº solicitud (SOL-…)',
    async build(db, nro) {
      const s = await obtenerSolicitud(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Formulario de salida — SIN EXISTENCIA', nro);
      pdf.aviso('SIN EXISTENCIA EN ALMACÉN');
      pdf.parrafo(`El Responsable de Activos Fijos certifica que, a la fecha, no existen en almacén los activos solicitados por ${s.funcionario} (${s.unidad}) mediante la solicitud ${nro}; corresponde a la unidad solicitante gestionar su adquisición.`);
      pdf.tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Cuenta contable', w: 3 }, { header: 'Activo solicitado', w: 4 }, { header: 'Cantidad', w: 1, num: 'int' }, { header: 'Saldo', w: 1, num: 'int' }], s.items.map((x: any) => [x.item, x.cuenta, x.descripcion, x.cantidad, x.saldo]));
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo. DAF' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'af-ficha', nombre: 'Ficha técnica del activo fijo', modulo: 'af', ref: 'Código del activo',
    async build(db, codigo) {
      const a = await obtenerActivo(db, codigo);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Ficha técnica del activo fijo', codigo);
      pdf.kv([['Descripción', a.descripcion], ['Estado físico', a.estado], ['Cuenta contable', a.cuenta], ['Valor (Bs)', fmt2(a.valor)], ['Auxiliar', a.auxiliar], ['Fecha de ingreso', fmtDate(a.fecha_ingreso)], ['Marca', a.marca], ['Modelo', a.modelo], ['Serie', a.serie], ['Color', a.color], ['Situación', a.situacion], ['Funcionario', a.funcionario], ['Ubicación actual', a.ubicacion_actual], ['Nº ingreso / acta', `${txt(a.nro_ingreso)} / ${txt(a.nro_acta)}`], ['Observaciones', a.observaciones]]);
      if (a.campos.length) pdf.seccion('Características técnicas').tabla([{ header: 'Característica', w: 3 }, { header: 'Detalle', w: 5 }], a.campos.map((x: any) => [x.campo, x.valor]));
      const fotos = [1, 2, 3, 4].map((n) => (a['foto' + n] ? path.join(FOTOS_DIR(), a['foto' + n]) : '')).filter((f) => f && fs.existsSync(f));
      if (fotos.length) {
        pdf.seccion('Registro fotográfico');
        const w = (pdf.width - 12) / 2;
        let col = 0;
        let y = pdf.doc.y;
        for (const f of fotos) {
          if (col === 0 && y + 150 > pdf.doc.page.height - 60) { pdf.doc.addPage(); y = 50; }
          try { pdf.doc.image(f, 36 + col * (w + 12), y, { fit: [w, 140], align: 'center' }); } catch { /* imagen inválida */ }
          col++;
          if (col === 2) { col = 0; y += 150; }
        }
        pdf.doc.y = y + (col ? 150 : 0);
      }
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'af-movimiento', nombre: 'Acta de devolución, transferencia o baja de activos', modulo: 'af', ref: 'Nº documento (DEV-/TRF-/BAJ-…)',
    async build(db, nro) {
      const rows = await db('af_movimientos as m').join('af_activos as a', 'a.codigo', 'm.codigo').where('m.documento', nro).whereIn('m.tipo', ['DEVOLUCIÓN', 'TRANSFERENCIA', 'BAJA']).select('m.*', 'a.descripcion', 'a.auxiliar', 'a.valor').orderBy('m.codigo');
      if (!rows.length) throw new NotFound(`No existe el movimiento ${nro}.`);
      const c = await cfgAll(db);
      const t = rows[0].tipo as string;
      const pdf = await nuevo(db, `Acta de ${t === 'DEVOLUCIÓN' ? 'devolución' : t === 'TRANSFERENCIA' ? 'transferencia' : 'baja'} de activos fijos`, nro, undefined, true);
      pdf.kv([['Fecha', fmtDate(rows[0].fecha)], ['Origen', rows[0].origen], ['Destino', rows[0].destino], ['Detalle / motivo', rows[0].detalle]]);
      pdf.espacio(4).tabla([{ header: 'Código', w: 1.5 }, { header: 'Auxiliar', w: 2 }, { header: 'Descripción', w: 4 }, { header: 'Valor Bs', w: 1.1, num: 'money' }], rows.map((x: any) => [x.codigo, x.auxiliar, x.descripcion, x.valor]), { totales: ['TOTAL', '', '', rows.reduce((s: number, x: any) => s + num(x.valor), 0)] });
      pdf.firmas(t === 'BAJA' ? [{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }, { nombre: c.NombreCON, cargo: c.CargoCON, rol: 'CONTABILIDAD' }, { nombre: c.NombreMAE, cargo: c.CargoMAE, rol: 'AUTORIZA' }] : [{ nombre: rows[0].origen, rol: t === 'DEVOLUCIÓN' ? 'DEVUELVE' : 'ENTREGA (ORIGEN)' }, { nombre: rows[0].destino, rol: 'RECIBE' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }]);
      return pdf.buffer();
    },
  },
);

/** Hoja de stickers (3 columnas × 10 filas por página carta): entidad, edificio, auxiliar y código del activo. */
export async function stickersPdf(db: Db, codigos: string[]): Promise<Buffer> {
  if (!codigos.length) fail('Marque con X los códigos que desea imprimir.');
  const c = await cfgAll(db);
  const acts = await db('af_activos as a').leftJoin('af_edificios as e', 'e.cod_edif', 'a.cod_edif').whereIn('a.codigo', codigos).select('a.codigo', 'a.auxiliar', 'e.edificio').orderBy('a.codigo');
  const doc = new PDFDocument({ size: 'LETTER', margin: 0, bufferPages: true });
  const chunks: Buffer[] = [];
  doc.on('data', (b: Buffer) => chunks.push(b));
  const done = new Promise<Buffer>((res) => doc.on('end', () => res(Buffer.concat(chunks))));
  const W = 180, H = 72, M = 36;
  const logo = c.Logo && fs.existsSync(c.Logo) ? c.Logo : '';
  acts.forEach((a: any, k: number) => {
    if (k > 0 && k % 30 === 0) doc.addPage();
    const x = M + (k % 3) * W;
    const y = M + Math.floor((k % 30) / 3) * H;
    doc.rect(x + 3, y + 3, W - 6, H - 6).lineWidth(0.6).strokeColor('#1F3A5F').stroke();
    doc.rect(x + 3, y + 3, W - 6, 13).fill('#1F3A5F');
    doc.fillColor('#FFFFFF').font('Helvetica-Bold').fontSize(6.3).text(String(c.Entidad ?? '').toUpperCase(), x + 5, y + 7, { width: W - 10, align: 'center', lineBreak: false });
    let tx = x + 6;
    let tw = W - 12;
    if (logo) { try { doc.image(logo, x + 7, y + 20, { fit: [34, 34] }); tx = x + 44; tw = W - 50; } catch { /* sin logo */ } }
    doc.fillColor('#1A1A1A').font('Helvetica-Bold').fontSize(7).text(txt(a.edificio), tx, y + 20, { width: tw, align: 'center', lineBreak: false });
    doc.font('Helvetica').fontSize(7).text(txt(a.auxiliar), tx, y + 29, { width: tw, align: 'center', lineBreak: false });
    doc.font('Helvetica-Bold').fontSize(14).text(a.codigo, tx, y + 42, { width: tw, align: 'center', lineBreak: false });
  });
  doc.end();
  return done;
}
void today;
void NotFound;
