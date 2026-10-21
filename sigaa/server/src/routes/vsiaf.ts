import type { Ctx } from '../app.js';
import {
  enviosDeActivo, guardarConfigVsiaf, guardarEquivalencias, importarLote, infoDestino, leerConfigVsiaf, listarEquivalencias, listarLotes, seleccionVsiaf, validarLote,
} from '../vsiaf/servicio.js';
import { armarLote } from '../vsiaf/adaptador.js';
import { TIPOS_EQUIV } from '../vsiaf/adaptador.js';

/** Envío de activos al VSIAF (/api/af/vsiaf). Escribir exige el rol de Activos Fijos (o ADMIN). */
export async function registerVsiaf({ db, app, w }: Ctx) {
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

  app.get(`${P}/lotes`, async () => listarLotes(db));
  app.get(`${P}/envios/:codigo`, async (req) => enviosDeActivo(db, decodeURIComponent((req.params as any).codigo)));
}
