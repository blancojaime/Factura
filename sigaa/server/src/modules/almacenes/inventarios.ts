import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, txt, today } from '../../core/util.js';
import { cfg, siguienteNro } from '../../core/services.js';
import { bitacoraUsuario, requerirBodega } from './helpers.js';
import { stockDe, ultimoPrecio, precioPromedio } from './stock.js';
import { docsRequeridos } from './ingresos.js';

export const TIPOS_INVENTARIO = ['PROGRAMADO', 'SORPRESIVO', 'POR CAMBIO DE ENCARGADO', 'ANUAL DE CIERRE DE GESTIÓN'];

/** Abre un inventario cargando los ítems activos de la bodega con su saldo del sistema (corte de documentación). */
export async function nuevoInventario(
  db: Db,
  u: Usuario,
  d: { fecha: string; cod_bod: string; tipo: string; responsable?: string; designado?: string; observador?: string; filtro_subgrupo?: string },
) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha del inventario.');
  e.add(!TIPOS_INVENTARIO.includes(txt(d.tipo)), 'Seleccione el tipo de inventario.');
  e.throwIfAny('Inventario incompleto:');
  const bod = await requerirBodega(db, d.cod_bod);
  return db.transaction(async (trx) => {
    const q = trx('alm_catalogo').whereNot({ estado: 'INACTIVO' }).where({ cod_bod: bod }).orderBy('codigo');
    if (d.filtro_subgrupo) {
      const [g, s] = d.filtro_subgrupo.split('-').map(Number);
      q.where({ grupo: g, subgrupo: s });
    }
    const items = await q;
    if (!items.length) fail('No hay ítems activos en la bodega para el filtro indicado.');
    const nro = await siguienteNro(trx, 'INV');
    const ing = await trx('alm_ingresos').where({ cod_bod: bod, estado: 'INGRESADO' }).orderBy('nro', 'desc').first('nro');
    const sal = await trx('alm_salidas').where({ cod_bod: bod, estado: 'ENTREGADO' }).orderBy('nro', 'desc').first('nro');
    await trx('alm_inventarios').insert({
      nro,
      fecha: d.fecha,
      cod_bod: bod,
      tipo: d.tipo,
      responsable: txt(d.responsable) || (await cfg(trx, 'NombreALM')),
      designado: txt(d.designado),
      observador: txt(d.observador),
      corte_ing: ing ? `Últ. ingreso: ${ing.nro}` : '',
      corte_sal: sal ? `Últ. vale de salida: ${sal.nro}` : '',
      filtro_subgrupo: txt(d.filtro_subgrupo),
      estado: 'EN CONTEO',
      faltante_bs: 0,
      sobrante_bs: 0,
      fecha_reg: nowIso(),
    });
    let k = 0;
    for (const it of items) {
      await trx('alm_inventarios_det').insert({
        nro,
        item: ++k,
        cod_item: it.codigo,
        descripcion: it.descripcion,
        unidad: it.unidad,
        saldo_sist: await stockDe(trx, bod, it.codigo),
        conteo: null,
        diferencia: 0,
        precio_unit: await precioPromedio(trx, bod, it.codigo),
        estado_bien: '',
        obs: '',
      });
    }
    await bitacoraUsuario(trx, u, 'APERTURA DE INVENTARIO', nro, `${d.tipo} - ${bod} - ${k} ítems`);
    return { nro, items: k };
  });
}

export async function guardarConteo(db: Db, u: Usuario, nro: string, lineas: { cod_item: string; conteo: number | null; estado_bien?: string; obs?: string }[]) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_inventarios').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el inventario ${nro}.`);
    if (h.estado === 'CERRADO') fail('El inventario está CERRADO y no puede modificarse.');
    for (const l of lineas) {
      const det = await trx('alm_inventarios_det').where({ nro, cod_item: l.cod_item }).first();
      if (!det) fail(`El ítem ${l.cod_item} no pertenece al inventario.`);
      const conteo = l.conteo === null || l.conteo === undefined || (l.conteo as any) === '' ? null : num(l.conteo);
      if (conteo !== null && conteo < 0) fail(`Ítem ${l.cod_item}: el conteo no puede ser negativo.`);
      await trx('alm_inventarios_det')
        .where({ id: det.id })
        .update({ conteo, diferencia: conteo === null ? 0 : round(conteo - num(det.saldo_sist), 6), estado_bien: txt(l.estado_bien), obs: txt(l.obs) });
    }
    return resumen(trx, nro);
  });
}

async function resumen(db: Db, nro: string) {
  const det = await db('alm_inventarios_det').where({ nro });
  let falt = 0;
  let sobr = 0;
  let contados = 0;
  for (const x of det) {
    if (x.conteo === null || x.conteo === undefined) continue;
    contados++;
    const v = round(num(x.diferencia) * num(x.precio_unit), 2);
    if (v < 0) falt += -v;
    else sobr += v;
  }
  await db('alm_inventarios').where({ nro }).update({ faltante_bs: round(falt, 2), sobrante_bs: round(sobr, 2) });
  return { nro, contados, total: det.length, faltante_bs: round(falt, 2), sobrante_bs: round(sobr, 2) };
}

/** Cierra el inventario: todos los ítems contados y sin movimientos posteriores al corte (art. 28). */
export async function cerrarInventario(db: Db, u: Usuario, nro: string) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_inventarios').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el inventario ${nro}.`);
    if (h.estado === 'CERRADO') fail('El inventario ya está cerrado.');
    const det = await trx('alm_inventarios_det').where({ nro });
    const sinContar = det.filter((x: any) => x.conteo === null || x.conteo === undefined);
    if (sinContar.length) fail(`Faltan ${sinContar.length} ítem(s) por contar (p. ej. ${sinContar[0].cod_item}). Registre el conteo físico de todos los ítems.`);
    const movidos: string[] = [];
    for (const x of det) if (Math.abs((await stockDe(trx, h.cod_bod, x.cod_item)) - num(x.saldo_sist)) > 1e-6) movidos.push(x.cod_item);
    if (movidos.length)
      fail(`Hubo movimientos en la bodega después del corte para ${movidos.length} ítem(s) (art. 28): ${movidos.slice(0, 5).join(', ')}. Reabra el inventario o actualice los saldos y repita el conteo de esos ítems.`);
    const r = await resumen(trx, nro);
    await trx('alm_inventarios').where({ nro }).update({ estado: 'CERRADO' });
    await bitacoraUsuario(trx, u, 'CIERRE DE INVENTARIO', nro, `Faltantes Bs ${r.faltante_bs} / Sobrantes Bs ${r.sobrante_bs}`);
    return { ...r, estado: 'CERRADO' };
  });
}

/** Actualiza los saldos del sistema de los ítems aún no contados (cuando hubo movimientos tras la apertura). */
export async function actualizarSaldos(db: Db, nro: string) {
  const h = await db('alm_inventarios').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el inventario ${nro}.`);
  if (h.estado === 'CERRADO') fail('El inventario está CERRADO.');
  const det = await db('alm_inventarios_det').where({ nro });
  for (const x of det) {
    const s = await stockDe(db, h.cod_bod, x.cod_item);
    if (Math.abs(s - num(x.saldo_sist)) > 1e-6)
      await db('alm_inventarios_det').where({ id: x.id }).update({ saldo_sist: s, diferencia: x.conteo === null ? 0 : round(num(x.conteo) - s, 6) });
  }
  return resumen(db, nro);
}

/** Sobrantes → ingreso de ajuste valorado al último precio de compra (cotización de un bien similar). */
export async function ingresarSobrantes(db: Db, u: Usuario, nro: string) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_inventarios').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el inventario ${nro}.`);
    if (h.estado !== 'CERRADO') fail('Cierre el inventario antes de regularizar sobrantes.');
    const det = (await trx('alm_inventarios_det').where({ nro })).filter((x: any) => num(x.diferencia) > 1e-6);
    if (!det.length) fail('El inventario no tiene sobrantes.');
    const yaGenerado = await trx('alm_ingresos').where({ tipo: 'AJUSTE - SOBRANTE DE INVENTARIO', proyecto: `Sobrantes del inventario ${nro}` }).whereNot({ estado: 'ANULADO' }).first();
    if (yaGenerado) fail(`Los sobrantes de este inventario ya generaron el ingreso ${yaGenerado.nro}.`);
    const cgi = await siguienteNro(trx, 'CGI');
    let tot = 0;
    let k = 0;
    for (const x of det) {
      const pu = (await ultimoPrecio(trx, x.cod_item)) || 0.01;
      const t = round(num(x.diferencia) * pu, 2);
      tot += t;
      await trx('alm_ingresos_det').insert({ nro: cgi, item: ++k, cod_item: x.cod_item, descripcion: x.descripcion, unidad: x.unidad, cantidad: x.diferencia, precio_unit: pu, total: t });
    }
    const tipo = 'AJUSTE - SOBRANTE DE INVENTARIO';
    await trx('alm_ingresos').insert({
      nro: cgi, fecha: today(), cod_bod: h.cod_bod, tipo, proyecto: `Sobrantes del inventario ${nro}`, comision: await cfg(trx, 'NombreALM'),
      obs_plazo: `Generado desde el inventario ${nro}`, total: tot, estado: 'REGISTRADO', fecha_reg: nowIso(), usuario: u.usuario,
    });
    let o = 0;
    for (const dd of await docsRequeridos(trx, tipo)) await trx('alm_ingresos_doc').insert({ nro: cgi, orden: ++o, documento: dd.documento, estado: '' });
    await bitacoraUsuario(trx, u, 'SOBRANTES A CGI DE AJUSTE', nro, `${cgi} Bs ${tot.toFixed(2)}`);
    return { cgi, total: tot, items: k };
  });
}

/** Faltantes → expediente de baja por pérdida (el Manual exige reposición por el encargado o baja con responsabilidad). */
export async function bajaPorFaltante(db: Db, u: Usuario, nro: string) {
  const h = await db('alm_inventarios').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el inventario ${nro}.`);
  if (h.estado !== 'CERRADO') fail('Cierre el inventario antes de regularizar faltantes.');
  const det = (await db('alm_inventarios_det').where({ nro })).filter((x: any) => num(x.diferencia) < -1e-6);
  if (!det.length) fail('El inventario no tiene faltantes.');
  return {
    cod_bod: h.cod_bod,
    causal: 'Robo o pérdida fortuita',
    responsable: h.responsable,
    justificacion: `Faltantes detectados en el inventario ${nro} del ${h.fecha}. Se solicita la baja previo análisis de responsabilidad.`,
    items: det.map((x: any) => ({ cod_item: x.cod_item, cantidad: -num(x.diferencia) })),
  };
}

export async function obtenerInventario(db: Db, nro: string) {
  const h = await db('alm_inventarios as i').leftJoin('alm_bodegas as b', 'b.cod', 'i.cod_bod').where('i.nro', nro).select('i.*', 'b.nombre as bodega').first();
  if (!h) throw new NotFound(`No existe el inventario ${nro}.`);
  return { ...h, items: await db('alm_inventarios_det').where({ nro }).orderBy('item') };
}
export async function listarInventarios(db: Db) {
  return db('alm_inventarios as i').leftJoin('alm_bodegas as b', 'b.cod', 'i.cod_bod').select('i.*', 'b.nombre as bodega').orderBy('i.nro', 'desc');
}
