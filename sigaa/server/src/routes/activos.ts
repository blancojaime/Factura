import fs from 'node:fs';
import path from 'node:path';
import type { Ctx } from '../app.js';
import { sendFile } from '../app.js';
import { fail, NotFound } from '../core/errors.js';
import {
  activosDeFuncionario, buscarActivos, codificarActivos, disponiblesParaAsignar, generarAsignacion, guardarFicha, guardarFoto, guardarIngresoAF, guardarSolicitud, indicadoresAF, kardexActivo, listarAsignaciones, listarIngresosAF,
  listarSolicitudes, marcarEtiquetas, obtenerActivo, obtenerAsignacion, obtenerIngresoAF, obtenerSolicitud, pendientesCodificar, procesarMovimientoAF, solicitudSinExistencia, TIPOS_INGRESO_AF,
} from '../modules/activos/service.js';
import { FOTOS_DIR, stickersPdf } from '../docs/activos.js';
import { cfgAll } from '../core/services.js';

/** Rutas del módulo de Activos Fijos (/api/af). */
export async function registerActivos({ db, app, w }: Ctx) {
  const P = '/api/af';
  const W = { preHandler: w('af') };
  const q = (req: any) => req.query as Record<string, string>;
  const body = (req: any) => req.body as any;
  const nro = (req: any) => decodeURIComponent((req.params as any).nro);

  app.get(`${P}/indicadores`, async () => indicadoresAF(db));
  app.get(`${P}/meta`, async () => ({
    cuentas: await db('af_cuentas').orderBy('id_cta'),
    auxiliares: await db('af_auxiliares').orderBy(['id_cta', 'id_aux']),
    edificios: await db('af_edificios').orderBy('cod_edif'),
    ambientes: await db('af_ambientes').orderBy(['cod_edif', 'cod_amb']),
    estados: await db('af_estados').orderBy('cod'),
    funcionarios: await db('core_funcionarios').where({ estado: 'ACTIVO' }).orderBy('nombre'),
    unidades: await db('core_unidades').orderBy('nombre'),
    proveedores: await db('core_proveedores').orderBy('razon_social'),
    tipos_ingreso: TIPOS_INGRESO_AF,
    config: await cfgAll(db),
  }));

  app.get(`${P}/activos`, async (req) => {
    const x = q(req);
    return buscarActivos(db, { texto: x.texto, situacion: x.situacion, funcionario: x.funcionario, cod_edif: x.cod_edif ? Number(x.cod_edif) : undefined, cod_amb: x.cod_amb as any, id_cta: x.id_cta ? Number(x.id_cta) : undefined, id_aux: x.id_aux ? Number(x.id_aux) : undefined, limite: x.limite ? Number(x.limite) : undefined });
  });
  app.get(`${P}/activos/:codigo`, async (req) => obtenerActivo(db, (req.params as any).codigo));
  app.put(`${P}/activos/:codigo`, W, async (req) => guardarFicha(db, req.usuario, (req.params as any).codigo, body(req)));
  app.get(`${P}/activos/:codigo/kardex`, async (req) => kardexActivo(db, (req.params as any).codigo));

  // Fotografías (hasta 4 por activo): se suben como imagen binaria.
  app.put(`${P}/activos/:codigo/foto/:n`, W, async (req) => {
    const { codigo, n } = req.params as { codigo: string; n: string };
    const ct = String(req.headers['content-type'] || '');
    const ext = ct.includes('png') ? 'png' : ct.includes('webp') ? 'webp' : 'jpg';
    if (!Buffer.isBuffer(req.body) || !(req.body as Buffer).length) fail('Seleccione una imagen (JPG o PNG).');
    if ((req.body as Buffer).length > 8 * 1024 * 1024) fail('La imagen supera 8 MB.');
    await obtenerActivo(db, codigo);
    fs.mkdirSync(FOTOS_DIR(), { recursive: true });
    const file = `${codigo}_${n}.${ext}`;
    fs.writeFileSync(path.join(FOTOS_DIR(), file), req.body as Buffer);
    await guardarFoto(db, req.usuario, codigo, Number(n), file);
    return { archivo: file };
  });
  app.delete(`${P}/activos/:codigo/foto/:n`, W, async (req) => {
    const { codigo, n } = req.params as { codigo: string; n: string };
    await guardarFoto(db, req.usuario, codigo, Number(n), null);
    return { ok: true };
  });
  app.get(`${P}/fotos/:archivo`, async (req, reply) => {
    const f = path.basename((req.params as any).archivo);
    const p = path.join(FOTOS_DIR(), f);
    if (!fs.existsSync(p)) throw new NotFound('La fotografía no existe.');
    return sendFile(reply, fs.readFileSync(p), f.endsWith('png') ? 'image/png' : f.endsWith('webp') ? 'image/webp' : 'image/jpeg', f);
  });

  app.get(`${P}/ingresos`, async () => listarIngresosAF(db));
  app.get(`${P}/ingresos/:nro`, async (req) => obtenerIngresoAF(db, nro(req)));
  app.get(`${P}/ingresos/:nro/pendientes`, async (req) => pendientesCodificar(db, nro(req)));
  app.post(`${P}/ingresos`, W, async (req) => guardarIngresoAF(db, req.usuario, body(req)));
  app.post(`${P}/codificar`, W, async (req) => codificarActivos(db, req.usuario, body(req)));

  app.get(`${P}/solicitudes`, async () => listarSolicitudes(db));
  app.get(`${P}/solicitudes/:nro`, async (req) => obtenerSolicitud(db, nro(req)));
  app.post(`${P}/solicitudes`, W, async (req) => guardarSolicitud(db, req.usuario, body(req)));
  app.post(`${P}/solicitudes/:nro/sin-existencia`, W, async (req) => solicitudSinExistencia(db, req.usuario, nro(req)));

  app.get(`${P}/asignaciones`, async () => listarAsignaciones(db));
  app.get(`${P}/asignaciones/disponibles`, async (req) => disponiblesParaAsignar(db, { nro_sol: q(req).nro_sol, id_cta: q(req).id_cta ? Number(q(req).id_cta) : undefined, id_aux: q(req).id_aux ? Number(q(req).id_aux) : undefined }));
  app.get(`${P}/asignaciones/:nro`, async (req) => obtenerAsignacion(db, nro(req)));
  app.post(`${P}/asignaciones`, W, async (req) => generarAsignacion(db, req.usuario, body(req)));

  app.post(`${P}/movimientos`, W, async (req) => procesarMovimientoAF(db, req.usuario, body(req)));
  app.get(`${P}/funcionarios/:nombre/activos`, async (req) => activosDeFuncionario(db, decodeURIComponent((req.params as any).nombre)));
  app.get(`${P}/movimientos`, async (req) => {
    const x = q(req);
    const qb = db('af_movimientos').orderBy('id', 'desc').limit(1000);
    if (x.tipo) qb.where({ tipo: x.tipo });
    if (x.documento) qb.where({ documento: x.documento });
    return qb;
  });

  app.post(`${P}/stickers`, W, async (req, reply) => {
    const codigos = (body(req)?.codigos ?? []) as string[];
    const buf = await stickersPdf(db, codigos);
    if (body(req)?.marcar !== false) await marcarEtiquetas(db, req.usuario, codigos);
    return sendFile(reply, buf, 'application/pdf', `stickers-${new Date().toISOString().slice(0, 10)}.pdf`);
  });
  app.get(`${P}/stickers`, async (req, reply) => {
    const codigos = String(q(req).codigos || '').split(',').filter(Boolean);
    return sendFile(reply, await stickersPdf(db, codigos), 'application/pdf', 'stickers.pdf');
  });
}
