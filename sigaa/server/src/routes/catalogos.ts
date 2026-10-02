import type { Ctx } from '../app.js';
import { sendFile } from '../app.js';
import { MAESTROS, actualizarMaestro, crearMaestro, eliminarMaestro, listarMaestro, maestroPorKey, opcionesRef } from '../modules/maestros.js';
import { REGISTRO, ejecutarReporte, renderTablaPdf, renderTablaXlsx } from '../reports/types.js';
import { DOCS } from '../docs/types.js';
import '../reports/almacenes.js';
import '../reports/combustible.js';
import '../reports/activos.js';
import '../docs/almacenes.js';
import '../docs/combustible.js';
import '../docs/activos.js';
import { fail, NotFound } from '../core/errors.js';
import { bitacora } from '../core/services.js';

/** Catálogos maestros (CRUD genérico), reportes y documentos PDF/Excel. */
export async function registerCatalogos({ db, app, w }: Ctx) {
  // ── Maestros ──
  app.get('/api/maestros', async () => MAESTROS.map((m) => ({ key: m.key, titulo: m.titulo, modulo: m.modulo, pk: m.pk, autoId: !!m.autoId, cols: m.cols })));
  app.get('/api/maestros/:key', async (req) => {
    const { key } = req.params as { key: string };
    const { q } = req.query as { q?: string };
    return listarMaestro(db, key, q);
  });
  app.get('/api/ref/:ref', async (req) => opcionesRef(db, (req.params as { ref: string }).ref));
  const idDe = (key: string, pk: string): Record<string, unknown> => {
    const m = maestroPorKey(key);
    const partes = decodeURIComponent(pk).split('~');
    return Object.fromEntries(m.pk.map((k, i) => [k, partes[i]]));
  };
  const permiso = async (req: any, key: string) => w(maestroPorKey(key).modulo)(req);
  app.post('/api/maestros/:key', async (req) => {
    const { key } = req.params as { key: string };
    await permiso(req, key);
    return crearMaestro(db, req.usuario, key, req.body as Record<string, unknown>);
  });
  app.put('/api/maestros/:key/:pk', async (req) => {
    const { key, pk } = req.params as { key: string; pk: string };
    await permiso(req, key);
    await actualizarMaestro(db, req.usuario, key, idDe(key, pk), req.body as Record<string, unknown>);
    return { ok: true };
  });
  app.delete('/api/maestros/:key/:pk', async (req) => {
    const { key, pk } = req.params as { key: string; pk: string };
    await permiso(req, key);
    await eliminarMaestro(db, req.usuario, key, idDe(key, pk));
    return { ok: true };
  });

  // ── Reportes ──
  app.get('/api/reportes', async () => [...REGISTRO.values()].map((r) => ({ id: r.id, nombre: r.nombre, modulo: r.modulo, params: r.params })));
  app.get('/api/reportes/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    const q = req.query as Record<string, string>;
    const { rep, tabla } = await ejecutarReporte(db, id, q);
    const formato = (q.formato || 'json').toLowerCase();
    const base = `${rep.id}-${new Date().toISOString().slice(0, 10)}`;
    if (formato === 'pdf') return sendFile(reply, await renderTablaPdf(db, tabla), 'application/pdf', `${base}.pdf`);
    if (formato === 'xlsx' || formato === 'excel') return sendFile(reply, await renderTablaXlsx(db, tabla), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', `${base}.xlsx`, false);
    return { reporte: { id: rep.id, nombre: rep.nombre }, ...tabla };
  });

  // ── Documentos ──
  app.get('/api/documentos', async () => [...DOCS.values()].map((d) => ({ id: d.id, nombre: d.nombre, modulo: d.modulo, ref: d.ref })));
  app.get('/api/documentos/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    const q = req.query as Record<string, string>;
    const doc = DOCS.get(id);
    if (!doc) throw new NotFound(`El documento "${id}" no existe.`);
    if (!q.ref) fail(`Indique la referencia del documento (${doc.ref}).`);
    const buf = await doc.build(db, q.ref, q);
    await bitacora(db, req.usuario, doc.modulo === 'alm' ? 'ALMACENES' : doc.modulo === 'com' ? 'COMBUSTIBLE' : 'ACTIVOS FIJOS', 'IMPRESIÓN', q.ref, doc.nombre);
    return sendFile(reply, buf, 'application/pdf', `${id}-${q.ref.replace(/[^\w.-]+/g, '_')}.pdf`);
  });
}
