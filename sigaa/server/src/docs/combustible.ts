/** Documentos PDF de Combustible: solicitud y vale (Anexos 1 y 2), nota de ingreso, planilla y descargo (Anexo 3), actas, conciliación y viajes (Anexos 4 y 6). */
import type { Db } from '../core/context.js';
import { fail, NotFound } from '../core/errors.js';
import { fmtDate, fmt2, literal, num, txt, round } from '../core/util.js';
import { cfgAll } from '../core/services.js';
import { PdfDoc, loadHeader } from '../pdf/builder.js';
import { registrarDoc, nomCargo } from './types.js';

const nuevo = async (db: Db, titulo: string, nro?: string, subtitulo?: string, landscape = false) => new PdfDoc({ titulo, nro, subtitulo, landscape, header: await loadHeader(db, 'combustible') });

async function emision(db: Db, nro: string) {
  const e = await db('com_emisiones').where({ nro }).first();
  if (!e) throw new NotFound(`No existe la emisión ${nro}.`);
  return e;
}

registrarDoc(
  {
    id: 'com-vale', nombre: 'Solicitud (Anexo 1) y vale de combustible (Anexo 2)', modulo: 'com', ref: 'Nº emisión (VC-…)',
    async build(db, nro) {
      const e = await emision(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Formulario de solicitud de combustible (Anexo 1)', nro, e.estado === 'Anulado' ? 'EMISIÓN ANULADA' : undefined);
      pdf.kv([['Fecha', fmtDate(e.fecha)], ['Unidad / área solicitante', e.unidad], ['Solicitante', e.solicitante], ['Cargo', e.cargo_solicitante], ['Destino', `${e.destino === 'TURRIL' ? 'Turril' : 'Vehículo'}: ${e.placa} — ${e.descripcion_destino}`], ['Conductor / operador', e.conductor], ['Apertura programática', `${e.apertura} - ${txt(e.desc_apertura)}`], ['Periodo de utilización', `${fmtDate(e.desde)} al ${fmtDate(e.hasta)}`], ['Trabajo a realizar', e.trabajo], ['Km / horómetro actual', e.lectura_actual], ['Programado (km u horas)', e.programado], ['Litros máximos permitidos', e.litros_max], ['Justificación de excedente', e.justificacion], ['Observaciones', e.observaciones]]);
      pdf.seccion('Combustible solicitado').kv([['Combustible', e.combustible], ['Vales', e.detalle_vales], ['Monto (Bs)', fmt2(e.monto)], ['Litros equivalentes', `${fmt2(e.litros)} L a Bs ${e.precio_l}/L`]], 1);
      pdf.firmas([{ nombre: e.solicitante, cargo: e.cargo_solicitante, rol: 'SOLICITANTE' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'AUTORIZA' }]);
      pdf.pagina('Vale de combustible (Anexo 2)', nro);
      pdf.kv([['Nº de emisión', nro], ['Fecha', fmtDate(e.fecha)], ['Conductor', e.conductor], ['Placa / código', e.placa], ['Nº de licencia', e.licencia], ['Destino', e.descripcion_destino], ['Unidad', e.unidad], ['Periodo', `${fmtDate(e.desde)} al ${fmtDate(e.hasta)}`], ['Km / horómetro', e.lectura_actual], ['Trabajo a realizar', e.trabajo]]);
      pdf.tabla([{ header: 'Apertura', w: 1.2 }, { header: 'Descripción apertura', w: 3 }, { header: 'Litros', w: 1, num: 'money' }, { header: 'CU (Bs/L)', w: 1, num: 'money' }, { header: 'Costo total Bs', w: 1.2, num: 'money' }], [[e.apertura, e.desc_apertura, e.litros, e.precio_l, e.monto]], { totales: ['', '', '', 'TOTAL', e.monto] });
      pdf.parrafo(`Son: ${literal(num(e.monto))}`, { bold: true, align: 'left' });
      pdf.kv([['Vales entregados', e.detalle_vales], ['Cantidad', `${e.cant_vales} vales`]], 1);
      pdf.parrafo('El conductor se compromete a presentar el descargo (Anexo 3) con la bitácora de recorrido y las facturas dentro del plazo establecido. Prohibido usar los vales en vehículos distintos al consignado (Art. 14).', { size: 8, align: 'left' });
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'ENTREGA' }, { nombre: e.conductor, cargo: 'CONDUCTOR / OPERADOR', rol: 'RECIBÍ CONFORME' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'AUTORIZA' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'com-nota-ingreso', nombre: 'Nota de ingreso de vales a almacén', modulo: 'com', ref: 'Nº ingreso (IV-…)',
    async build(db, nro) {
      const l = await db('com_lotes').where({ nro_ingreso: nro }).orderBy('id_lote');
      if (!l.length) throw new NotFound(`No existe el ingreso ${nro}.`);
      const c = await cfgAll(db);
      const h = l[0];
      const pdf = await nuevo(db, 'Nota de ingreso de vales a almacén', nro, undefined, true);
      pdf.kv([['Fecha de recepción', fmtDate(h.fecha)], ['Contrato', h.nro_contrato], ['Proveedor', h.proveedor], ['Modalidad', h.modalidad], ['Combustible', h.combustible], ['Factura Nº', h.factura], ['Fecha de factura', fmtDate(h.fecha_factura)], ['Nota / comprobante', `${txt(h.nota_ref)} ${txt(h.comprobante)}`.trim()], ['Observaciones', h.observaciones]]);
      const filas = l.map((x: any) => [x.id_lote, x.corte, x.desde, x.hasta, x.cantidad, x.monto]);
      pdf.espacio(4).tabla([{ header: 'Lote', w: 1 }, { header: 'Corte Bs', w: 1, num: 'int' }, { header: 'Nº desde', w: 1.2, num: 'int' }, { header: 'Nº hasta', w: 1.2, num: 'int' }, { header: 'Cantidad', w: 1, num: 'int' }, { header: 'Monto Bs', w: 1.3, num: 'money' }], filas, { totales: ['TOTAL', '', '', '', filas.reduce((t: number, f: any) => t + f[4], 0), filas.reduce((t: number, f: any) => t + f[5], 0)] });
      pdf.parrafo(`Son: ${literal(filas.reduce((t: number, f: any) => t + f[5], 0))}`, { bold: true, align: 'left' });
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RECIBE EN ALMACÉN' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo.' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'com-planilla-descargo', nombre: 'Planilla de descargo del conductor (bitácora, Anexo 3)', modulo: 'com', ref: 'Nº emisión (VC-…)',
    async build(db, nro) {
      const e = await emision(db, nro);
      const vales = await db('com_vales').where({ nro_emision: nro }).orderBy(['corte', 'nro_vale']);
      const pdf = await nuevo(db, 'Descargo de vales — bitácora de control (Anexo 3)', nro, 'El conductor presenta la bitácora con las lecturas, los vales usados y las facturas', true);
      pdf.kv([['Vehículo / puesto', `${e.placa} — ${e.descripcion_destino}`], ['Conductor', e.conductor], ['Periodo', `${fmtDate(e.desde)} al ${fmtDate(e.hasta)}`], ['Combustible', e.combustible], ['Vales entregados', e.detalle_vales], ['Lectura al emitir', e.lectura_actual]]);
      pdf.espacio(4).tabla([{ header: 'Fecha', w: 1 }, { header: 'Ruta / actividad', w: 3 }, { header: 'Lectura salida', w: 1.1 }, { header: 'Lectura llegada', w: 1.1 }, { header: 'Nº vale', w: 1 }, { header: 'Litros', w: 0.9 }, { header: 'Nº factura', w: 1.1 }, { header: 'Estación de servicio', w: 2 }], Array.from({ length: Math.max(12, vales.length + 3) }, () => ['', '', '', '', '', '', '', '']), { fontSize: 11 });
      pdf.parrafo(`Plazo para presentar el descargo: ${await (async () => (await cfgAll(db)).DIAS_PLAZO_DESCARGO ?? '3')()} día(s) después del fin del periodo.`, { size: 8, align: 'left' });
      pdf.firmas([{ nombre: e.conductor, rol: 'CONDUCTOR / OPERADOR' }, { nombre: (await cfgAll(db)).NombreRAF, cargo: (await cfgAll(db)).CargoRAF, rol: 'RECIBE EL DESCARGO' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'com-descargo', nombre: 'Descargo de vales registrado', modulo: 'com', ref: 'Nº descargo (DS-…)',
    async build(db, nro) {
      const d = await db('com_descargos').where({ nro }).first();
      if (!d) throw new NotFound(`No existe el descargo ${nro}.`);
      const lin = await db('com_descargo_lineas').where({ nro }).orderBy('id');
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Descargo de vales de combustible (Anexo 3)', nro, `Estado: ${d.estado}${d.alertas ? ' — ' + d.alertas : ''}`, true);
      pdf.kv([['Emisión', d.nro_emision], ['Fecha de descargo', fmtDate(d.fecha)], ['Placa', d.placa], ['Conductor', d.conductor], ['Lectura inicial / final', `${d.lectura_inicial ?? ''} / ${d.lectura_final ?? ''} (${d.medidor})`], ['Recorrido', d.recorrido], ['Litros', d.litros], ['Vales usados / devueltos', `${d.vales_usados} / ${d.vales_devueltos}`], ['Monto usado (Bs)', fmt2(d.monto_usado)], ['Rendimiento real / ref.', `${d.rendimiento_real ?? '-'} / ${d.rendimiento_ref ?? '-'}`], ['Desviación', d.desviacion !== null && d.desviacion !== undefined ? `${(num(d.desviacion) * 100).toFixed(1)}%` : '-'], ['Observaciones', d.observaciones]]);
      pdf.espacio(4).tabla([{ header: 'Fecha', w: 1 }, { header: 'Ruta', w: 3 }, { header: 'Lect. salida', w: 1, num: 'money' }, { header: 'Lect. llegada', w: 1, num: 'money' }, { header: 'Nº vale', w: 1, num: 'int' }, { header: 'Litros', w: 0.9, num: 'money' }, { header: 'Factura', w: 1.1 }, { header: 'Estación', w: 2 }], lin.map((l: any) => [fmtDate(l.fecha), l.ruta, l.lectura_salida, l.lectura_llegada, l.nro_vale, l.litros, l.factura, l.estacion]));
      pdf.firmas([{ nombre: d.conductor, rol: 'CONDUCTOR / OPERADOR' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RECIBE EL DESCARGO' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'com-acta-movimiento', nombre: 'Acta de devolución, anulación, vencimiento o extravío de vales', modulo: 'com', ref: 'Nº movimiento (MV-… o DS-…)',
    async build(db, nro) {
      const k = await db('com_kardex').where({ documento: nro }).whereIn('tipo', ['DEVOLUCIÓN', 'BAJA']).orderBy('id');
      if (!k.length) fail(`El documento ${nro} no tiene movimientos de vales (devolución/baja).`);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Acta de movimiento de vales de combustible', nro);
      pdf.kv([['Fecha', fmtDate(k[0].fecha)], ['Tipo', k[0].tipo === 'DEVOLUCIÓN' ? 'Devolución al almacén' : 'Baja de vales']]);
      pdf.espacio(4).tabla([{ header: 'Ítem', w: 2.5 }, { header: 'Movimiento', w: 1.2 }, { header: 'Cantidad', w: 0.9, num: 'int' }, { header: 'Importe Bs', w: 1.1, num: 'money' }, { header: 'Detalle', w: 4 }], k.map((x: any) => [x.item, x.tipo, num(x.entrada) || num(x.salida), num(x.importe_entrada) || num(x.importe_salida), x.detalle]));
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ALMACÉN' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo.' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'com-conciliacion', nombre: 'Conciliación con el proveedor', modulo: 'com', ref: 'Nº conciliación (CC-…)',
    async build(db, nro) {
      const rows = await db('com_conciliaciones').where({ nro }).orderBy('id');
      if (!rows.length) throw new NotFound(`No existe la conciliación ${nro}.`);
      const h = rows[0];
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Conciliación de vales con el proveedor', nro, undefined, true);
      const pag = rows.filter((r: any) => r.pagable);
      pdf.kv([['Proveedor', h.proveedor], ['Contrato', h.contrato], ['Periodo', `${fmtDate(h.desde)} al ${fmtDate(h.hasta)}`], ['Vales conformes', pag.length], ['Monto a pagar (Bs)', fmt2(pag.reduce((t: number, r: any) => t + num(r.monto_cobrado), 0))], ['Observados', rows.length - pag.length]]);
      pdf.espacio(4).tabla([{ header: 'Nº vale', w: 1, num: 'int' }, { header: 'Corte', w: 0.7, num: 'int' }, { header: 'Cobrado Bs', w: 1, num: 'money' }, { header: 'Placa cobro', w: 1 }, { header: 'Placa sistema', w: 1 }, { header: 'Emisión', w: 1.2 }, { header: 'Resultado', w: 1.3 }, { header: 'Detalle', w: 4 }], rows.map((r: any) => [r.nro_vale, r.corte, r.monto_cobrado, r.placa_cobro, r.placa_sistema, r.nro_emision, r.resultado, r.detalle]));
      pdf.firmas([{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE COMBUSTIBLE' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'AUTORIZA PAGO' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'com-viaje', nombre: 'Viaje oficial: solicitud (Anexo 4) y descargo (Anexo 6)', modulo: 'com', ref: 'Nº viaje (VJ-…)',
    async build(db, nro) {
      const v = await db('com_viajes').where({ nro }).first();
      if (!v) throw new NotFound(`No existe el viaje ${nro}.`);
      const det = await db('com_viajes_det').where({ nro }).orderBy('id');
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Viaje oficial con fondos en avance', nro, `Estado: ${v.estado}`, true);
      pdf.seccion('Solicitud (Anexo 4)').kv([['Fecha de solicitud', fmtDate(v.fecha)], ['Vehículo', v.placa], ['Conductor', v.conductor], ['Ruta', `${v.origen} → ${v.destino}`], ['Salida / retorno', `${fmtDate(v.salida)} / ${fmtDate(v.retorno)}`], ['Km / litros estimados', `${v.km_estimado ?? '-'} / ${v.litros_estimados ?? '-'}`], ['Apertura', `${v.apertura} ${txt(v.desc_apertura)}`], ['Fondo en avance (Bs)', fmt2(v.fondo)], ['Motivo / comisión', v.motivo], ['Funcionarios', v.funcionarios], ['Nota / comprobante', `${txt(v.nota)} ${txt(v.comprobante)}`.trim()]]);
      if (v.estado === 'Descargado') {
        pdf.seccion('Descargo (Anexo 6)');
        const tr = det.filter((d: any) => d.tipo === 'TRAMO');
        const co = det.filter((d: any) => d.tipo === 'COMPRA');
        pdf.tabla([{ header: 'Fecha', w: 1 }, { header: 'Origen', w: 2 }, { header: 'Destino', w: 2 }, { header: 'Km inicial', w: 1, num: 'money' }, { header: 'Km final', w: 1, num: 'money' }, { header: 'Recorrido', w: 1, num: 'money' }], tr.map((d: any) => [fmtDate(d.fecha), d.origen, d.destino, d.km_inicial, d.km_final, d.recorrido]), { totales: ['TOTAL', '', '', '', '', v.km_recorrido] });
        pdf.tabla([{ header: 'Fecha', w: 1 }, { header: 'Estación de servicio', w: 3 }, { header: 'Factura', w: 1.2 }, { header: 'Litros', w: 1, num: 'money' }, { header: 'Total Bs', w: 1.2, num: 'money' }], co.map((d: any) => [fmtDate(d.fecha), d.estacion, d.factura, d.litros, d.total]), { totales: ['TOTAL', '', '', v.litros_comprados, v.gastado] });
        pdf.kv([['Fondo (Bs)', fmt2(v.fondo)], ['Gastado (Bs)', fmt2(v.gastado)], ['Saldo (Bs)', `${fmt2(v.saldo)} ${num(v.saldo) >= 0 ? '(a devolver)' : '(reembolso sujeto a aprobación)'}`], ['Rendimiento real', v.rendimiento_real], ['Resultado', `${v.resultado}${v.alertas ? ' — ' + v.alertas : ''}`], ['Actividades', v.actividades], ['Conclusiones', v.conclusiones]]);
      } else pdf.aviso('Viaje en curso — pendiente de descargo', '#B3261E');
      pdf.firmas([{ nombre: v.conductor, cargo: 'CONDUCTOR', rol: 'RESPONSABLE DEL FONDO' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE COMBUSTIBLE' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'AUTORIZA' }]);
      return pdf.buffer();
    },
  },
);
void nomCargo;
void round;
