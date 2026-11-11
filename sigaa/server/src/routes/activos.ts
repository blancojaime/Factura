import { today } from '../core/util.js';
import fs from 'node:fs';
import path from 'node:path';
import type { Ctx } from '../app.js';
import { sendFile } from '../app.js';
import { fail, NotFound } from '../core/errors.js';
import {
  activosDeFuncionario, buscarActivos, codificarActivos, disponiblesParaAsignar, generarAsignacion, guardarFicha, copiarFicha, guardarFoto, guardarIngresoAF, guardarSolicitud, indicadoresAF, kardexActivo, listarAsignaciones, listarIngresosAF,
  listarSolicitudes, marcarEtiquetas, obtenerActivo, obtenerAsignacion, obtenerIngresoAF, obtenerSolicitud, pendientesCodificar, procesarMovimientoAF, solicitudSinExistencia, TIPOS_INGRESO_AF,
} from '../modules/activos/service.js';
import { FOTOS_DIR, stickersPdf } from '../docs/activos.js';
import { estructuraActivos, importarActivosExcel, plantillaActivos } from '../modules/activos/importar.js';
import { cfgAll } from '../core/services.js';
import { formatoImagen } from '../core/logo.js';
import { actualizarLote, agregarCotizacion, aprobarLote, crearLote, editarCotizacion, elegibles, eliminarLote, FACTORES, guardarItem, guardarSoporte, listarLotes, marcarOperativo, obtenerLote, quitarCotizacion, quitarItem, REVAL_DIR } from '../modules/activos/revaluo.js';
import { anexosDocx, informeTecnicoDocx } from '../docs/revaluoDocx.js';

/** Rutas del módulo de Activos Fijos (/api/af). */
export async function registerActivos({ db, app, w }: Ctx) {
  const P = '/api/af';
  const W = { preHandler: w('af') };
  const q = (req: any) => req.query as Record<string, string>;
  const body = (req: any) => req.body as any;
  const nro = (req: any) => decodeURIComponent((req.params as any).nro);

  // Importación de activos desde Excel (las fotos se suben después, una a una, con el endpoint de fotos).
  app.get(`${P}/importar/estructura`, async () => estructuraActivos());
  app.get(`${P}/importar/plantilla`, async (_req, reply) => sendFile(reply, await plantillaActivos(db), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'plantilla_activos_fijos.xlsx', false));
  app.post(`${P}/importar`, W, async (req) => {
    if (!Buffer.isBuffer(req.body) || !(req.body as Buffer).length) fail('Seleccione un archivo .xlsx.');
    return importarActivosExcel(db, req.usuario, req.body as Buffer, q(req).confirmar === '1');
  });

  // ───────── Revalúo técnico (NC 4) ─────────
  const R = `${P}/revaluo`;
  const rid = (req: any) => Number((req.params as any).id);
  const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  app.get(`${R}/meta`, async () => ({ factores: FACTORES, estados: Object.keys(FACTORES), cuentas: await db('af_cuentas').orderBy('id_cta'), auxiliares: await db('af_auxiliares').orderBy(['id_cta', 'id_aux']) }));
  app.get(`${R}/bandeja`, async (req) => elegibles(db, { id_cta: q(req).id_cta ? Number(q(req).id_cta) : undefined, id_aux: q(req).id_aux ? Number(q(req).id_aux) : undefined, texto: q(req).texto, incluirEnLote: q(req).todos === '1' }));
  app.put(`${R}/operativo/:codigo`, W, async (req) => marcarOperativo(db, req.usuario, decodeURIComponent((req.params as any).codigo), body(req).operativo, body(req).motivo));
  app.get(`${R}/lotes`, async () => listarLotes(db));
  app.post(`${R}/lotes`, W, async (req) => crearLote(db, req.usuario, body(req)));
  app.get(`${R}/lotes/:id`, async (req) => obtenerLote(db, rid(req)));
  app.put(`${R}/lotes/:id`, W, async (req) => actualizarLote(db, req.usuario, rid(req), body(req)));
  app.delete(`${R}/lotes/:id`, W, async (req) => eliminarLote(db, req.usuario, rid(req)));
  app.post(`${R}/lotes/:id/aprobar`, W, async (req) => aprobarLote(db, req.usuario, rid(req), body(req)));
  app.get(`${R}/lotes/:id/informe`, async (req, reply) => sendFile(reply, await informeTecnicoDocx(db, rid(req)), DOCX, `Informe_Tecnico_Revaluo_${rid(req)}.docx`, false));
  app.get(`${R}/lotes/:id/anexos`, async (req, reply) => sendFile(reply, await anexosDocx(db, rid(req)), DOCX, `Anexos_Revaluo_${rid(req)}.docx`, false));
  app.put(`${R}/items/:id`, W, async (req) => guardarItem(db, req.usuario, rid(req), body(req)));
  app.delete(`${R}/items/:id`, W, async (req) => quitarItem(db, req.usuario, rid(req)));
  app.post(`${R}/items/:id/cotizaciones`, W, async (req) => agregarCotizacion(db, req.usuario, rid(req), body(req)));
  app.put(`${R}/cotizaciones/:id`, W, async (req) => editarCotizacion(db, req.usuario, rid(req), body(req)));
  app.delete(`${R}/cotizaciones/:id`, W, async (req) => quitarCotizacion(db, req.usuario, rid(req)));
  app.put(`${R}/cotizaciones/:id/soporte`, W, async (req) => guardarSoporte(db, req.usuario, rid(req), req.body));
  app.get(`${R}/soporte/:archivo`, async (req, reply) => {
    const f = path.basename((req.params as any).archivo);
    const p = path.join(REVAL_DIR(), f);
    if (!fs.existsSync(p)) throw new NotFound('El archivo de soporte no existe.');
    return sendFile(reply, fs.readFileSync(p), f.endsWith('.pdf') ? 'application/pdf' : f.endsWith('.png') ? 'image/png' : 'image/jpeg', f);
  });

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
  // Copia la ficha técnica de un activo a otros (lote de bienes iguales). Las fotografías se copian como archivos propios.
  app.post(`${P}/activos/:codigo/copiar-ficha`, W, async (req) => {
    const copiarArchivo = (archivo: string, destino: string, n: number) => {
      const src = path.join(FOTOS_DIR(), path.basename(archivo));
      if (!fs.existsSync(src)) return null;
      const ext = path.extname(src) || '.jpg';
      const nuevo = `${destino}_${n}${ext}`;
      fs.mkdirSync(FOTOS_DIR(), { recursive: true });
      fs.copyFileSync(src, path.join(FOTOS_DIR(), nuevo));
      return nuevo;
    };
    return copiarFicha(db, req.usuario, { ...body(req), origen: (req.params as any).codigo }, copiarArchivo);
  });
  app.get(`${P}/activos/:codigo/kardex`, async (req) => kardexActivo(db, (req.params as any).codigo));

  // Fotografías (hasta 4 por activo): se suben como imagen binaria.
  app.put(`${P}/activos/:codigo/foto/:n`, W, async (req) => {
    const { codigo, n } = req.params as { codigo: string; n: string };
    // El número y el formato se validan ANTES de tocar el disco: nada del nombre viene tal cual del cliente.
    const nn = Number(n);
    if (!/^[1-4]$/.test(n) || !Number.isInteger(nn)) fail('Las fotografías van del 1 al 4.');
    if (!Buffer.isBuffer(req.body) || !(req.body as Buffer).length) fail('Seleccione una imagen (JPG o PNG).');
    if ((req.body as Buffer).length > 8 * 1024 * 1024) fail('La imagen supera 8 MB.');
    const ext = formatoImagen(req.body as Buffer);
    if (!ext) fail('El archivo no es una imagen válida (JPG, PNG o WEBP).');
    await obtenerActivo(db, codigo);
    fs.mkdirSync(FOTOS_DIR(), { recursive: true });
    const file = `${codigo.replace(/[^A-Za-z0-9._-]+/g, '_')}_${nn}.${ext}`;
    fs.writeFileSync(path.join(FOTOS_DIR(), file), req.body as Buffer);
    await guardarFoto(db, req.usuario, codigo, nn, file);
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
    return sendFile(reply, buf, 'application/pdf', `stickers-${today()}.pdf`);
  });
  app.get(`${P}/stickers`, async (req, reply) => {
    const codigos = String(q(req).codigos || '').split(',').filter(Boolean);
    return sendFile(reply, await stickersPdf(db, codigos), 'application/pdf', 'stickers.pdf');
  });
}
