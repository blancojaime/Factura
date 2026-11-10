import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, txt, year, month } from '../../core/util.js';
import { cfg, cfgNum, siguienteNro } from '../../core/services.js';
import { bitacoraUsuario, requerirBodega } from './helpers.js';
import { anularMovimientos, consumirPEPS, stockDisponibleEntrega, stockDe } from './stock.js';

export interface SalidaInput {
  nro?: string;
  fecha_pedido: string;
  cod_bod: string;
  unidad: string;
  solicitante: string;
  cargo?: string;
  superior: string;
  proyecto?: string;
  nota_interna?: string;
  justificacion: string;
  observ?: string;
  excepcion?: string;
  items: { cod_item: string; cant_pedida: number; obs?: string }[];
}

/** Umbral de "cantidad elevada": lo mayor entre CantElevada y 25% del stock máximo del ítem. */
async function umbralElevado(db: Db, cod: string): Promise<number> {
  const u = await cfgNum(db, 'CantElevada', 50);
  const it = await db('alm_catalogo').where({ codigo: cod }).first('stock_max');
  return Math.max(u, 0.25 * num(it?.stock_max));
}

/** Reglas del Manual: pedidos del día 1 al 25 y máximo de pedidos por funcionario al mes. */
export async function reglasPedido(db: Db, fecha: string, solicitante: string, nro: string): Promise<string[]> {
  const w: string[] = [];
  const d1 = await cfgNum(db, 'DiaPedidoIni', 1);
  const d2 = await cfgNum(db, 'DiaPedidoFin', 25);
  const mx = await cfgNum(db, 'MaxPedidosMes', 1);
  const dia = Number(fecha.slice(8, 10));
  if (dia < d1 || dia > d2) w.push(`El pedido se registra fuera del plazo permitido (días ${d1} al ${d2} de cada mes).`);
  const rows = await db('alm_salidas').where({ solicitante }).whereNotIn('estado', ['ANULADO', 'RECHAZADO']).whereNot({ nro }).select('fecha_pedido');
  const n = rows.filter((r: any) => year(r.fecha_pedido) === year(fecha) && month(r.fecha_pedido) === month(fecha)).length;
  if (n >= mx) w.push(`El solicitante ya tiene ${n} pedido(s) este mes (máximo permitido: ${mx}).`);
  return w;
}

export async function nuevoVale(db: Db) {
  return siguienteNro(db, 'VS');
}

export async function guardarSalida(db: Db, u: Usuario, d: SalidaInput) {
  const e = new Errores();
  e.add(!isDate(d.fecha_pedido), 'Registre la fecha del pedido.');
  e.add(!txt(d.unidad), 'Seleccione la unidad solicitante.');
  e.add(!txt(d.solicitante), 'Seleccione al funcionario solicitante.');
  e.add(!txt(d.superior), 'Seleccione al inmediato superior que dará el Vo.Bo.');
  e.add(txt(d.superior).toUpperCase() === txt(d.solicitante).toUpperCase() && !!txt(d.solicitante), 'El inmediato superior no puede ser el mismo solicitante.');
  e.throwIfAny('Pedido incompleto:');
  const bod = await requerirBodega(db, d.cod_bod);
  return db.transaction(async (trx) => {
    let nro = txt(d.nro);
    if (nro) {
      const ex = await trx('alm_salidas').where({ nro }).first();
      if (ex && !['PEDIDO', 'APROBADO'].includes(ex.estado)) fail(`El vale ${nro} está ${ex.estado} y no puede modificarse.`);
    }
    const filas: any[] = [];
    const vistos = new Set<string>();
    let elevada = false;
    let j = 0;
    for (const it of d.items || []) {
      if (!txt(it.cod_item) && !num(it.cant_pedida)) continue;
      j++;
      const cod = txt(it.cod_item);
      const cat = await trx('alm_catalogo').where({ codigo: cod }).first();
      if (!cat) fail(`Ítem ${j}: el código '${cod}' no existe en el catálogo.`);
      if (vistos.has(cod)) fail(`Ítem ${j}: ${cod} está repetido en el pedido; sume las cantidades en una sola línea.`);
      vistos.add(cod);
      const cant = num(it.cant_pedida);
      if (!(cant > 0)) fail(`Ítem ${j}: registre la cantidad pedida.`);
      if (cant > (await umbralElevado(trx, cod))) elevada = true;
      filas.push({ item: j, cod_item: cod, descripcion: cat.descripcion, unidad: cat.unidad, cant_pedida: cant, cant_entregada: 0, precio_prom: 0, total: 0, obs: txt(it.obs) });
    }
    if (!filas.length) fail('Registre al menos un ítem en el pedido.');
    if (elevada && (!txt(d.nota_interna) || !txt(d.justificacion)))
      fail(`Hay cantidades elevadas (más de ${await cfgNum(trx, 'CantElevada', 50)} unidades o más del 25% del stock máximo del ítem). Registre el Nº de nota interna y la justificación (Manual 11).`);
    const w = await reglasPedido(trx, d.fecha_pedido, txt(d.solicitante), nro);
    if (w.length && !txt(d.excepcion))
      fail('El pedido no cumple las reglas del Manual:\n' + w.map((x) => '- ' + x).join('\n') + "\nSi corresponde una excepción, registre quién la autoriza en 'Excepción autorizada por'.");
    if (!txt(d.justificacion)) fail('Registre una breve justificación del pedido.');
    const cab = {
      fecha_pedido: d.fecha_pedido,
      cod_bod: bod,
      unidad: txt(d.unidad),
      solicitante: txt(d.solicitante),
      cargo: txt(d.cargo),
      superior: txt(d.superior),
      proyecto: txt(d.proyecto),
      nota_interna: txt(d.nota_interna),
      justificacion: txt(d.justificacion),
      observ: txt(d.observ),
      excepcion: txt(d.excepcion),
    };
    if (nro && (await trx('alm_salidas').where({ nro }).first())) {
      await trx('alm_salidas').where({ nro }).update(cab);
      await trx('alm_salidas_det').where({ nro }).delete();
    } else {
      nro = nro || (await siguienteNro(trx, 'VS'));
      await trx('alm_salidas').insert({ nro, ...cab, estado: 'PEDIDO', total: 0, fecha_reg: nowIso(), usuario: u.usuario });
    }
    for (const f of filas) await trx('alm_salidas_det').insert({ nro, ...f });
    await bitacoraUsuario(trx, u, 'REGISTRO DE PEDIDO', nro, `${cab.solicitante} - ${cab.unidad}${w.length ? ' [EXCEPCION: ' + cab.excepcion + ']' : ''}`);
    return { nro, advertencias: w };
  });
}

export async function aprobarSalida(db: Db, u: Usuario, nro: string) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_salidas').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el vale ${nro}.`);
    if (h.estado !== 'PEDIDO') fail(`Solo se pueden aprobar pedidos en estado PEDIDO (actual: ${h.estado}).`);
    await trx('alm_salidas').where({ nro }).update({ estado: 'APROBADO', fecha_aprob: nowIso(), aprobador: h.superior });
    await bitacoraUsuario(trx, u, 'APROBACIÓN DE PEDIDO', nro, h.superior);
    return { nro, estado: 'APROBADO' };
  });
}

export async function entregarSalida(db: Db, u: Usuario, nro: string) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_salidas').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el vale ${nro}.`);
    if (h.estado !== 'APROBADO') fail(`El pedido debe estar APROBADO para entregarse (actual: ${h.estado}). Prohibido entregar sin aprobación del inmediato superior.`);
    const ref = `${txt(h.unidad)} / ${txt(h.solicitante)}`;
    const det = await trx('alm_salidas_det').where({ nro }).orderBy('item');
    const hoy = nowIso().slice(0, 10);
    let tot = 0;
    let entregadas = 0;
    const sinStock: string[] = [];
    for (const x of det) {
      const cant = num(x.cant_pedida);
      const disp = await stockDisponibleEntrega(trx, h.cod_bod, x.cod_item, hoy);
      if (disp <= 1e-6) {
        sinStock.push(`${x.cod_item} ${String(x.descripcion).slice(0, 40)}`);
        await trx('alm_salidas_det').where({ id: x.id }).update({ cant_entregada: 0, precio_prom: 0, total: 0 });
        continue;
      }
      if (cant > disp + 1e-6) fail(`El ítem ${x.cod_item} solo tiene ${disp} disponible(s) (se excluyen lotes vencidos) y se pidieron ${cant}. Reduzca la cantidad pedida.`);
      const impo = await consumirPEPS(trx, u.usuario, { bod: h.cod_bod, cod: x.cod_item, cant, fecha: hoy, tipoMov: 'SALIDA', doc: nro, refer: ref });
      await trx('alm_salidas_det').where({ id: x.id }).update({ cant_entregada: cant, precio_prom: round(impo / cant, 4), total: round(impo, 2) });
      tot += round(impo, 2);
      entregadas++;
    }
    if (!entregadas) fail('Ningún ítem del pedido tiene existencia. Emita la Certificación de Inexistencia e inicie el requerimiento de compra.');
    await trx('alm_salidas').where({ nro }).update({ estado: 'ENTREGADO', fecha_entrega: nowIso(), entregador: (await cfg(trx, 'NombreALM')) || u.nombre, total: tot });
    await bitacoraUsuario(trx, u, 'ENTREGA DE MATERIALES', nro, `Bs ${tot.toFixed(2)} a ${ref}`);
    return { nro, estado: 'ENTREGADO', total: tot, sinExistencia: sinStock };
  });
}

export async function aprobarYEntregar(db: Db, u: Usuario, nro: string) {
  const h = await db('alm_salidas').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el vale ${nro}.`);
  if (h.estado === 'PEDIDO') await aprobarSalida(db, u, nro);
  return entregarSalida(db, u, nro);
}

export async function rechazarSalida(db: Db, u: Usuario, nro: string, motivo: string) {
  if (!txt(motivo)) fail('El rechazo requiere un motivo.');
  const h = await db('alm_salidas').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el vale ${nro}.`);
  if (!['PEDIDO', 'APROBADO'].includes(h.estado)) fail(`Solo se rechazan pedidos pendientes (actual: ${h.estado}).`);
  await db('alm_salidas').where({ nro }).update({ estado: 'RECHAZADO', motivo });
  await bitacoraUsuario(db, u, 'RECHAZO DE PEDIDO', nro, motivo);
  return { nro, estado: 'RECHAZADO' };
}

/** Anula un vale. Si ya fue entregado devuelve las existencias (solo para corregir errores de registro). */
export async function anularSalida(db: Db, u: Usuario, nro: string, motivo: string) {
  if (!txt(motivo)) fail('La anulación requiere un motivo.');
  return db.transaction(async (trx) => {
    const h = await trx('alm_salidas').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el vale ${nro}.`);
    if (h.estado === 'ANULADO') fail('El vale ya está anulado.');
    if (h.estado === 'ENTREGADO') await anularMovimientos(trx, nro);
    await trx('alm_salidas').where({ nro }).update({ estado: 'ANULADO', motivo });
    await bitacoraUsuario(trx, u, 'ANULACIÓN DE VALE', nro, motivo);
    return { nro, estado: 'ANULADO' };
  });
}

export async function obtenerSalida(db: Db, nro: string) {
  const h = await db('alm_salidas as s').leftJoin('alm_bodegas as b', 'b.cod', 's.cod_bod').where('s.nro', nro).select('s.*', 'b.nombre as bodega').first();
  if (!h) throw new NotFound(`No existe el vale ${nro}.`);
  const items = await db('alm_salidas_det').where({ nro }).orderBy('item');
  for (const it of items) (it as any).saldo_actual = await stockDe(db, h.cod_bod, it.cod_item);
  const pedidosMes = (await reglasPedido(db, h.fecha_pedido, h.solicitante, nro)).length;
  return { ...h, items, reglas_incumplidas: pedidosMes };
}

export async function listarSalidas(db: Db, f: { estado?: string; bod?: string; desde?: string; hasta?: string } = {}) {
  const q = db('alm_salidas as s').leftJoin('alm_bodegas as b', 'b.cod', 's.cod_bod').select('s.*', 'b.nombre as bodega').orderBy('s.nro', 'desc');
  if (f.estado) q.where('s.estado', f.estado);
  if (f.bod) q.where('s.cod_bod', f.bod);
  if (f.desde) q.where('s.fecha_pedido', '>=', f.desde);
  if (f.hasta) q.where('s.fecha_pedido', '<=', f.hasta);
  return q;
}
