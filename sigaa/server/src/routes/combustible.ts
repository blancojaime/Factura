import type { Ctx } from '../app.js';
import { fail } from '../core/errors.js';
import { isDate, today, txt } from '../core/util.js';
import { anularEmision, emitirVales, ejecutarMovimiento, movimientoPorRango, registrarDescargo, registrarRecepcion, resumenVales } from '../modules/combustible/vales.js';
import { conciliarProveedor, descargoViaje, despachoTurril, guardarCronograma, ingresoTurril, listarCronograma, registrarViaje, tablero } from '../modules/combustible/otros.js';
import { costoPromTurril, descargosPendientes, litrosMaximos, precioVigente, saldoTurril, ultimaLectura } from '../modules/combustible/base.js';
import { cfgAll } from '../core/services.js';
import { leerCobrosXlsx } from '../modules/combustible/cobros.js';

/** Rutas del módulo de Combustible (/api/com). */
export async function registerCombustible({ db, app, w }: Ctx) {
  const P = '/api/com';
  const W = { preHandler: w('com') };
  const q = (req: any) => req.query as Record<string, string>;
  const body = (req: any) => req.body as any;
  const nro = (req: any) => decodeURIComponent((req.params as any).nro);

  app.get(`${P}/tablero`, async (req) => tablero(db, q(req).gestion ? Number(q(req).gestion) : undefined));
  app.get(`${P}/resumen-vales`, async () => resumenVales(db));
  app.get(`${P}/meta`, async () => ({
    vehiculos: await db('com_vehiculos').where({ estado: 'Activo' }).orderBy('placa'),
    conductores: await db('com_conductores').where({ estado: 'Activo' }).orderBy('nombre'),
    puestos: await db('com_puestos').where({ estado: 'Activo' }).orderBy('codigo'),
    contratos: await db('com_contratos').orderBy('nro'),
    aperturas: await db('core_aperturas').orderBy('apertura'),
    unidades: await db('core_unidades').orderBy('nombre'),
    proveedores: await db('core_proveedores').orderBy('razon_social'),
    precios: await db('com_precios').orderBy(['combustible', 'vigente_desde']),
    cortes: (await cfgAll(db)).CORTES_VALE?.split(',').map(Number) ?? [30, 50, 100],
    config: await cfgAll(db),
  }));
  app.get(`${P}/precio`, async (req) => ({ precio: await precioVigente(db, q(req).combustible, q(req).fecha || today()) }));
  app.get(`${P}/litros-maximos`, async (req) => {
    const x = q(req);
    return { litros: await litrosMaximos(db, { placa: x.placa, destino: x.destino || 'VEHICULO', desde: x.desde, hasta: x.hasta, programado: Number(x.programado) || 0 }) };
  });
  app.get(`${P}/ultima-lectura`, async (req) => ({ lectura: await ultimaLectura(db, q(req).placa, q(req).fecha || today()) }));
  app.get(`${P}/descargos-pendientes`, async (req) => ({ pendientes: await descargosPendientes(db, q(req).conductor, q(req).fecha || today()) }));

  app.post(`${P}/recepciones`, W, async (req) => registrarRecepcion(db, req.usuario, body(req)));
  app.get(`${P}/lotes`, async () => db('com_lotes').orderBy('id_lote', 'desc').limit(500));
  app.get(`${P}/vales`, async (req) => {
    const x = q(req);
    const qb = db('com_vales').orderBy(['proveedor', 'combustible', 'corte', 'nro_vale']).limit(Math.min(Number(x.limite) || 500, 5000));
    for (const k of ['estado', 'combustible', 'placa', 'nro_emision', 'proveedor']) if (x[k]) qb.where(k, x[k]);
    if (x.corte) qb.where('corte', Number(x.corte));
    if (x.nro) qb.where('nro_vale', Number(x.nro));
    return qb;
  });

  app.get(`${P}/emisiones`, async (req) => {
    const x = q(req);
    const qb = db('com_emisiones').orderBy('nro', 'desc').limit(1000);
    if (x.estado) qb.where({ estado: x.estado });
    if (x.placa) qb.where({ placa: x.placa });
    if (isDate(x.desde)) qb.where('fecha', '>=', x.desde);
    if (isDate(x.hasta)) qb.where('fecha', '<=', x.hasta);
    return qb;
  });
  app.get(`${P}/emisiones/:nro`, async (req) => {
    const e = await db('com_emisiones').where({ nro: nro(req) }).first();
    if (!e) fail('La emisión no existe.');
    return { ...e, vales: await db('com_vales').where({ nro_emision: e.nro }).orderBy(['corte', 'nro_vale']) };
  });
  app.post(`${P}/emisiones`, W, async (req) => emitirVales(db, req.usuario, body(req)));
  app.post(`${P}/emisiones/:nro/anular`, W, async (req) => anularEmision(db, req.usuario, nro(req), body(req)?.motivo));
  app.post(`${P}/movimientos`, W, async (req) => movimientoPorRango(db, req.usuario, body(req)));

  app.get(`${P}/descargos`, async () => db('com_descargos').orderBy('nro', 'desc').limit(1000));
  app.get(`${P}/descargos/:nro`, async (req) => {
    const d = await db('com_descargos').where({ nro: nro(req) }).first();
    if (!d) fail('El descargo no existe.');
    return { ...d, lineas: await db('com_descargo_lineas').where({ nro: d.nro }).orderBy('id') };
  });
  app.post(`${P}/descargos`, W, async (req) => registrarDescargo(db, req.usuario, body(req)));

  app.get(`${P}/turriles`, async () => {
    const out = [];
    for (const p of await db('com_puestos').orderBy('codigo')) out.push({ ...p, saldo: await saldoTurril(db, p.codigo), costo_prom: await costoPromTurril(db, p.codigo) });
    return out;
  });
  app.post(`${P}/turriles/ingreso`, W, async (req) => ingresoTurril(db, req.usuario, body(req)));
  app.post(`${P}/turriles/despacho`, W, async (req) => despachoTurril(db, req.usuario, body(req)));
  app.get(`${P}/kardex`, async (req) => {
    const x = q(req);
    const qb = db('com_kardex').orderBy('id', 'desc').limit(1000);
    if (x.almacen) qb.where({ almacen: x.almacen });
    if (isDate(x.desde)) qb.where('fecha', '>=', x.desde);
    if (isDate(x.hasta)) qb.where('fecha', '<=', x.hasta);
    return qb;
  });

  app.get(`${P}/viajes`, async () => db('com_viajes').orderBy('nro', 'desc').limit(500));
  app.get(`${P}/viajes/:nro`, async (req) => {
    const v = await db('com_viajes').where({ nro: nro(req) }).first();
    if (!v) fail('El viaje no existe.');
    return { ...v, detalle: await db('com_viajes_det').where({ nro: v.nro }).orderBy('id') };
  });
  app.post(`${P}/viajes`, W, async (req) => registrarViaje(db, req.usuario, body(req)));
  app.post(`${P}/viajes/:nro/descargo`, W, async (req) => descargoViaje(db, req.usuario, { ...body(req), nro: nro(req) }));

  app.post(`${P}/conciliaciones`, W, async (req) => conciliarProveedor(db, req.usuario, body(req)));
  /** Lee el detalle de cobros del proveedor desde un .xlsx (columnas: Nº vale, Fecha, Placa, Litros, Monto, Factura). */
  app.post(`${P}/conciliaciones/leer-xlsx`, W, async (req) => {
    if (!Buffer.isBuffer(req.body) || !(req.body as Buffer).length) fail('Seleccione un archivo .xlsx.');
    return { cobros: await leerCobrosXlsx(req.body as Buffer) };
  });
  app.get(`${P}/conciliaciones`, async () => db('com_conciliaciones').select('nro', 'fecha', 'proveedor', 'desde', 'hasta').count({ lineas: '*' }).groupBy('nro', 'fecha', 'proveedor', 'desde', 'hasta').orderBy('nro', 'desc'));

  app.get(`${P}/cronograma`, async (req) => listarCronograma(db, q(req).mes));
  app.put(`${P}/cronograma`, W, async (req) => guardarCronograma(db, req.usuario, body(req)?.mes, body(req)?.filas ?? []));
  void ejecutarMovimiento;
  void txt;
}
