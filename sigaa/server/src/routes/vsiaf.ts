import type { Ctx } from '../app.js';
import {
  enviosDeActivo, guardarConfigVsiaf, guardarEquivalencias, importarLote, infoDestino, leerConfigVsiaf, listarEquivalencias, listarLotes, seleccionVsiaf, validarLote,
} from '../vsiaf/servicio.js';
import { armarLote } from '../vsiaf/adaptador.js';
import { TIPOS_EQUIV } from '../vsiaf/adaptador.js';
import { sendFile } from '../app.js';
import { informeExcel, libroExcel } from '../vsiaf/exportes.js';
import { BusinessError } from '../core/errors.js';

/** Envío de activos al VSIAF (/api/af/vsiaf). Escribir exige el rol de Activos Fijos (o ADMIN). */
export async function registerVsiaf({ db, app, w }: Ctx) {
  const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  const P = '/api/af/vsiaf';
  const W = { preHandler: w('af') };
  const q = (req: any) => req.query as Record<string, string>;
  const body = (req: any) => (req.body ?? {}) as any;

  app.get(`${P}/config`, async () => leerConfigVsiaf(db));
  app.put(`${P}/config`, W, async (req) => guardarConfigVsiaf(db, req.usuario, body(req)));
  app.get(`${P}/destino`, async (req) => infoDestino(db, q(req).ruta || undefined));

  app.get(`${P}/seleccion`, async (req) => {
    const x = q(req);
    return seleccionVsiaf(db, { desde: x.desde, hasta: x.hasta, id_cta: x.id_cta ? Number(x.id_cta) : undefined, cod_edif: x.cod_edif ? Number(x.cod_edif) : undefined, texto: x.texto, situacion: x.situacion, estado: (x.estado as any) || undefined, limite: x.limite ? Number(x.limite) : undefined });
  });

  app.get(`${P}/equivalencias`, async () => ({ tipos: TIPOS_EQUIV, items: await listarEquivalencias(db) }));
  app.put(`${P}/equivalencias`, W, async (req) => ({ tipos: TIPOS_EQUIV, items: await guardarEquivalencias(db, req.usuario, body(req).items) }));
  /** Equivalencias que faltan para el envío (con sugerencias), sin abrir el VSIAF. */
  app.post(`${P}/pendientes`, async (req) => {
    const r = await armarLote(db, body(req));
    return { faltantes: r.faltantes, omitidos: r.omitidos, resumen: r.resumen };
  });

  app.post(`${P}/validar`, W, async (req) => validarLote(db, req.usuario, body(req)));
  app.post(`${P}/importar`, W, async (req) => importarLote(db, req.usuario, body(req)));

  /** Libro Excel para el «Importador Excel → VSIAF» (no toca el VSIAF ni marca nada como enviado). */
  app.post(`${P}/exportar/libro`, W, async (req, reply) => {
    const r = await armarLote(db, body(req));
    const n = r.resumen.activos + r.resumen.transferencias + r.resumen.bajas;
    if (!n) throw new BusinessError('No hay nada que exportar: no hay activos pendientes ni movimientos nuevos.');
    return sendFile(reply, await libroExcel(r.libro, `${r.resumen.activos} activo(s), ${r.resumen.transferencias} transferencia(s), ${r.resumen.bajas} baja(s).`), XLSX, `SIGAA_para_VSIAF_${new Date().toISOString().slice(0, 10)}.xlsx`, false);
  });
  /** Informe de la vista previa (validación) en Excel. */
  app.post(`${P}/exportar/informe`, W, async (req, reply) => {
    const v = await validarLote(db, req.usuario, body(req));
    return sendFile(reply, await informeExcel(v, 'Informe de validación — envío SIGAA → VSIAF'), XLSX, `informe_validacion_${new Date().toISOString().slice(0, 10)}.xlsx`, false);
  });

  /** Informe de una importación ya hecha: se arma con el resultado que devolvió «importar». */
  app.post(`${P}/exportar/informe-importacion`, W, async (req, reply) => {
    const b = body(req);
    const v = b.validacion;
    if (!v || !Array.isArray(v.incidencias) || !v.resumen) throw new BusinessError('Falta el resultado de la importación.');
    v.faltantes ??= []; v.omitidos ??= []; v.totalesPorGrupo ??= []; v.calculos ??= {};
    return sendFile(reply, await informeExcel(v, `Informe de importación — lote ${b.lote ?? ''}`, [['Lote', b.lote ?? ''], ['Respaldo', b.respaldo ?? '']]), XLSX, `informe_importacion_${b.lote ?? ''}.xlsx`, false);
  });

  app.get(`${P}/lotes`, async () => listarLotes(db));
  app.get(`${P}/envios/:codigo`, async (req) => enviosDeActivo(db, decodeURIComponent((req.params as any).codigo)));
}
