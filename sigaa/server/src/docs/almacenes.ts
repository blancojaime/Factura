/** Documentos PDF de Almacenes: CGI, vale de salida, kardex, actas de inventario, expediente de baja, transferencia, requerimiento, inspección. */
import type { Db } from '../core/context.js';
import { fail, NotFound } from '../core/errors.js';
import { fmtDate, fmt2, isDate, literal, num, round, today, txt, addDays } from '../core/util.js';
import { cfgAll, cfgNum } from '../core/services.js';
import { PdfDoc, loadHeader } from '../pdf/builder.js';
import { kardex } from '../modules/almacenes/stock.js';
import { obtenerIngreso } from '../modules/almacenes/ingresos.js';
import { obtenerSalida } from '../modules/almacenes/salidas.js';
import { obtenerInventario } from '../modules/almacenes/inventarios.js';
import { obtenerBaja } from '../modules/almacenes/bajas.js';
import { obtenerTransferencia, obtenerRequerimiento, obtenerInspeccion } from '../modules/almacenes/otros.js';
import { sumarDiasHabiles } from '../core/util.js';
import { registrarDoc, nomCargo, casilla } from './types.js';

const nuevo = async (db: Db, titulo: string, nro?: string, subtitulo?: string, landscape = false) => new PdfDoc({ titulo, nro, subtitulo, landscape, header: await loadHeader(db, 'UnidadAlm') });
const bodegaNombre = async (db: Db, cod: string) => txt((await db('alm_bodegas').where({ cod }).first('nombre'))?.nombre);

registrarDoc(
  {
    id: 'alm-cgi', nombre: 'Control General de Ingresos (CGI)', modulo: 'alm', ref: 'Nº CGI',
    async build(db, nro) {
      const h = await obtenerIngreso(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Control General de Ingresos a Almacén (CGI)', nro, h.estado === 'INGRESADO' ? undefined : `Estado: ${h.estado} — documento no válido hasta confirmar el ingreso`, true);
      pdf.kv([['Fecha de recepción', fmtDate(h.fecha)], ['Bodega', h.bodega], ['Tipo de ingreso', h.tipo], ['Proveedor', h.proveedor], ['NIT', h.nit], ['Orden de compra / contrato', h.nro_oc], ['Plazo de entrega', fmtDate(h.plazo_entrega)], ['Factura / nota de remisión', h.factura], ['Fecha de factura', fmtDate(h.fecha_factura)], ['Unidad solicitante', h.unidad], ['Nº preventivo', h.preventivo], ['Proyecto / destino', h.proyecto], ['Fuente de financiamiento', h.fuente], ['Partida', h.partida], ['Comisión de recepción', h.comision], ['Observaciones', h.obs_plazo]]);
      pdf.espacio(4).tabla(
        [{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Marca / caract.', w: 1.5 }, { header: 'Unidad', w: 0.9 }, { header: 'Cantidad', w: 0.9, num: 'qty' }, { header: 'P. unit. (Bs)', w: 1, num: 'money' }, { header: 'Total (Bs)', w: 1.1, num: 'money' }, { header: 'Vencim.', w: 1 }, { header: 'Lote', w: 0.9 }],
        h.items.map((x: any) => [x.item, x.cod_item, x.descripcion, x.marca, x.unidad, x.cantidad, x.precio_unit, x.total, fmtDate(x.vencimiento), x.lote]),
        { totales: ['', '', '', '', '', '', 'TOTAL', h.total, '', ''] },
      );
      pdf.parrafo(`Son: ${literal(num(h.total))}`, { bold: true, align: 'left' });
      pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' }, { nombre: txt(h.comision).split('/')[0], cargo: 'COMISIÓN DE RECEPCIÓN', rol: 'RECEPCIÓN CONFORME' }, { nombre: c.NombreCON, cargo: c.CargoCON, rol: 'REGISTRO CONTABLE' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-verif-docs', nombre: 'Verificación de documentos de respaldo del ingreso', modulo: 'alm', ref: 'Nº CGI',
    async build(db, nro) {
      const h = await obtenerIngreso(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Verificación de documentos de respaldo', nro, 'Art. 13-IV · Manual 11.2');
      pdf.kv([['Bodega', h.bodega], ['Tipo de ingreso', h.tipo], ['Proveedor', h.proveedor], ['Factura', h.factura]]);
      pdf.espacio(4).tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Documento exigido', w: 6 }, { header: '¿Recibido?', w: 1, align: 'center' }, { header: 'Obligatorio', w: 1, align: 'center' }],
        h.docs.map((d: any) => [d.orden, String(d.documento).replace('  (*)', ''), d.estado === 'SI' ? 'SÍ' : 'NO', String(d.documento).endsWith('(*)') ? 'SÍ' : 'NO']));
      pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo.' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-vale', nombre: 'Pedido y vale de salida de materiales', modulo: 'alm', ref: 'Nº vale',
    async build(db, nro) {
      const h = await obtenerSalida(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Pedido y vale de salida de materiales y suministros', nro, `Estado: ${h.estado}`, true);
      pdf.kv([['Fecha del pedido', fmtDate(h.fecha_pedido)], ['Bodega', h.bodega], ['Unidad solicitante', h.unidad], ['Solicitante', h.solicitante], ['Cargo', h.cargo], ['Inmediato superior (Vo.Bo.)', h.superior], ['Proyecto / destino', h.proyecto], ['Nota interna', h.nota_interna], ['Justificación', h.justificacion], ['Excepción autorizada por', h.excepcion], ['Fecha de entrega', h.fecha_entrega], ['Observaciones', h.observ]]);
      pdf.espacio(4).tabla(
        [{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unidad', w: 1 }, { header: 'Saldo', w: 0.9, num: 'qty' }, { header: 'Pedida', w: 0.9, num: 'qty' }, { header: 'Entregada', w: 0.9, num: 'qty' }, { header: 'P.U. prom. (Bs)', w: 1.1, num: 'money' }, { header: 'Importe (Bs)', w: 1.1, num: 'money' }],
        h.items.map((x: any) => [x.item, x.cod_item, x.descripcion, x.unidad, x.saldo_actual, x.cant_pedida, h.estado === 'ENTREGADO' ? x.cant_entregada : '', h.estado === 'ENTREGADO' ? x.precio_prom : '', h.estado === 'ENTREGADO' ? x.total : '']),
        { totales: ['', '', '', '', '', '', '', 'TOTAL', h.estado === 'ENTREGADO' ? h.total : ''] },
      );
      pdf.firmas([{ nombre: h.solicitante, cargo: h.cargo, rol: 'SOLICITANTE — RECIBIDO' }, { nombre: h.superior, rol: 'Vo.Bo. INMEDIATO SUPERIOR' }, { nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENTREGA — ALMACÉN' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-cert-inexistencia', nombre: 'Certificación de inexistencia de materiales', modulo: 'alm', ref: 'Nº vale',
    async build(db, nro) {
      const h = await obtenerSalida(db, nro);
      const c = await cfgAll(db);
      const sin = h.items.filter((x: any) => num(x.saldo_actual) <= 1e-6 || num(x.cant_entregada) === 0 && h.estado === 'ENTREGADO');
      if (!sin.length) fail('Todos los ítems del pedido tienen existencia; no corresponde certificar inexistencia.');
      const pdf = await nuevo(db, 'Certificación de inexistencia de materiales', nro);
      pdf.lugarFecha();
      pdf.parrafo(`El Encargado de Almacenes certifica que, a la fecha, la ${h.bodega} NO cuenta con existencias de los siguientes materiales solicitados por ${h.solicitante} (${h.unidad}) mediante el pedido ${nro}, por lo que corresponde iniciar el requerimiento de compra (Manual de Almacenes).`);
      pdf.tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 5 }, { header: 'Unidad', w: 1 }, { header: 'Cant. pedida', w: 1, num: 'qty' }, { header: 'Saldo', w: 1, num: 'qty' }], sin.map((x: any, i: number) => [i + 1, x.cod_item, x.descripcion, x.unidad, x.cant_pedida, x.saldo_actual]));
      pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo. JEFE DE BIENES Y SERVICIOS' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-kardex', nombre: 'Kardex de existencias (tarjeta valorada por ítem)', modulo: 'alm', ref: 'Código del ítem (parámetros: bodega, desde, hasta)',
    async build(db, cod, p) {
      const it = await db('alm_catalogo').where({ codigo: cod }).first();
      if (!it) throw new NotFound(`No existe el ítem ${cod}.`);
      const desde = isDate(p.desde) ? p.desde! : `${today().slice(0, 4)}-01-01`;
      const hasta = isDate(p.hasta) ? p.hasta! : today();
      const bod = txt(p.bodega) && p.bodega!.toUpperCase() !== 'TODAS' ? p.bodega! : '';
      const k = await kardex(db, bod, cod, desde, hasta);
      const pdf = await nuevo(db, 'Kardex de existencias (tarjeta valorada)', undefined, 'Método de valoración: PEPS por lotes · saldo con precio promedio informativo', true);
      pdf.kv([['Bodega', bod ? await bodegaNombre(db, bod) : 'TODAS'], ['Ítem', `${it.codigo} - ${it.descripcion}`], ['Unidad / partida', `${it.unidad} / ${it.partida ?? ''}`], ['Periodo', `${fmtDate(desde)} al ${fmtDate(hasta)}`], ['Saldo actual', k[k.length - 1].saldoCant]]);
      pdf.espacio(4).tabla(
        [{ header: 'Fecha', w: 1 }, { header: 'Documento', w: 1.3 }, { header: 'Detalle', w: 4 }, { header: 'Entrada cant.', w: 1, num: 'qty' }, { header: 'Entrada Bs', w: 1.1, num: 'money' }, { header: 'Salida cant.', w: 1, num: 'qty' }, { header: 'Salida Bs', w: 1.1, num: 'money' }, { header: 'Saldo cant.', w: 1, num: 'qty' }, { header: 'Saldo Bs', w: 1.1, num: 'money' }, { header: 'P.U. prom.', w: 1, num: 'money' }],
        k.map((x) => [fmtDate(x.fecha), x.documento, x.detalle, x.entCant, x.entBs, x.salCant, x.salBs, x.saldoCant, x.saldoBs, x.puProm]),
      );
      const c = await cfgAll(db);
      pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-hoja-conteo', nombre: 'Hoja de conteo físico', modulo: 'alm', ref: 'Nº inventario',
    async build(db, nro) {
      const h = await obtenerInventario(db, nro);
      const ciego = (await cfgAll(db)).ConteoCiego !== 'NO';
      const pdf = await nuevo(db, 'Hoja de conteo físico de existencias', nro, ciego ? 'Conteo ciego: sin saldos del sistema' : undefined);
      pdf.kv([['Fecha del inventario', fmtDate(h.fecha)], ['Bodega', h.bodega], ['Tipo', h.tipo], ['Encargado', h.responsable]]);
      const cols: any[] = [{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unidad', w: 1 }];
      if (!ciego) cols.push({ header: 'Saldo sistema', w: 1, num: 'qty' });
      cols.push({ header: 'CONTEO FÍSICO', w: 1.4 }, { header: 'Estado / observación', w: 2 });
      pdf.espacio(4).tabla(cols, h.items.map((x: any) => (ciego ? [x.item, x.cod_item, x.descripcion, x.unidad, '', ''] : [x.item, x.cod_item, x.descripcion, x.unidad, x.saldo_sist, '', ''])), { fontSize: 8.5 });
      pdf.firmas([{ nombre: h.responsable, rol: 'ENCARGADO DE ALMACENES' }, { rol: 'FUNCIONARIO DESIGNADO' }, { nombre: h.observador, rol: 'OBSERVADOR / TESTIGO' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-acta-inventario', nombre: 'Acta de inventario físico', modulo: 'alm', ref: 'Nº inventario',
    async build(db, nro) {
      const h = await obtenerInventario(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Acta de inventario físico de existencias', nro, h.estado === 'CERRADO' ? undefined : 'Inventario en conteo (borrador)', true);
      pdf.kv([['Fecha', fmtDate(h.fecha)], ['Bodega', h.bodega], ['Tipo de inventario', h.tipo], ['Encargado de almacén', h.responsable], ['Funcionario(s) designado(s)', h.designado], ['Observador / testigo', h.observador], ['Corte de documentación', [h.corte_ing, h.corte_sal].filter(Boolean).join('  |  ')], ['Faltantes / sobrantes (Bs)', `Faltantes Bs ${fmt2(h.faltante_bs)} · Sobrantes Bs ${fmt2(h.sobrante_bs)}`]]);
      const filas = h.items.map((x: any) => [x.item, x.cod_item, x.descripcion, x.unidad, x.saldo_sist, x.conteo, x.diferencia, x.precio_unit, round(num(x.diferencia) * num(x.precio_unit), 2), x.estado_bien, x.obs]);
      pdf.espacio(4).tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 3.5 }, { header: 'Unid.', w: 0.9 }, { header: 'Saldo sist.', w: 0.9, num: 'qty' }, { header: 'Conteo', w: 0.9, num: 'qty' }, { header: 'Dif.', w: 0.8, num: 'qty' }, { header: 'P.U. (Bs)', w: 0.9, num: 'money' }, { header: 'Valor dif. (Bs)', w: 1, num: 'money' }, { header: 'Estado del bien', w: 1.2 }, { header: 'Observación', w: 2.2 }], filas, { totales: ['', '', '', '', '', '', '', 'TOTAL', filas.reduce((t: number, f: any) => t + num(f[8]), 0), '', ''] });
      pdf.firmas([{ nombre: h.responsable, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' }, { nombre: txt(h.designado).split(' y ')[0], rol: 'FUNCIONARIO DESIGNADO' }, { nombre: h.observador, rol: 'OBSERVADOR / TESTIGO' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo.' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-acta-reposicion', nombre: 'Acta de reposición de faltantes de inventario', modulo: 'alm', ref: 'Nº inventario',
    async build(db, nro) {
      const h = await obtenerInventario(db, nro);
      const c = await cfgAll(db);
      const falt = h.items.filter((x: any) => num(x.diferencia) < -1e-6);
      if (!falt.length) fail('El inventario no tiene faltantes.');
      const pdf = await nuevo(db, 'Acta de reposición de faltantes', nro);
      pdf.lugarFecha();
      pdf.parrafo(`En ${h.bodega}, como resultado del inventario ${nro} realizado el ${fmtDate(h.fecha)}, se establecieron faltantes de existencias. De conformidad con el Manual de Almacenes, el Encargado ${h.responsable} se compromete a REPONER los bienes faltantes, de iguales características, en el plazo que fije el inmediato superior; caso contrario se iniciará el expediente de baja por pérdida y la determinación de responsabilidades.`);
      const filas = falt.map((x: any, i: number) => [i + 1, x.cod_item, x.descripcion, x.unidad, -num(x.diferencia), x.precio_unit, round(-num(x.diferencia) * num(x.precio_unit), 2)]);
      pdf.tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unid.', w: 1 }, { header: 'Cant. faltante', w: 1, num: 'qty' }, { header: 'P.U. (Bs)', w: 1, num: 'money' }, { header: 'Total (Bs)', w: 1, num: 'money' }], filas, { totales: ['', '', '', '', '', 'TOTAL', filas.reduce((t: number, f: any) => t + f[6], 0)] });
      pdf.firmas([{ nombre: h.responsable, cargo: c.CargoALM, rol: 'ENCARGADO — SE COMPROMETE' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'INMEDIATO SUPERIOR' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'AUTORIZA' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-inventario-valorado', nombre: 'Inventario valorado de existencias', modulo: 'alm', ref: 'Nº inventario',
    async build(db, nro) {
      const h = await obtenerInventario(db, nro);
      const pdf = await nuevo(db, 'Inventario valorado de existencias', nro, `${h.bodega} · ${fmtDate(h.fecha)}`, true);
      const filas = h.items.map((x: any) => [x.item, x.cod_item, x.descripcion, x.unidad, x.conteo ?? x.saldo_sist, x.precio_unit, round(num(x.conteo ?? x.saldo_sist) * num(x.precio_unit), 2)]);
      pdf.tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4.5 }, { header: 'Unid.', w: 1 }, { header: 'Existencia', w: 1, num: 'qty' }, { header: 'P.U. (Bs)', w: 1, num: 'money' }, { header: 'Valor (Bs)', w: 1.2, num: 'money' }], filas, { totales: ['', '', '', '', '', 'TOTAL', filas.reduce((t: number, f: any) => t + f[6], 0)] });
      const c = await cfgAll(db);
      pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' }, { nombre: c.NombreCON, cargo: c.CargoCON, rol: 'CONTABILIDAD' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-baja', nombre: 'Documento del expediente de baja (acta, informe, memorándum, registro, convocatoria)', modulo: 'alm', ref: 'Nº expediente (parámetro: doc = ACTAVER|INFSOL|INFTEC|MEMOCOM|ACTADEST|ACTAENT|REGBAJA|CONVOC)',
    async build(db, nro, p) {
      const h = await obtenerBaja(db, nro);
      const cod = txt(p.doc).toUpperCase();
      const c = await cfgAll(db);
      const causal = String(h.causal).toLowerCase();
      const tot = h.items.reduce((t: number, x: any) => t + num(x.total), 0);
      const items = (conPrecio: boolean) => ({
        cols: conPrecio
          ? [{ header: 'N°', w: 0.5, align: 'center' as const }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unid.', w: 0.9 }, { header: 'Lote', w: 0.9 }, { header: 'Cantidad', w: 1, num: 'qty' as const }, { header: 'P.U. (Bs)', w: 1, num: 'money' as const }, { header: 'Total (Bs)', w: 1.1, num: 'money' as const }]
          : [{ header: 'N°', w: 0.5, align: 'center' as const }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unid.', w: 0.9 }, { header: 'Lote', w: 0.9 }, { header: 'Cantidad', w: 1, num: 'qty' as const }, { header: 'Estado / observación', w: 2.5 }],
        filas: h.items.map((x: any) => (conPrecio ? [x.item, x.cod_item, x.descripcion, x.unidad, x.id_lote, x.cantidad, x.precio_unit, x.total] : [x.item, x.cod_item, x.descripcion, x.unidad, x.id_lote, x.cantidad, ''])),
      });
      const nombres: Record<string, string> = { ACTAVER: 'Acta de verificación', INFSOL: 'Informe de solicitud de baja', INFTEC: 'Informe técnico de recomendación de baja', MEMOCOM: 'Memorándum de designación de comisión', ACTADEST: 'Acta de destrucción', ACTAENT: 'Acta de entrega gratuita / subasta / destrucción', REGBAJA: 'Registro de baja de bienes', CONVOC: 'Convocatoria de publicación (SICOES)' };
      if (!nombres[cod]) fail(`Documento de baja desconocido: ${cod || '(vacío)'}.`);
      const pdf = await nuevo(db, nombres[cod], nro);
      const it = items(cod === 'REGBAJA' || cod === 'INFTEC' || cod === 'INFSOL');
      switch (cod) {
        case 'ACTAVER':
          pdf.parrafo(`En ${c.Municipio}, ${fmtDate(today())}, en instalaciones de la ${h.bodega}, ${nomCargo(c.NombreALM, c.CargoALM)} en coordinación con ${nomCargo(c.NombreJBS, c.CargoJBS)} procedieron a verificar físicamente los bienes que se detallan, constatando su situación de ${causal}.`);
          pdf.kv([['Descripción del hecho / estado', h.justificacion]], 1).espacio(3).tabla(it.cols, it.filas);
          pdf.parrafo('Observadores (uno o dos servidores públicos): ____________________________________   ____________________________________', { align: 'left' });
          pdf.parrafo('Se suscribe la presente acta en constancia de lo verificado.', { align: 'left' });
          pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'INMEDIATO SUPERIOR' }, { rol: 'OBSERVADOR 1' }, { rol: 'OBSERVADOR 2' }]);
          break;
        case 'INFSOL':
          pdf.kv([['A', nomCargo(c.NombreJBS, c.CargoJBS)], ['Fecha', fmtDate(h.fecha)], ['De', nomCargo(h.responsable, c.CargoALM)], ['Referencia', `Solicitud de baja por causal de ${causal}`]]);
          pdf.seccion('Antecedentes y justificación').parrafo(`Como resultado de la verificación periódica de las existencias de la ${h.bodega}, se identificaron bienes de consumo en situación de ${causal}. ${h.justificacion}`);
          pdf.seccion('Detalle de los bienes').tabla(it.cols, it.filas, { totales: ['', '', '', '', '', '', 'TOTAL', tot] });
          pdf.seccion('Solicitud').parrafo(`Por lo expuesto, y de conformidad con el artículo 30 del Reglamento Interno de Administración de Almacenes, se solicita iniciar el trámite de baja de los bienes detallados, con la causal de ${causal}.`);
          pdf.firmas([{ nombre: h.responsable, cargo: c.CargoALM, rol: 'SOLICITA' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo. INMEDIATO SUPERIOR' }]);
          break;
        case 'INFTEC':
          pdf.kv([['A', nomCargo(c.NombreSEC, c.CargoSEC)], ['Fecha', fmtDate(today())], ['De', nomCargo(c.NombreJBS, c.CargoJBS)], ['Referencia', `Recomendación de baja por ${causal}`]]);
          pdf.seccion('1. Antecedentes').parrafo(`El Encargado de Almacenes solicitó la baja de bienes de consumo de la ${h.bodega} con causal de ${causal} (expediente ${nro}). ${h.justificacion}`);
          pdf.seccion('2. Verificación del estado de los bienes y de la documentación').parrafo(`Verificado el estado de los bienes y la documentación de respaldo, se constata la situación de ${causal} de los siguientes ítems:`).tabla(it.cols, it.filas, { totales: ['', '', '', '', '', '', 'TOTAL', tot] });
          pdf.seccion('3. Recomendación').parrafo(`En mérito a lo expuesto, se recomienda aprobar la baja de los bienes detallados por el valor total de Bs ${fmt2(tot)}, y remitir los antecedentes a la Secretaría Municipal de Asuntos Jurídicos para el informe legal y la Resolución Administrativa.`);
          pdf.firmas([{ nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'ELABORA' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'APRUEBA' }]);
          break;
        case 'MEMOCOM':
          pdf.kv([['Lugar y fecha', `${c.Municipio}, ${fmtDate(today())}`], ['A', 'Representante de la Unidad Administrativa: ____________________\nRepresentante del Área Jurídica: ____________________\nVeedor - Unidad de Transparencia: ' + nomCargo(c.NombreTRA, c.CargoTRA)], ['De', nomCargo(c.NombreMAE, c.CargoMAE)], ['Referencia', 'Designación de comisión para la entrega / destrucción de bienes dados de baja']], 1);
          pdf.parrafo(`Mediante el presente se les designa como COMISIÓN para participar en la entrega o destrucción de los bienes de consumo dados de baja por ${causal} (expediente ${nro}, Resolución Administrativa Nº ${txt(h.nro_ra)}), debiendo elaborar el acta correspondiente.`);
          pdf.tabla(it.cols, it.filas);
          pdf.firmas([{ nombre: c.NombreMAE, cargo: c.CargoMAE, rol: 'MÁXIMA AUTORIDAD EJECUTIVA' }]);
          break;
        case 'ACTADEST':
        case 'ACTAENT':
          pdf.parrafo(`En ${c.Municipio}, ${fmtDate(today())}, a horas ........, la comisión designada mediante memorándum procedió a ${cod === 'ACTADEST' ? 'la destrucción' : 'la entrega o destrucción'} de los bienes de consumo dados de baja por ${causal} (expediente ${nro}, RA ${txt(h.nro_ra)}).`);
          if (cod === 'ACTAENT') pdf.seccion('Modalidad de disposición').parrafo(`${casilla(false)} Entrega gratuita a entidad pública (prioridad educación, salud, bienestar social)   ${casilla(false)} Entrega gratuita a institución privada   ${casilla(false)} Subasta al alza   ${casilla(false)} Destrucción`, { align: 'left' });
          pdf.kv([['Beneficiario / adjudicatario', ''], ['Nº carta / documento de interés', ''], [cod === 'ACTADEST' ? 'Lugar y método de destrucción' : 'Lugar y método de disposición', ''], ['Normativa ambiental aplicada', '']]);
          pdf.seccion('Bienes').tabla(it.cols, it.filas);
          pdf.parrafo(`Se adjunta registro fotográfico del acto (${casilla(false)} sí). Observaciones: ____________________________________________________________`, { align: 'left' });
          pdf.firmas([{ rol: 'REPRESENTANTE UNIDAD ADMINISTRATIVA' }, { rol: 'REPRESENTANTE ÁREA JURÍDICA' }, { nombre: c.NombreTRA, cargo: c.CargoTRA, rol: 'VEEDOR - TRANSPARENCIA' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo.' }]);
          break;
        case 'REGBAJA':
          pdf.kv([['Lugar y fecha', `${c.Municipio}, ${fmtDate(today())}`], ['Estado del expediente', h.estado], ['Bodega', h.bodega], ['Causal de baja', h.causal], ['Resolución Administrativa Nº', h.nro_ra], ['Fecha de la Resolución', fmtDate(h.fecha_ra)]]);
          pdf.parrafo('Con la Resolución Administrativa que autoriza la baja, se procede a la exclusión física del inventario del almacén y de los registros contables de los bienes de consumo que se detallan:');
          pdf.tabla(it.cols, it.filas, { totales: ['', '', '', '', '', '', 'TOTAL', tot] });
          pdf.parrafo(`Son: ${literal(tot)}`, { bold: true, align: 'left' });
          pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'DA DE BAJA LOS REGISTROS' }, { nombre: c.NombreCON, cargo: c.CargoCON, rol: 'REGISTRO CONTABLE' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo. INMEDIATO SUPERIOR' }]);
          break;
        case 'CONVOC': {
          const paso = h.pasos.find((x: any) => x.clase === 'PUB' && x.fecha) ?? h.pasos.find((x: any) => x.clase === 'PUB');
          const dias = await cfgNum(db, 'DiasPublicacion', 15);
          const fi = paso?.fecha;
          pdf.kv([['Entidad convocante', c.Entidad], ['Unidad', c.UnidadAlm], ['Inicio de publicación', fmtDate(fi)], ['Plazo mínimo', `${dias} días hábiles${fi ? ` (hasta el ${fmtDate(sumarDiasHabiles(fi, dias))})` : ''}`]]);
          pdf.parrafo(`El ${c.Entidad} convoca a las entidades públicas interesadas en recibir, a título gratuito y por ítems de manera total o parcial, los bienes de consumo que se detallan. Vencido el plazo sin interés, se convocará a instituciones privadas de bienestar social y, agotada la entrega gratuita, a la SUBASTA AL ALZA sin precio base.`);
          pdf.seccion('Bienes (características, ubicación y condición actual)').tabla(it.cols, it.filas);
          pdf.kv([['Ubicación de los bienes', `${h.bodega} - ${c.Municipio}`], ['Informes y entrega de cartas', `${c.UnidadAlm} - ${c.Entidad}`]], 1);
          pdf.firmas([{ nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'UNIDAD ADMINISTRATIVA' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'Vo.Bo.' }]);
          break;
        }
      }
      return pdf.buffer();
    },
  },
  {
    id: 'alm-acta-transferencia', nombre: 'Acta de transferencia entre bodegas', modulo: 'alm', ref: 'Nº transferencia',
    async build(db, nro) {
      const h = await obtenerTransferencia(db, nro);
      const pdf = await nuevo(db, 'Acta de transferencia de bienes entre bodegas', nro, `Estado: ${h.estado}`);
      pdf.kv([['Fecha', fmtDate(h.fecha)], ['Bodega de origen', h.bodega_origen], ['Bodega de destino', h.bodega_destino], ['Motivo', h.motivo], ['Entrega', h.entrega], ['Recibe', h.recibe]]);
      pdf.espacio(4).tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unid.', w: 1 }, { header: 'Cantidad', w: 1, num: 'qty' }, { header: 'P.U. prom. (Bs)', w: 1.1, num: 'money' }, { header: 'Total (Bs)', w: 1.1, num: 'money' }], h.items.map((x: any) => [x.item, x.cod_item, x.descripcion, x.unidad, x.cantidad, x.precio_unit, x.total]), { totales: ['', '', '', '', '', 'TOTAL', h.total] });
      pdf.firmas([{ nombre: h.entrega, rol: 'ENTREGA — BODEGA ORIGEN' }, { nombre: h.recibe, rol: 'RECIBE — BODEGA DESTINO' }, { nombre: (await cfgAll(db)).NombreJBS, cargo: (await cfgAll(db)).CargoJBS, rol: 'Vo.Bo.' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-requerimiento', nombre: 'Requerimiento de compra / informe técnico de reposición', modulo: 'alm', ref: 'Nº requerimiento',
    async build(db, nro) {
      const h = await obtenerRequerimiento(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Requerimiento de compra e informe técnico de reposición', nro, undefined, true);
      pdf.kv([['Fecha', fmtDate(h.fecha)], ['Bodega', h.bodega], ['Tipo de requerimiento', h.tipo], ['Total estimado (Bs)', fmt2(h.total)], ['Justificación', h.justificacion]]);
      pdf.espacio(4).tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unid.', w: 1 }, { header: 'Stock', w: 0.9, num: 'qty' }, { header: 'Cant. a solicitar', w: 1.1, num: 'qty' }, { header: 'P.U. ref. (Bs)', w: 1, num: 'money' }, { header: 'Importe (Bs)', w: 1.1, num: 'money' }, { header: 'Partida', w: 0.9 }], h.items.map((x: any) => [x.item, x.cod_item, x.descripcion, x.unidad, x.stock, x.cant_solic, x.precio_ref, x.total, x.partida]), { totales: ['', '', '', '', '', '', 'TOTAL', h.total, ''] });
      pdf.firmas([{ nombre: c.NombreALM, cargo: c.CargoALM, rol: 'SOLICITA' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo.' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'AUTORIZA' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-acta-inspeccion', nombre: 'Acta de inspección de higiene y seguridad', modulo: 'alm', ref: 'Nº inspección',
    async build(db, nro) {
      const h = await obtenerInspeccion(db, nro);
      const c = await cfgAll(db);
      const pdf = await nuevo(db, 'Acta de inspección de higiene, seguridad y salvaguarda', nro);
      const tot = h.cumple + h.no_cumple;
      pdf.kv([['Fecha', fmtDate(h.fecha)], ['Bodega inspeccionada', h.bodega], ['Inspector / responsable', h.inspector], ['Resultado', `Cumple ${h.cumple} | No cumple ${h.no_cumple}${tot ? ` (${Math.round((h.cumple / tot) * 100)}% de cumplimiento)` : ''}`]]);
      pdf.espacio(4).tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Criterio de verificación', w: 5 }, { header: 'Resultado', w: 1.1, align: 'center' }, { header: 'Observación / medida correctiva', w: 3.5 }], h.items.map((x: any) => [x.item, x.criterio, x.resultado, x.obs]));
      pdf.firmas([{ nombre: h.inspector, rol: 'INSPECTOR' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo.' }]);
      return pdf.buffer();
    },
  },
  {
    id: 'alm-nota-mantenimiento', nombre: 'Nota de solicitud de mantenimiento / medidas correctivas', modulo: 'alm', ref: 'Nº inspección',
    async build(db, nro) {
      const h = await obtenerInspeccion(db, nro);
      const c = await cfgAll(db);
      const no = h.items.filter((x: any) => x.resultado === 'NO CUMPLE');
      if (!no.length) fail('La inspección no tiene criterios que no cumplen.');
      const pdf = await nuevo(db, 'Nota de solicitud de mantenimiento', nro);
      pdf.kv([['A', nomCargo(c.NombreSEC, c.CargoSEC)], ['Fecha', fmtDate(today())], ['De', nomCargo(h.inspector, c.CargoALM)], ['Referencia', `Medidas correctivas — ${h.bodega}`]], 1);
      pdf.parrafo(`Como resultado de la inspección ${nro} realizada el ${fmtDate(h.fecha)} a la ${h.bodega}, se identificaron las siguientes observaciones que requieren medidas correctivas para garantizar la higiene, seguridad y salvaguarda de las existencias:`);
      pdf.tabla([{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Criterio observado', w: 4 }, { header: 'Medida correctiva requerida', w: 5 }], no.map((x: any, i: number) => [i + 1, x.criterio, x.obs]));
      pdf.firmas([{ nombre: h.inspector, rol: 'SOLICITA' }, { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo.' }]);
      return pdf.buffer();
    },
  },
);
void addDays;
