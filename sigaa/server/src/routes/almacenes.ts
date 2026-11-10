import type { Ctx } from '../app.js';
import { fail } from '../core/errors.js';
import { guardarItem, listarCatalogo, obtenerItem } from '../modules/almacenes/catalogo.js';
import { anularIngreso, confirmarIngreso, docsRequeridos, guardarIngreso, listarIngresos, obtenerIngreso } from '../modules/almacenes/ingresos.js';
import { anularSalida, aprobarSalida, aprobarYEntregar, entregarSalida, guardarSalida, listarSalidas, obtenerSalida, rechazarSalida, reglasPedido } from '../modules/almacenes/salidas.js';
import { actualizarSaldos, bajaPorFaltante, cerrarInventario, guardarConteo, ingresarSobrantes, listarInventarios, nuevoInventario, obtenerInventario, TIPOS_INVENTARIO } from '../modules/almacenes/inventarios.js';
import { anularBaja, concluirBaja, ejecutarBaja, guardarBaja, listarBajas, obtenerBaja, tramiteDeCausal } from '../modules/almacenes/bajas.js';
import { alertasSeguridad, calcularReposicion, CRITERIOS, ejecutarTransferencia, guardarInspeccion, guardarRequerimiento, guardarTransferencia, itemsSinMovimiento, listarInspecciones, listarRequerimientos, listarTransferencias, nuevaGestion, obtenerInspeccion, obtenerRequerimiento, obtenerTransferencia, verificarCierre } from '../modules/almacenes/otros.js';
import { kardex, lotesDeItem, saldosActuales } from '../modules/almacenes/stock.js';
import { dashboardAlm } from '../modules/almacenes/dashboard.js';
import { today, txt, num, round } from '../core/util.js';
import { cfgAll } from '../core/services.js';

/** Rutas del módulo de Almacenes (/api/alm). */
export async function registerAlmacenes({ db, app, w }: Ctx) {
  const P = '/api/alm';
  const W = { preHandler: w('alm') };
  const q = (req: any) => req.query as Record<string, string>;
  const body = (req: any) => req.body as any;
  const nro = (req: any) => decodeURIComponent((req.params as any).nro);

  app.get(`${P}/dashboard`, async () => dashboardAlm(db));
  app.get(`${P}/meta`, async () => ({
    bodegas: await db('alm_bodegas').orderBy('cod'),
    grupos: await db('alm_grupos').orderBy('grupo'),
    subgrupos: await db('alm_subgrupos').orderBy(['grupo', 'subgrupo']),
    unidades_medida: (await db('alm_unidades_medida').orderBy('nombre')).map((x: any) => x.nombre),
    partidas: await db('core_partidas').orderBy('partida'),
    causales: await db('alm_causales').orderBy(['grupo', 'causal']),
    tipos_ingreso: [...new Set((await db('alm_docreq').select('tipo')).map((x: any) => x.tipo))],
    tipos_inventario: TIPOS_INVENTARIO,
    tipos_requerimiento: ['PREVISTO - REPOSICIÓN DE STOCK', 'NO PREVISTO', 'SIN EXISTENCIA'],
    estados_bien: ['BUENO', 'DETERIORADO', 'VENCIDO', 'OBSOLETO', 'POCO MOVIMIENTO', 'DAÑADO'],
    criterios_inspeccion: CRITERIOS,
    config: await cfgAll(db),
  }));

  // Catálogo
  app.get(`${P}/catalogo`, async (req) => listarCatalogo(db, q(req)));
  app.get(`${P}/catalogo/:codigo`, async (req) => obtenerItem(db, (req.params as any).codigo));
  app.post(`${P}/catalogo`, W, async (req) => guardarItem(db, req.usuario, body(req)));

  // Existencias, lotes y kardex
  app.get(`${P}/existencias`, async (req) => {
    const bod = q(req).bod || '';
    const sal = await saldosActuales(db, bod);
    const cat = await db('alm_catalogo as c').leftJoin('alm_bodegas as b', 'b.cod', 'c.cod_bod').select('c.*', 'b.nombre as bodega').orderBy('c.codigo');
    return cat.filter((c: any) => !bod || c.cod_bod === bod).map((c: any) => {
      const s = sal.get(`${c.cod_bod}|${c.codigo}`);
      return { codigo: c.codigo, descripcion: c.descripcion, unidad: c.unidad, bodega: c.bodega, cod_bod: c.cod_bod, stock_min: c.stock_min, stock_max: c.stock_max, existencia: s?.cant ?? 0, valor: round(s?.bs ?? 0, 2), estado: c.estado };
    });
  });
  app.get(`${P}/lotes`, async (req) => lotesDeItem(db, q(req).bod, q(req).cod));
  app.get(`${P}/kardex`, async (req) => {
    const { bod, cod, desde, hasta } = q(req);
    if (!cod) fail('Seleccione el ítem.');
    return kardex(db, bod || '', cod, desde || `${today().slice(0, 4)}-01-01`, hasta || today());
  });
  app.get(`${P}/sin-movimiento`, async () => itemsSinMovimiento(db));

  // Ingresos (CGI)
  app.get(`${P}/ingresos`, async (req) => listarIngresos(db, q(req)));
  app.get(`${P}/ingresos/docs/:tipo`, async (req) => docsRequeridos(db, decodeURIComponent((req.params as any).tipo)));
  app.get(`${P}/ingresos/:nro`, async (req) => obtenerIngreso(db, nro(req)));
  app.post(`${P}/ingresos`, W, async (req) => guardarIngreso(db, req.usuario, body(req)));
  app.post(`${P}/ingresos/:nro/confirmar`, W, async (req) => confirmarIngreso(db, req.usuario, nro(req)));
  app.post(`${P}/ingresos/:nro/anular`, W, async (req) => anularIngreso(db, req.usuario, nro(req), body(req)?.motivo));

  // Salidas (vales)
  app.get(`${P}/salidas`, async (req) => listarSalidas(db, q(req)));
  app.get(`${P}/salidas/reglas`, async (req) => reglasPedido(db, q(req).fecha || today(), q(req).solicitante || '', q(req).nro || ''));
  app.get(`${P}/salidas/:nro`, async (req) => obtenerSalida(db, nro(req)));
  app.post(`${P}/salidas`, W, async (req) => guardarSalida(db, req.usuario, body(req)));
  app.post(`${P}/salidas/:nro/aprobar`, W, async (req) => aprobarSalida(db, req.usuario, nro(req)));
  app.post(`${P}/salidas/:nro/entregar`, W, async (req) => entregarSalida(db, req.usuario, nro(req)));
  app.post(`${P}/salidas/:nro/aprobar-entregar`, W, async (req) => aprobarYEntregar(db, req.usuario, nro(req)));
  app.post(`${P}/salidas/:nro/rechazar`, W, async (req) => rechazarSalida(db, req.usuario, nro(req), body(req)?.motivo));
  app.post(`${P}/salidas/:nro/anular`, W, async (req) => anularSalida(db, req.usuario, nro(req), body(req)?.motivo));

  // Inventarios
  app.get(`${P}/inventarios`, async () => listarInventarios(db));
  app.get(`${P}/inventarios/:nro`, async (req) => {
    const inv = await obtenerInventario(db, nro(req));
    // conteo ciego: el contador no ve el saldo del sistema mientras el inventario está en conteo
    if (inv.estado !== 'CERRADO' && (await cfgAll(db)).ConteoCiego !== 'NO') for (const it of inv.items) { (it as any).saldo_sist = null; (it as any).diferencia = null; }
    return inv;
  });
  app.post(`${P}/inventarios`, W, async (req) => nuevoInventario(db, req.usuario, body(req)));
  app.put(`${P}/inventarios/:nro/conteo`, W, async (req) => guardarConteo(db, req.usuario, nro(req), body(req)?.lineas ?? []));
  app.post(`${P}/inventarios/:nro/actualizar-saldos`, W, async (req) => actualizarSaldos(db, nro(req)));
  app.post(`${P}/inventarios/:nro/cerrar`, W, async (req) => cerrarInventario(db, req.usuario, nro(req)));
  app.post(`${P}/inventarios/:nro/sobrantes`, W, async (req) => ingresarSobrantes(db, req.usuario, nro(req)));
  app.get(`${P}/inventarios/:nro/baja-faltante`, async (req) => bajaPorFaltante(db, req.usuario, nro(req)));

  // Bajas
  app.get(`${P}/bajas`, async () => listarBajas(db));
  app.get(`${P}/bajas/tramite`, async (req) => tramiteDeCausal(db, q(req).causal));
  app.get(`${P}/bajas/:nro`, async (req) => obtenerBaja(db, nro(req)));
  app.post(`${P}/bajas`, W, async (req) => guardarBaja(db, req.usuario, body(req)));
  app.post(`${P}/bajas/:nro/ejecutar`, W, async (req) => ejecutarBaja(db, req.usuario, nro(req)));
  app.post(`${P}/bajas/:nro/concluir`, W, async (req) => concluirBaja(db, req.usuario, nro(req)));
  app.post(`${P}/bajas/:nro/anular`, W, async (req) => anularBaja(db, req.usuario, nro(req), body(req)?.motivo));

  // Transferencias
  app.get(`${P}/transferencias`, async () => listarTransferencias(db));
  app.get(`${P}/transferencias/:nro`, async (req) => obtenerTransferencia(db, nro(req)));
  app.post(`${P}/transferencias`, W, async (req) => guardarTransferencia(db, req.usuario, body(req)));
  app.post(`${P}/transferencias/:nro/ejecutar`, W, async (req) => ejecutarTransferencia(db, req.usuario, nro(req)));

  // Reposición / requerimientos
  app.get(`${P}/reposicion`, async (req) => calcularReposicion(db, q(req).bod || undefined));
  app.get(`${P}/requerimientos`, async () => listarRequerimientos(db));
  app.get(`${P}/requerimientos/:nro`, async (req) => obtenerRequerimiento(db, nro(req)));
  app.post(`${P}/requerimientos`, W, async (req) => guardarRequerimiento(db, req.usuario, body(req)));

  // Seguridad
  app.get(`${P}/inspecciones`, async () => listarInspecciones(db));
  app.get(`${P}/inspecciones/:nro`, async (req) => obtenerInspeccion(db, nro(req)));
  app.post(`${P}/inspecciones`, W, async (req) => guardarInspeccion(db, req.usuario, body(req)));
  app.get(`${P}/alertas-seguridad`, async () => alertasSeguridad(db));

  // Cierre de gestión
  app.get(`${P}/cierre`, async () => verificarCierre(db));
  app.post(`${P}/cierre/nueva-gestion`, W, async (req) => nuevaGestion(db, req.usuario));
  void txt;
  void num;
}
