/** Transferencias entre bodegas, requerimientos de reposición, seguridad/inspecciones y cierre de gestión. */
import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, today, txt, year, diffDays, addDays } from '../../core/util.js';
import { cfg, cfgNum, gestion, setCfg, siguienteNro } from '../../core/services.js';
import { bitacoraUsuario, requerirBodega } from './helpers.js';
import { altaLote, cerrarLote, precioPromedio, saldosActuales, stockDe, transferirLotes, ultimoMovimiento } from './stock.js';

// ───────────── TRANSFERENCIAS ─────────────
export async function guardarTransferencia(
  db: Db, u: Usuario,
  d: { nro?: string; fecha: string; bod_origen: string; bod_destino: string; entrega: string; recibe: string; motivo: string; items: { cod_item: string; cantidad: number }[] },
) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha.');
  e.add(!txt(d.entrega) || !txt(d.recibe), 'Registre quién entrega y quién recibe.');
  e.add(!txt(d.motivo), 'Registre el motivo de la transferencia.');
  e.throwIfAny('Transferencia incompleta:');
  const co = await requerirBodega(db, d.bod_origen);
  const cd = await requerirBodega(db, d.bod_destino);
  if (co === cd) fail('La bodega de origen y destino deben ser distintas.');
  return db.transaction(async (trx) => {
    let nro = txt(d.nro);
    if (nro) {
      const ex = await trx('alm_transferencias').where({ nro }).first();
      if (ex && ex.estado !== 'REGISTRADA') fail(`La transferencia está ${ex.estado} y no puede modificarse.`);
    }
    const filas: any[] = [];
    const vistos = new Set<string>();
    let tot = 0;
    let j = 0;
    for (const it of d.items || []) {
      if (!txt(it.cod_item)) continue;
      j++;
      const cod = txt(it.cod_item);
      const cat = await trx('alm_catalogo').where({ codigo: cod }).first();
      if (!cat) fail(`Ítem ${j}: el código '${cod}' no existe.`);
      if (vistos.has(cod)) fail(`Ítem ${j}: repetido.`);
      vistos.add(cod);
      const cant = num(it.cantidad);
      if (!(cant > 0)) fail(`Ítem ${j}: registre la cantidad.`);
      const s = await stockDe(trx, co, cod);
      if (cant > s + 1e-6) fail(`Ítem ${j}: la cantidad excede el saldo de la bodega de origen (${s}).`);
      const pu = await precioPromedio(trx, co, cod);
      const t = round(cant * pu, 2);
      tot += t;
      filas.push({ item: j, cod_item: cod, descripcion: cat.descripcion, unidad: cat.unidad, cantidad: cant, precio_unit: pu, total: t });
    }
    if (!filas.length) fail('Registre al menos un ítem.');
    const cab = { fecha: d.fecha, bod_origen: co, bod_destino: cd, entrega: txt(d.entrega), recibe: txt(d.recibe), motivo: txt(d.motivo), total: round(tot, 2) };
    if (nro && (await trx('alm_transferencias').where({ nro }).first())) {
      await trx('alm_transferencias').where({ nro }).update(cab);
      await trx('alm_transferencias_det').where({ nro }).delete();
    } else {
      nro = nro || (await siguienteNro(trx, 'TRF'));
      await trx('alm_transferencias').insert({ nro, ...cab, estado: 'REGISTRADA', fecha_reg: nowIso() });
    }
    for (const f of filas) await trx('alm_transferencias_det').insert({ nro, ...f });
    await bitacoraUsuario(trx, u, 'REGISTRO DE TRANSFERENCIA', nro, `${co} → ${cd} Bs ${tot.toFixed(2)}`);
    return { nro, total: round(tot, 2) };
  });
}

export async function ejecutarTransferencia(db: Db, u: Usuario, nro: string) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_transferencias').where({ nro }).first();
    if (!h) throw new NotFound('La transferencia aún no fue guardada.');
    if (h.estado !== 'REGISTRADA') fail(`La transferencia está ${h.estado}.`);
    const det = await trx('alm_transferencias_det').where({ nro });
    for (const x of det)
      await transferirLotes(trx, u.usuario, { bodOri: h.bod_origen, bodDes: h.bod_destino, cod: x.cod_item, cant: num(x.cantidad), fecha: h.fecha, doc: nro, refer: `${h.bod_origen} a ${h.bod_destino}` });
    await trx('alm_transferencias').where({ nro }).update({ estado: 'EJECUTADA' });
    await bitacoraUsuario(trx, u, 'TRANSFERENCIA EJECUTADA', nro, `Bs ${num(h.total).toFixed(2)}`);
    return { nro, estado: 'EJECUTADA' };
  });
}

export async function obtenerTransferencia(db: Db, nro: string) {
  const h = await db('alm_transferencias').where({ nro }).first();
  if (!h) throw new NotFound(`No existe la transferencia ${nro}.`);
  const bo = await db('alm_bodegas').where({ cod: h.bod_origen }).first('nombre');
  const bd = await db('alm_bodegas').where({ cod: h.bod_destino }).first('nombre');
  return { ...h, bodega_origen: bo?.nombre, bodega_destino: bd?.nombre, items: await db('alm_transferencias_det').where({ nro }).orderBy('item') };
}
export async function listarTransferencias(db: Db) {
  return db('alm_transferencias').orderBy('nro', 'desc');
}

// ───────────── REPOSICIÓN / REQUERIMIENTOS ─────────────
/** Ítems en o bajo el stock mínimo con cantidad sugerida = máximo - stock (o 2×mínimo - stock). */
export async function calcularReposicion(db: Db, bod?: string) {
  const sal = await saldosActuales(db, '');
  const q = db('alm_catalogo').whereNot({ estado: 'INACTIVO' }).orderBy('codigo');
  if (bod) q.where({ cod_bod: bod });
  const out: any[] = [];
  for (const it of await q) {
    const smin = num(it.stock_min);
    const smax = num(it.stock_max);
    const stk = sal.get(`${it.cod_bod}|${it.codigo}`)?.cant ?? 0;
    if (smin > 0 && stk <= smin) {
      let sug = smax > 0 ? smax - stk : 2 * smin - stk;
      if (sug < 1) sug = 1;
      out.push({ cod_item: it.codigo, descripcion: it.descripcion, unidad: it.unidad, stock: stk, minimo: smin, maximo: smax, sugerido: sug, cant_solic: sug, precio_ref: num(it.precio_ref), importe: round(sug * num(it.precio_ref), 2), partida: it.partida });
    }
  }
  return out;
}

export async function guardarRequerimiento(
  db: Db, u: Usuario,
  d: { nro?: string; fecha: string; bod?: string; tipo: string; justificacion: string; items: { cod_item: string; cant_solic: number }[] },
) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha.');
  e.add(!txt(d.tipo), 'Seleccione el tipo de requerimiento.');
  e.add(!txt(d.justificacion), 'Registre la justificación.');
  e.throwIfAny('Requerimiento incompleto:');
  const cb = txt(d.bod) && txt(d.bod).toUpperCase() !== 'TODAS' ? await requerirBodega(db, d.bod) : null;
  return db.transaction(async (trx) => {
    const filas: any[] = [];
    let tot = 0;
    let j = 0;
    for (const it of d.items || []) {
      const cant = num(it.cant_solic);
      if (!txt(it.cod_item) || !(cant > 0)) continue;
      const cat = await trx('alm_catalogo').where({ codigo: it.cod_item }).first();
      if (!cat) fail(`Ítem ${j + 1}: el código '${it.cod_item}' no existe.`);
      j++;
      const t = round(cant * num(cat.precio_ref), 2);
      tot += t;
      filas.push({ item: j, cod_item: cat.codigo, descripcion: cat.descripcion, unidad: cat.unidad, stock: await stockDe(trx, cat.cod_bod, cat.codigo), cant_solic: cant, precio_ref: cat.precio_ref, total: t, partida: cat.partida });
    }
    if (!filas.length) fail('El requerimiento no tiene ítems.');
    let nro = txt(d.nro);
    const cab = { fecha: d.fecha, cod_bod: cb, tipo: d.tipo, total: round(tot, 2), justificacion: txt(d.justificacion) };
    if (nro && (await trx('alm_requerimientos').where({ nro }).first())) {
      await trx('alm_requerimientos').where({ nro }).update(cab);
      await trx('alm_requerimientos_det').where({ nro }).delete();
    } else {
      nro = nro || (await siguienteNro(trx, 'REQ'));
      await trx('alm_requerimientos').insert({ nro, ...cab, estado: 'REGISTRADO', fecha_reg: nowIso() });
    }
    for (const f of filas) await trx('alm_requerimientos_det').insert({ nro, ...f });
    await bitacoraUsuario(trx, u, 'REQUERIMIENTO DE COMPRA', nro, `Bs ${tot.toFixed(2)} - ${filas.length} ítems`);
    return { nro, total: round(tot, 2) };
  });
}
export async function obtenerRequerimiento(db: Db, nro: string) {
  const h = await db('alm_requerimientos').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el requerimiento ${nro}.`);
  return { ...h, bodega: h.cod_bod ? txt((await db('alm_bodegas').where({ cod: h.cod_bod }).first('nombre'))?.nombre) : 'TODAS', items: await db('alm_requerimientos_det').where({ nro }).orderBy('item') };
}
export async function listarRequerimientos(db: Db) {
  return db('alm_requerimientos').orderBy('nro', 'desc');
}

// ───────────── SEGURIDAD / INSPECCIONES ─────────────
export const CRITERIOS = [
  'Materiales ordenados y clasificados según su naturaleza y peligrosidad',
  'Espacio libre para el movimiento y tránsito de los bienes',
  'Ventilación adecuada',
  'Iluminación adecuada',
  'Humedad y temperatura dentro de lo adecuado (sin filtraciones)',
  'Libre de plagas y roedores',
  'Extintores vigentes, con carga y accesibles',
  'Salidas y accesos de emergencia libres y señalizados',
  'Instalaciones eléctricas en buen estado',
  'Estantes y mobiliario en buen estado y estables',
  'Sustancias peligrosas en espacio separado y señalizado',
  'Equipo de protección personal disponible (guantes, barbijo, etc.)',
  'Botiquín de primeros auxilios completo',
  'Seguridad física: puertas, cerraduras y control de acceso',
  'Medidas contra incendios e inundaciones',
  'Medicamentos: almacenamiento y cadena de frío (bodega SUS)',
];

export async function guardarInspeccion(
  db: Db, u: Usuario,
  d: { nro?: string; fecha: string; cod_bod: string; inspector: string; items: { criterio: string; resultado: string; obs?: string }[] },
) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha.');
  e.add(!txt(d.inspector), 'Registre al inspector o responsable.');
  e.throwIfAny('Inspección incompleta:');
  const bod = await requerirBodega(db, d.cod_bod);
  return db.transaction(async (trx) => {
    let cumple = 0;
    let no = 0;
    let j = 0;
    for (const it of d.items) {
      j++;
      const r = txt(it.resultado).toUpperCase();
      if (!['CUMPLE', 'NO CUMPLE', 'N/A'].includes(r)) fail(`Criterio ${j}: registre el resultado (CUMPLE, NO CUMPLE o N/A).`);
      if (r === 'NO CUMPLE' && !txt(it.obs)) fail(`Criterio ${j}: registre la medida correctiva requerida.`);
      if (r === 'CUMPLE') cumple++;
      if (r === 'NO CUMPLE') no++;
    }
    let nro = txt(d.nro);
    const cab = { fecha: d.fecha, cod_bod: bod, inspector: txt(d.inspector), cumple, no_cumple: no };
    if (nro && (await trx('alm_inspecciones').where({ nro }).first())) {
      await trx('alm_inspecciones').where({ nro }).update(cab);
      await trx('alm_inspecciones_det').where({ nro }).delete();
    } else {
      nro = nro || (await siguienteNro(trx, 'INS'));
      await trx('alm_inspecciones').insert({ nro, ...cab, fecha_reg: nowIso() });
    }
    j = 0;
    for (const it of d.items) await trx('alm_inspecciones_det').insert({ nro, item: ++j, criterio: it.criterio, resultado: txt(it.resultado).toUpperCase(), obs: txt(it.obs) });
    await bitacoraUsuario(trx, u, 'INSPECCIÓN DE SEGURIDAD', nro, `Cumple ${cumple} / No cumple ${no}`);
    return { nro, cumple, no_cumple: no, porcentaje: cumple + no ? Math.round((cumple / (cumple + no)) * 100) : 0 };
  });
}
export async function obtenerInspeccion(db: Db, nro: string) {
  const h = await db('alm_inspecciones as i').leftJoin('alm_bodegas as b', 'b.cod', 'i.cod_bod').where('i.nro', nro).select('i.*', 'b.nombre as bodega').first();
  if (!h) throw new NotFound(`No existe la inspección ${nro}.`);
  return { ...h, items: await db('alm_inspecciones_det').where({ nro }).orderBy('item') };
}
export async function listarInspecciones(db: Db) {
  return db('alm_inspecciones as i').leftJoin('alm_bodegas as b', 'b.cod', 'i.cod_bod').select('i.*', 'b.nombre as bodega').orderBy('i.nro', 'desc');
}

/** Extintores y seguros con vencimiento vencido o próximo (DiasAlertaSeg). */
export async function alertasSeguridad(db: Db) {
  const dias = await cfgNum(db, 'DiasAlertaSeg', 30);
  const hoy = today();
  const lim = addDays(hoy, dias);
  const ext = await db('alm_extintores').where({ estado: 'ACTIVO' });
  const seg = await db('alm_seguros').where({ estado: 'VIGENTE' });
  return {
    extintoresVencidos: ext.filter((x: any) => x.venc_recarga && x.venc_recarga < hoy),
    extintoresPorVencer: ext.filter((x: any) => x.venc_recarga && x.venc_recarga >= hoy && x.venc_recarga <= lim),
    segurosVencidos: seg.filter((x: any) => x.hasta && x.hasta < hoy),
    segurosPorVencer: seg.filter((x: any) => x.hasta && x.hasta >= hoy && x.hasta <= lim),
  };
}

// ───────────── CIERRE DE GESTIÓN ─────────────
export interface Control {
  n: number;
  control: string;
  resultado: 'OK' | 'OBSERVADO';
  detalle: string;
  critico: boolean;
}

/** Verificaciones previas al cierre de gestión (10 controles del sistema original). */
export async function verificarCierre(db: Db): Promise<Control[]> {
  const g = await gestion(db);
  const out: Control[] = [];
  const add = (control: string, ok: boolean, detalle: string, critico: boolean) => out.push({ n: out.length + 1, control, resultado: ok ? 'OK' : 'OBSERVADO', detalle, critico });
  const bodegas = await db('alm_bodegas').where({ estado: 'ACTIVO' });
  const invs = await db('alm_inventarios');
  const anuales = invs.filter((i: any) => String(i.tipo).startsWith('ANUAL') && i.estado === 'CERRADO' && year(i.fecha) === g);
  const faltan = bodegas.filter((b: any) => !anuales.some((i: any) => i.cod_bod === b.cod)).map((b: any) => b.nombre);
  add('Inventario anual (100%) de cierre realizado y cerrado en cada bodega', faltan.length === 0, faltan.length ? 'Falta: ' + faltan.join('; ').slice(0, 160) : 'Todas las bodegas tienen inventario anual cerrado.', true);
  const abiertos = invs.filter((i: any) => i.estado === 'EN CONTEO').length;
  add('Sin inventarios en conteo (abiertos)', abiertos === 0, `${abiertos} inventario(s) sin cerrar.`, false);
  const ped = Number((await db('alm_salidas').whereIn('estado', ['PEDIDO', 'APROBADO']).count({ n: '*' }).first())?.n);
  add('Sin pedidos de salida pendientes de aprobación o entrega (corte de documentación)', ped === 0, `${ped} pedido(s) pendiente(s).`, true);
  const ing = Number((await db('alm_ingresos').where({ estado: 'REGISTRADO' }).count({ n: '*' }).first())?.n);
  add('Sin ingresos registrados pendientes de confirmar', ing === 0, `${ing} ingreso(s) pendiente(s).`, true);
  const baj = Number((await db('alm_bajas').where({ estado: 'EN TRÁMITE' }).count({ n: '*' }).first())?.n);
  add('Expedientes de baja sin ejecutar (se trasladan a la nueva gestión)', baj === 0, `${baj} expediente(s) en trámite; las existencias involucradas pasan como saldo inicial.`, false);
  const venc = Number((await db('alm_lotes').where({ estado: 'ACTIVO' }).where('saldo', '>', 1e-6).whereNotNull('vencimiento').where('vencimiento', '<', today()).count({ n: '*' }).first())?.n);
  add('Sin lotes vencidos con existencia (inicie baja por vencimiento)', venc === 0, `${venc} lote(s) vencido(s) con saldo.`, false);
  const dif = anuales.filter((i: any) => num(i.faltante_bs) > 0 || num(i.sobrante_bs) > 0).length;
  add('Diferencias de inventario anual resueltas (reposición, ingreso de sobrantes o baja)', dif === 0, `${dif} inventario(s) anual(es) con diferencias: verifique que estén regularizadas.`, false);
  add('Listado de ítems sin movimiento (obsolescencia) emitido', true, "Informativo: emita el reporte 'Ítems sin movimiento' antes del cierre.", false);
  add('Copia de seguridad de la base de datos realizada hoy', true, 'Use Administración → Copia de seguridad.', false);
  // Integridad kardex vs lotes
  const movs: any[] = await db('alm_movimientos').where((w) => w.whereNull('anulado').orWhere('anulado', '<>', 'SI')).groupBy('cod_bod', 'cod_item').select('cod_bod', 'cod_item').sum({ e: 'cant_ent', s: 'cant_sal' });
  const lotes: any[] = await db('alm_lotes').whereIn('estado', ['ACTIVO', 'AGOTADO', 'BAJA']).groupBy('cod_bod', 'cod_item').select('cod_bod', 'cod_item').sum({ s: 'saldo' });
  const lm = new Map(lotes.map((l: any) => [`${l.cod_bod}|${l.cod_item}`, num(l.s)]));
  const malos = movs.filter((m: any) => Math.abs(num(m.e) - num(m.s) - (lm.get(`${m.cod_bod}|${m.cod_item}`) ?? 0)) > 1e-4);
  add('Integridad: el saldo del kardex coincide con el saldo de los lotes', malos.length === 0, malos.length ? `${malos.length} ítem(s) con diferencia (p. ej. ${malos[0].cod_item}).` : 'Sin diferencias entre kardex y lotes.', true);
  // Controles críticos: 1, 3, 4, 10 (como el original)
  for (const k of [1, 3, 4, 10]) out[k - 1].critico = true;
  return out;
}

/**
 * Cierra la gestión actual y abre la siguiente en la misma base de datos:
 * traslada el saldo de cada lote activo como SALDO INICIAL y reinicia la numeración (nueva gestión).
 */
export async function nuevaGestion(db: Db, u: Usuario) {
  const controles = await verificarCierre(db);
  const crit = controles.filter((c) => c.critico && c.resultado === 'OBSERVADO');
  if (crit.length) fail(`Hay ${crit.length} control(es) crítico(s) observado(s). Regularice (inventario anual, pedidos/ingresos pendientes, integridad) antes de generar la nueva gestión.`);
  const g = (await gestion(db)) + 1;
  const fecha = `${g}-01-01`;
  return db.transaction(async (trx) => {
    const lotes = await trx('alm_lotes').where({ estado: 'ACTIVO' }).where('saldo', '>', 1e-6);
    // Cierra los lotes de la gestión anterior y abre lotes de saldo inicial (mismo vencimiento y precio)
    let n = 0;
    for (const l of lotes) {
      await cerrarLote(trx, u.usuario, l, `${g - 1}-12-31`, `CIERRE-${g - 1}`);
      const id = await altaLote(trx, u.usuario, { bod: l.cod_bod, cod: l.cod_item, docOrigen: `SALDO-${g}`, fechaIng: fecha, venc: l.vencimiento, cant: num(l.saldo), pu: num(l.precio_unit), tipoMov: 'SALDO INICIAL', refer: `Saldo inicial gestión ${g}` });
      await trx('alm_lotes').where({ id_lote: id }).update({ fecha_ing: l.fecha_ing }); // conserva la antigüedad para PEPS
      n++;
    }
    await setCfg(trx, 'Gestion', String(g));
    await bitacoraUsuario(trx, u, 'GENERACIÓN DE NUEVA GESTIÓN', String(g), `${n} lotes trasladados como saldo inicial`);
    return { gestion: g, lotes: n };
  });
}

export async function itemsSinMovimiento(db: Db) {
  const dias = await cfgNum(db, 'DiasSinMov', 730);
  const ult = await ultimoMovimiento(db);
  const sal = await saldosActuales(db, '');
  const hoy = today();
  const out: any[] = [];
  for (const [k, v] of sal) {
    const [bod, cod] = k.split('|');
    const f = ult.get(k);
    const d = f ? diffDays(hoy, f) : 99999;
    if (d >= dias) out.push({ bod, cod, ultimo: f ?? '', dias: d, cant: v.cant, bs: round(v.bs, 2) });
  }
  return out;
}
void cfg;
void year;
