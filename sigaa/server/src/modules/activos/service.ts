/** Activos Fijos: ingreso, codificación, ficha técnica, solicitudes, asignación, movimientos y consultas. */
import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, today, txt, diffDays, norm } from '../../core/util.js';
import { cfg, cfgNum, siguienteNro, bitacora } from '../../core/services.js';

const audit = (db: Db, u: Usuario, accion: string, doc: string, detalle: string) => bitacora(db, u, 'ACTIVOS FIJOS', accion, doc, detalle);
/** Número AF con contador propio (ING, SOL, ASG, DEV, TRF, BAJ) para no mezclar con Almacenes. */
const nroAF = (db: Db, prefijo: string) => siguienteNro(db, prefijo, undefined, 'AF.' + prefijo);

export const SIT_ALMACEN = 'EN ALMACEN';
export const SIT_ASIGNADO = 'ASIGNADO';
export const SIT_BAJA = 'BAJA';
export const TIPOS_INGRESO_AF = ['ORDEN DE COMPRA', 'CONTRATO', 'DONACIÓN', 'TRANSFERENCIA', 'INVENTARIO INICIAL'];

/** Código del activo: EEE-AA-CCXXX-NN (edificio-ambiente-cuenta+auxiliar-correlativo; 15 caracteres, límite VSIAF). */
export async function armarCodigo(db: Db, edif: number, amb: number, cta: number, aux: number, corr: number): Promise<string> {
  const s = (await cfg(db, 'SepCodigo', '-')) || '-';
  const p = (n: number, w: number) => String(n).padStart(w, '0');
  return `${p(edif, 3)}${s}${p(amb, 2)}${s}${p(cta, 2)}${p(aux, 3)}${s}${p(corr, 2)}`;
}

async function nombreAux(db: Db, cta: number, aux: number): Promise<string> {
  return txt((await db('af_auxiliares').where({ id_cta: cta, id_aux: aux }).first('auxiliar'))?.auxiliar);
}

async function movimiento(db: Db, u: Usuario, fecha: string, codigo: string, tipo: string, doc: string, origen: string, destino: string, detalle: string) {
  await db('af_movimientos').insert({ fecha, codigo, tipo, documento: doc, origen, destino, detalle, usuario: u.usuario, fecha_reg: nowIso() });
}

// ───────────── INGRESO ─────────────
export interface IngresoAFInput {
  nro?: string; fecha: string; tipo_doc: string; nro_doc?: string; preventivo?: string; proveedor?: string; factura?: string; nro_memo?: string;
  comision1?: string; comision2?: string; unidad?: string; fuente_fin?: string; observaciones?: string;
  items: { item?: number; id_cta: number; id_aux: number; descripcion?: string; unidad?: string; cantidad: number; precio_unit: number }[];
}

export async function guardarIngresoAF(db: Db, u: Usuario, d: IngresoAFInput) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha de recepción.');
  e.add(!TIPOS_INGRESO_AF.includes(txt(d.tipo_doc)), 'Seleccione el tipo de ingreso.');
  if (['ORDEN DE COMPRA', 'CONTRATO'].includes(txt(d.tipo_doc))) {
    e.add(!txt(d.nro_doc), 'Registre el Nº de Orden de Compra o Contrato.');
    e.add(!txt(d.proveedor), 'Seleccione el proveedor.');
  }
  e.throwIfAny('Ingreso incompleto:');
  const minimo = await cfgNum(db, 'ValorMinimo', 500);
  return db.transaction(async (trx) => {
    const filas: any[] = [];
    const avisos: string[] = [];
    let total = 0;
    let j = 0;
    for (const it of d.items || []) {
      j++;
      const cta = await trx('af_cuentas').where({ id_cta: it.id_cta }).first();
      if (!cta) fail(`Ítem ${j}: seleccione la cuenta contable.`);
      const aux = await nombreAux(trx, it.id_cta, it.id_aux);
      if (!aux) fail(`Ítem ${j}: el auxiliar no corresponde a la cuenta contable seleccionada.`);
      const cant = num(it.cantidad);
      if (!(cant > 0) || cant !== Math.floor(cant)) fail(`Ítem ${j}: la cantidad debe ser un número entero mayor a cero.`);
      const pu = num(it.precio_unit);
      if (pu < 0) fail(`Ítem ${j}: el precio unitario no es válido.`);
      if (pu > 0 && pu < minimo && it.id_cta !== 2) avisos.push(`Ítem ${j}: el valor unitario (Bs ${pu}) es menor al valor mínimo de activo fijo (Bs ${minimo}, RI-02); evalúe registrarlo como bien de consumo.`);
      const t = round(cant * pu, 2);
      total += t;
      filas.push({ item: j, id_cta: it.id_cta, id_aux: it.id_aux, descripcion: txt(it.descripcion) || aux, unidad: txt(it.unidad) || 'PIEZA', cantidad: cant, precio_unit: pu, total: t, cant_codif: 0 });
    }
    if (!filas.length) fail('Registre al menos un activo fijo en el detalle.');
    const prov = txt(d.proveedor);
    const pr = prov ? await trx('core_proveedores').where({ razon_social: prov }).first('nit') : null;
    const cab = {
      fecha: d.fecha, tipo_doc: d.tipo_doc, nro_doc: txt(d.nro_doc), preventivo: txt(d.preventivo), proveedor: prov, nit: txt(pr?.nit), factura: txt(d.factura), nro_memo: txt(d.nro_memo),
      comision1: txt(d.comision1), comision2: txt(d.comision2), unidad: txt(d.unidad), fuente_fin: txt(d.fuente_fin), observaciones: txt(d.observaciones), total: round(total, 2),
    };
    let nro = txt(d.nro);
    if (nro) {
      const ex = await trx('af_ingresos').where({ nro }).first();
      if (!ex) fail(`No existe el ingreso ${nro}.`);
      // Los ítems con códigos generados no pueden cambiar de cuenta/auxiliar ni reducir su cantidad.
      const prev = await trx('af_ingresos_det').where({ nro });
      for (const p of prev) {
        if (num(p.cant_codif) <= 0) continue;
        const nuevo = filas.find((f) => f.item === p.item);
        if (!nuevo) fail(`El ítem ${p.item} ya tiene códigos generados y no puede eliminarse del ingreso.`);
        if (nuevo.id_cta !== p.id_cta || nuevo.id_aux !== p.id_aux) fail(`El ítem ${p.item} ya tiene códigos generados: no puede cambiar su cuenta ni su auxiliar.`);
        if (nuevo.cantidad < num(p.cant_codif)) fail(`El ítem ${p.item} ya tiene ${p.cant_codif} códigos generados: la cantidad no puede ser menor.`);
        nuevo.cant_codif = num(p.cant_codif);
      }
      await trx('af_ingresos').where({ nro }).update(cab);
      await trx('af_ingresos_det').where({ nro }).delete();
    } else {
      nro = await nroAF(trx, 'ING');
      await trx('af_ingresos').insert({ nro, ...cab, estado: 'REGISTRADO', fecha_reg: nowIso() });
    }
    for (const f of filas) await trx('af_ingresos_det').insert({ nro, ...f });
    await actualizarEstadoIngreso(trx, nro);
    await audit(trx, u, 'REGISTRO DE INGRESO', nro, `${d.tipo_doc} ${txt(d.nro_doc)} - Bs ${total.toFixed(2)}`);
    return { nro, total: round(total, 2), advertencias: avisos };
  });
}

export async function actualizarEstadoIngreso(db: Db, nro: string) {
  const det = await db('af_ingresos_det').where({ nro });
  const tot = det.reduce((t: number, x: any) => t + num(x.cantidad), 0);
  const cod = det.reduce((t: number, x: any) => t + num(x.cant_codif), 0);
  const estado = cod === 0 ? 'REGISTRADO' : cod >= tot ? 'CODIFICADO' : 'PARCIAL';
  await db('af_ingresos').where({ nro }).update({ estado });
  return estado;
}

export async function obtenerIngresoAF(db: Db, nro: string) {
  const h = await db('af_ingresos').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el ingreso ${nro}.`);
  const items = await db('af_ingresos_det as d').leftJoin('af_cuentas as c', 'c.id_cta', 'd.id_cta').leftJoin('af_auxiliares as a', (j) => j.on('a.id_cta', 'd.id_cta').andOn('a.id_aux', 'd.id_aux')).where('d.nro', nro).select('d.*', 'c.cuenta', 'a.auxiliar').orderBy('d.item');
  return { ...h, items };
}
export async function listarIngresosAF(db: Db) {
  return db('af_ingresos').orderBy('nro', 'desc');
}

// ───────────── CODIFICACIÓN ─────────────
export interface CodificarInput {
  nro_ingreso?: string; // vacío = codificación directa (inventario inicial)
  fecha: string;
  estado?: string;
  filas: { item?: number; id_cta: number; id_aux: number; descripcion?: string; cod_edif: number; cod_amb?: number; cantidad: number; valor?: number }[];
}

/** Pendiente de codificar por ítem del ingreso. */
export async function pendientesCodificar(db: Db, nro: string) {
  const items = await obtenerIngresoAF(db, nro);
  return items.items.map((x: any) => ({ ...x, pendiente: num(x.cantidad) - num(x.cant_codif) }));
}

export async function codificarActivos(db: Db, u: Usuario, d: CodificarInput) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha de codificación.');
  e.add(!(d.filas || []).length, 'Indique la cantidad a codificar y el edificio/ambiente de destino.');
  e.throwIfAny('No se puede codificar:');
  return db.transaction(async (trx) => {
    let ing: any = null;
    let provNombre = '';
    let fechaIng = d.fecha;
    if (txt(d.nro_ingreso)) {
      ing = await trx('af_ingresos').where({ nro: d.nro_ingreso }).first();
      if (!ing) fail(`No existe el ingreso ${d.nro_ingreso}.`);
      provNombre = txt(ing.proveedor);
      fechaIng = ing.fecha;
    }
    const estadoFis = txt(d.estado) || 'Nuevo';
    if (!(await trx('af_estados').where({ estado: estadoFis }).first())) fail(`El estado físico "${estadoFis}" no existe.`);
    const usados = new Map<number, number>();
    const correl = new Map<string, number>(); // máximo correlativo asignado en esta operación por (edif, amb, cta, aux)
    const generados: { codigo: string; auxiliar: string; descripcion: string; ubicacion: string }[] = [];
    let j = 0;
    for (const f of d.filas) {
      j++;
      const q = Math.floor(num(f.cantidad));
      if (q <= 0) continue;
      if (q !== num(f.cantidad)) fail(`Fila ${j}: la cantidad a codificar debe ser entera.`);
      const aux = await nombreAux(trx, f.id_cta, f.id_aux);
      if (!f.id_cta || !f.id_aux) fail(`Fila ${j}: falta la cuenta contable o el auxiliar.`);
      if (!aux) fail(`Fila ${j}: el auxiliar no corresponde a la cuenta.`);
      const edif = await trx('af_edificios').where({ cod_edif: f.cod_edif }).first();
      if (!edif) fail(`Fila ${j}: seleccione el EDIFICIO destino.`);
      const am = f.cod_amb ?? 0;
      const amb = await trx('af_ambientes').where({ cod_edif: f.cod_edif, cod_amb: am }).first();
      if (!amb) fail(`Fila ${j}: el ambiente seleccionado no pertenece al edificio ${String(f.cod_edif).padStart(3, '0')}.`);
      let valor = num(f.valor);
      if (ing) {
        const item = f.item ?? 0;
        const det = await trx('af_ingresos_det').where({ nro: ing.nro, item }).first();
        if (!det) fail(`Fila ${j}: el ítem ${item} no existe en el ingreso.`);
        if (det.id_cta !== f.id_cta || det.id_aux !== f.id_aux) fail(`Fila ${j}: la cuenta/auxiliar no coincide con el ítem ${item} del ingreso.`);
        usados.set(item, (usados.get(item) ?? 0) + q);
        const pend = num(det.cantidad) - num(det.cant_codif);
        if ((usados.get(item) ?? 0) > pend) fail(`Fila ${j}: la cantidad a codificar supera la cantidad pendiente del ítem ${item} (${pend}).`);
        if (!valor) valor = num(det.precio_unit);
      }
      const clave = `${f.cod_edif}|${am}|${f.id_cta}|${f.id_aux}`;
      if (!correl.has(clave)) {
        const r = await trx('af_activos').where({ cod_edif: f.cod_edif, cod_amb: am, id_cta: f.id_cta, id_aux: f.id_aux }).max({ m: 'correl' }).first();
        correl.set(clave, num(r?.m));
      }
      const corr0 = correl.get(clave)!;
      if (corr0 + q > 99) fail(`Fila ${j}: se superaría el correlativo 99 para ${aux} en ese ambiente. Distribuya en otro ambiente.`);
      correl.set(clave, corr0 + q);
      const desc = txt(f.descripcion) || (ing ? txt((await trx('af_ingresos_det').where({ nro: ing.nro, item: f.item ?? 0 }).first('descripcion'))?.descripcion) : '') || aux;
      for (let t = 1; t <= q; t++) {
        const codigo = await armarCodigo(trx, f.cod_edif, am, f.id_cta, f.id_aux, corr0 + t);
        await trx('af_activos').insert({
          codigo, nro_ingreso: ing?.nro ?? null, item: ing ? f.item ?? null : null, cod_edif: f.cod_edif, cod_amb: am, id_cta: f.id_cta, id_aux: f.id_aux, auxiliar: aux, correl: corr0 + t, descripcion: desc,
          estado: estadoFis, valor, fecha_ingreso: fechaIng, fecha_codif: d.fecha, situacion: SIT_ALMACEN, edif_actual: f.cod_edif, amb_actual: am, etq_impresa: 'NO',
        });
        const ubic = `${edif.edificio} / ${amb.ambiente}`;
        await movimiento(trx, u, d.fecha, codigo, ing ? 'INGRESO Y CODIFICACIÓN' : 'CODIFICACIÓN DIRECTA', ing ? ing.nro : 'INV. INICIAL', provNombre, ing ? 'ALMACÉN' : ubic, `Codificado para ${ubic}`);
        generados.push({ codigo, auxiliar: aux, descripcion: desc, ubicacion: ubic });
      }
    }
    if (!generados.length) fail('Indique en la columna CANT. A CODIFICAR cuántos activos desea codificar y en qué edificio/ambiente.');
    if (ing) {
      for (const [item, q] of usados) await trx('af_ingresos_det').where({ nro: ing.nro, item }).increment('cant_codif', q);
      await actualizarEstadoIngreso(trx, ing.nro);
    }
    await audit(trx, u, 'CODIFICACIÓN DE ACTIVOS', ing?.nro ?? 'DIRECTA', `${generados.length} códigos: ${generados[0].codigo} … ${generados[generados.length - 1].codigo}`);
    return { generados, cantidad: generados.length };
  });
}

// ───────────── FICHA TÉCNICA ─────────────
export async function obtenerActivo(db: Db, codigo: string) {
  const a = await db('af_activos as a')
    .leftJoin('af_cuentas as c', 'c.id_cta', 'a.id_cta')
    .leftJoin('af_edificios as e', 'e.cod_edif', 'a.cod_edif')
    .leftJoin('af_ambientes as m', (j) => j.on('m.cod_edif', 'a.cod_edif').andOn('m.cod_amb', 'a.cod_amb'))
    .where('a.codigo', codigo)
    .select('a.*', 'c.cuenta', 'c.partida', 'c.vida_util', 'e.edificio', 'm.ambiente')
    .first();
  if (!a) throw new NotFound(`No existe el activo ${codigo}.`);
  const campos = await db('af_campos').where({ id_cta: a.id_cta }).orderBy('nro');
  const ubic = a.edif_actual ? await db('af_edificios as e').leftJoin('af_ambientes as m', (j) => j.on('m.cod_edif', 'e.cod_edif').andOn('m.cod_amb', db.raw('?', [a.amb_actual ?? 0]))).where('e.cod_edif', a.edif_actual).first('e.edificio', 'm.ambiente') : null;
  return { ...a, ubicacion_actual: ubic ? `${ubic.edificio} / ${txt(ubic.ambiente)}` : '', campos: campos.map((c: any) => ({ nro: c.nro, campo: c.campo, descripcion: c.descripcion, valor: a['c' + String(c.nro).padStart(2, '0')] ?? '' })) };
}

export async function buscarActivos(db: Db, q: { texto?: string; situacion?: string; funcionario?: string; cod_edif?: number; cod_amb?: number; id_cta?: number; id_aux?: number; limite?: number }) {
  const w = db('af_activos as a').leftJoin('af_edificios as e', 'e.cod_edif', 'a.cod_edif').select('a.*', 'e.edificio').orderBy('a.codigo').limit(q.limite ?? 500);
  if (q.texto) {
    const like = `%${norm(q.texto)}%`;
    w.where((b) => b.where('a.codigo', 'like', `%${q.texto}%`).orWhereRaw('upper(a.descripcion) like ?', [like]).orWhereRaw('upper(a.auxiliar) like ?', [like]));
  }
  if (q.situacion && q.situacion !== 'TODAS') w.where('a.situacion', q.situacion);
  if (q.funcionario) w.where('a.funcionario', q.funcionario);
  if (q.cod_edif) w.where('a.edif_actual', q.cod_edif);
  if (q.cod_amb !== undefined && q.cod_amb !== null && (q.cod_amb as any) !== '') w.where('a.amb_actual', q.cod_amb);
  if (q.id_cta) w.where('a.id_cta', q.id_cta);
  if (q.id_aux) w.where('a.id_aux', q.id_aux);
  return w;
}

export async function guardarFicha(db: Db, u: Usuario, codigo: string, d: { descripcion: string; marca?: string; modelo?: string; serie?: string; color?: string; estado: string; valor?: number; observaciones?: string; campos?: Record<string, string> }) {
  const a = await db('af_activos').where({ codigo }).first();
  if (!a) throw new NotFound(`No existe el activo ${codigo}.`);
  if (!txt(d.descripcion)) fail('Registre la descripción del activo.');
  if (!(await db('af_estados').where({ estado: d.estado }).first())) fail(`El estado físico "${d.estado}" no existe.`);
  if (d.valor !== undefined && d.valor !== null && (isNaN(Number(d.valor)) || Number(d.valor) < 0)) fail('El valor debe ser numérico.');
  const upd: Record<string, unknown> = { descripcion: txt(d.descripcion), marca: txt(d.marca), modelo: txt(d.modelo), serie: txt(d.serie), color: txt(d.color), estado: d.estado, observaciones: txt(d.observaciones) };
  if (d.valor !== undefined && d.valor !== null) upd.valor = num(d.valor);
  const campos = await db('af_campos').where({ id_cta: a.id_cta });
  for (const c of campos) upd['c' + String(c.nro).padStart(2, '0')] = txt(d.campos?.[String(c.nro)]);
  await db('af_activos').where({ codigo }).update(upd);
  if (d.estado !== a.estado) await movimiento(db, u, today(), codigo, 'CAMBIO DE ESTADO', '', a.estado, d.estado, 'Actualización de ficha técnica');
  await audit(db, u, 'FICHA TÉCNICA', codigo, txt(d.descripcion));
  return { codigo };
}

export async function guardarFoto(db: Db, u: Usuario, codigo: string, n: number, archivo: string | null) {
  if (n < 1 || n > 4) fail('Las fotografías van del 1 al 4.');
  const a = await db('af_activos').where({ codigo }).first();
  if (!a) throw new NotFound(`No existe el activo ${codigo}.`);
  await db('af_activos').where({ codigo }).update({ ['foto' + n]: archivo });
  await audit(db, u, archivo ? 'FOTOGRAFÍA' : 'QUITAR FOTOGRAFÍA', codigo, `Foto ${n}`);
}

export async function marcarEtiquetas(db: Db, u: Usuario, codigos: string[]) {
  if (!codigos.length) fail('Marque los códigos que desea imprimir.');
  await db('af_activos').whereIn('codigo', codigos).update({ etq_impresa: 'SI' });
  await audit(db, u, 'ETIQUETAS IMPRESAS', '', `${codigos.length} códigos`);
}

// ───────────── SOLICITUDES ─────────────
export async function saldoAlmacen(db: Db, cta: number, aux: number): Promise<number> {
  const r = await db('af_activos').where({ id_cta: cta, id_aux: aux, situacion: SIT_ALMACEN }).count({ n: '*' }).first();
  return Number(r?.n);
}

export async function guardarSolicitud(db: Db, u: Usuario, d: { nro?: string; fecha: string; unidad: string; funcionario: string; cargo?: string; justificacion?: string; aprobado_daf?: string; items: { id_cta: number; id_aux: number; cantidad: number; descripcion?: string }[] }) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha de la solicitud.');
  e.add(!txt(d.unidad), 'Seleccione la unidad solicitante.');
  e.add(!txt(d.funcionario), 'Seleccione el funcionario solicitante.');
  e.throwIfAny('Solicitud incompleta:');
  return db.transaction(async (trx) => {
    const filas: any[] = [];
    let j = 0;
    for (const it of d.items || []) {
      j++;
      const aux = await nombreAux(trx, it.id_cta, it.id_aux);
      if (!it.id_cta || !it.id_aux) fail(`Ítem ${j}: seleccione la cuenta y el auxiliar.`);
      if (!aux) fail(`Ítem ${j}: el auxiliar no corresponde a la cuenta.`);
      if (!(num(it.cantidad) > 0)) fail(`Ítem ${j}: registre la cantidad solicitada.`);
      filas.push({ item: j, id_cta: it.id_cta, id_aux: it.id_aux, descripcion: txt(it.descripcion) || aux, cantidad: Math.floor(num(it.cantidad)), saldo: await saldoAlmacen(trx, it.id_cta, it.id_aux) });
    }
    if (!filas.length) fail('Registre al menos un activo solicitado.');
    const cab = { fecha: d.fecha, unidad: d.unidad, funcionario: d.funcionario, cargo: txt(d.cargo), justificacion: txt(d.justificacion), aprobado_daf: txt(d.aprobado_daf) === 'SI' ? 'SI' : 'NO' };
    let nro = txt(d.nro);
    if (nro && (await trx('af_solicitudes').where({ nro }).first())) {
      await trx('af_solicitudes').where({ nro }).update(cab);
      await trx('af_solicitudes_det').where({ nro }).delete();
    } else {
      nro = nro || (await nroAF(trx, 'SOL'));
      await trx('af_solicitudes').insert({ nro, ...cab, estado: 'PENDIENTE', fecha_reg: nowIso() });
    }
    for (const f of filas) await trx('af_solicitudes_det').insert({ nro, ...f });
    await audit(trx, u, 'SOLICITUD DE ACTIVOS', nro, `${d.funcionario} - ${filas.length} ítems`);
    return { nro, items: filas };
  });
}
export async function solicitudSinExistencia(db: Db, u: Usuario, nro: string) {
  const s = await db('af_solicitudes').where({ nro }).first();
  if (!s) throw new NotFound(`No existe la solicitud ${nro}.`);
  await db('af_solicitudes').where({ nro }).update({ estado: 'SIN EXISTENCIA' });
  await audit(db, u, 'SOLICITUD SIN EXISTENCIA', nro, '');
  return { nro, estado: 'SIN EXISTENCIA' };
}
export async function obtenerSolicitud(db: Db, nro: string) {
  const h = await db('af_solicitudes').where({ nro }).first();
  if (!h) throw new NotFound(`No existe la solicitud ${nro}.`);
  const items = await db('af_solicitudes_det as d').leftJoin('af_cuentas as c', 'c.id_cta', 'd.id_cta').where('d.nro', nro).select('d.*', 'c.cuenta').orderBy('d.item');
  for (const it of items) (it as any).saldo = await saldoAlmacen(db, it.id_cta, it.id_aux);
  return { ...h, items };
}
export async function listarSolicitudes(db: Db) {
  return db('af_solicitudes').orderBy('nro', 'desc');
}

// ───────────── ASIGNACIÓN (Formulario de Salida) ─────────────
/** Activos en almacén, preseleccionando los de la solicitud según cantidades pendientes. */
export async function disponiblesParaAsignar(db: Db, f: { nro_sol?: string; id_cta?: number; id_aux?: number }) {
  const q = db('af_activos').where({ situacion: SIT_ALMACEN }).orderBy('codigo');
  if (f.id_cta) q.where({ id_cta: f.id_cta });
  if (f.id_aux) q.where({ id_aux: f.id_aux });
  let rows = await q;
  const pre = new Set<string>();
  if (f.nro_sol) {
    const sol = await db('af_solicitudes').where({ nro: f.nro_sol }).first();
    if (!sol) fail(`No existe la solicitud ${f.nro_sol}.`);
    const det = await db('af_solicitudes_det').where({ nro: f.nro_sol });
    const dadas = await db('af_asignaciones as a').join('af_asignaciones_det as d', 'd.nro', 'a.nro').join('af_activos as x', 'x.codigo', 'd.codigo').where('a.nro_sol', f.nro_sol).select('x.id_cta', 'x.id_aux');
    for (const x of det) {
      let falta = num(x.cantidad) - dadas.filter((y: any) => y.id_cta === x.id_cta && y.id_aux === x.id_aux).length;
      for (const a of rows.filter((r: any) => r.id_cta === x.id_cta && r.id_aux === x.id_aux)) {
        if (falta <= 0) break;
        pre.add(a.codigo);
        falta--;
      }
    }
    if (!f.id_cta && !f.id_aux) rows = rows.filter((r: any) => det.some((x: any) => x.id_cta === r.id_cta && x.id_aux === r.id_aux));
  }
  return rows.map((r: any) => ({ ...r, preseleccionado: pre.has(r.codigo) }));
}

export async function generarAsignacion(db: Db, u: Usuario, d: { fecha: string; nro_sol?: string; funcionario: string; cod_edif?: number | null; cod_amb?: number | null; codigos: string[]; observaciones?: string }) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha.');
  e.add(!txt(d.funcionario), 'Seleccione el servidor público al que se asignarán los activos.');
  e.add(!(d.codigos || []).length, 'Marque los activos a asignar.');
  e.throwIfAny('No se puede asignar:');
  return db.transaction(async (trx) => {
    const fn = await trx('core_funcionarios').where({ nombre: d.funcionario }).first();
    if (!fn) fail('El funcionario no está registrado en el catálogo de funcionarios.');
    let destino = '';
    if (d.cod_edif) {
      const am = d.cod_amb ?? 0;
      const amb = await trx('af_ambientes as m').join('af_edificios as e', 'e.cod_edif', 'm.cod_edif').where({ 'm.cod_edif': d.cod_edif, 'm.cod_amb': am }).first('e.edificio', 'm.ambiente');
      if (!amb) fail('El ambiente destino no pertenece al edificio seleccionado.');
      destino = `${amb.edificio} / ${amb.ambiente}`;
    }
    if (txt(d.nro_sol) && !(await trx('af_solicitudes').where({ nro: d.nro_sol }).first())) fail(`No existe la solicitud ${d.nro_sol}.`);
    const cods = [...new Set(d.codigos)];
    let valor = 0;
    const rows: any[] = [];
    for (const c of cods) {
      const a = await trx('af_activos').where({ codigo: c }).first();
      if (!a) fail(`No existe el activo ${c}.`);
      if (a.situacion !== SIT_ALMACEN) fail(`El activo ${c} ya no se encuentra en almacén.`);
      valor += num(a.valor);
      rows.push(a);
    }
    const nro = await nroAF(trx, 'ASG');
    await trx('af_asignaciones').insert({
      nro, fecha: d.fecha, nro_sol: txt(d.nro_sol) || null, funcionario: fn.nombre, ci: fn.ci, cargo: fn.cargo, unidad: fn.unidad, cod_edif: d.cod_edif ?? null, cod_amb: d.cod_edif ? d.cod_amb ?? 0 : null,
      cantidad: cods.length, valor: round(valor, 2), observaciones: txt(d.observaciones), fecha_reg: nowIso(),
    });
    for (const a of rows) {
      await trx('af_asignaciones_det').insert({ nro, codigo: a.codigo });
      const upd: Record<string, unknown> = { situacion: SIT_ASIGNADO, funcionario: fn.nombre, ci_func: fn.ci, nro_acta: nro, fecha_asig: d.fecha };
      if (d.cod_edif) Object.assign(upd, { edif_actual: d.cod_edif, amb_actual: d.cod_amb ?? 0 });
      await trx('af_activos').where({ codigo: a.codigo }).update(upd);
      await movimiento(trx, u, d.fecha, a.codigo, 'ASIGNACIÓN', nro, 'ALMACÉN', fn.nombre, `${destino ? 'Ubicación: ' + destino : ''}${d.nro_sol ? ' Solicitud ' + d.nro_sol : ''}`.trim());
    }
    if (txt(d.nro_sol)) await actualizarEstadoSolicitud(trx, d.nro_sol!);
    await audit(trx, u, 'ASIGNACIÓN DE ACTIVOS', nro, `${fn.nombre} - ${cods.length} activos - Bs ${valor.toFixed(2)}`);
    return { nro, cantidad: cods.length, valor: round(valor, 2) };
  });
}

async function actualizarEstadoSolicitud(db: Db, sol: string) {
  const det = await db('af_solicitudes_det').where({ nro: sol });
  const dadas = await db('af_asignaciones as a').join('af_asignaciones_det as d', 'd.nro', 'a.nro').join('af_activos as x', 'x.codigo', 'd.codigo').where('a.nro_sol', sol).select('x.id_cta', 'x.id_aux');
  const completo = det.every((x: any) => dadas.filter((y: any) => y.id_cta === x.id_cta && y.id_aux === x.id_aux).length >= num(x.cantidad));
  const actas = (await db('af_asignaciones').where({ nro_sol: sol }).select('nro')).map((r: any) => r.nro).join(', ');
  await db('af_solicitudes').where({ nro: sol }).update({ estado: completo ? 'ATENDIDA' : 'ATENDIDA PARCIAL', nro_acta: actas });
}

export async function obtenerAsignacion(db: Db, nro: string) {
  const h = await db('af_asignaciones').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el acta ${nro}.`);
  const activos = await db('af_asignaciones_det as d').join('af_activos as a', 'a.codigo', 'd.codigo').where('d.nro', nro).select('a.*').orderBy('a.codigo');
  return { ...h, activos };
}
export async function listarAsignaciones(db: Db) {
  return db('af_asignaciones').orderBy('nro', 'desc');
}

// ───────────── DEVOLUCIÓN · TRANSFERENCIA · BAJA ─────────────
export async function procesarMovimientoAF(
  db: Db, u: Usuario,
  d: { tipo: 'DEVOLUCIÓN' | 'TRANSFERENCIA' | 'BAJA'; fecha: string; origen?: string; destino?: string; cod_edif?: number | null; cod_amb?: number | null; estado?: string; motivo?: string; codigos: string[] },
) {
  const e = new Errores();
  e.add(!['DEVOLUCIÓN', 'TRANSFERENCIA', 'BAJA'].includes(d.tipo), 'Seleccione el tipo de movimiento: DEVOLUCIÓN, TRANSFERENCIA o BAJA.');
  e.add(!isDate(d.fecha), 'Registre la fecha.');
  e.add(!(d.codigos || []).length, 'Marque los activos a procesar.');
  if (d.tipo === 'DEVOLUCIÓN') e.add(!txt(d.origen), 'Seleccione el funcionario que devuelve los activos.');
  if (d.tipo === 'TRANSFERENCIA') {
    e.add(!txt(d.origen) || !txt(d.destino), 'Seleccione el funcionario ORIGEN y el funcionario DESTINO.');
    e.add(norm(d.origen) === norm(d.destino) && !!txt(d.origen), 'El funcionario origen y destino no pueden ser el mismo.');
  }
  if (d.tipo === 'BAJA') e.add(!txt(d.motivo), 'Registre el motivo de la baja (obsolescencia, siniestro, robo, deterioro, etc.).');
  e.throwIfAny('No se puede procesar el movimiento:');
  return db.transaction(async (trx) => {
    const prefijo = d.tipo === 'DEVOLUCIÓN' ? 'DEV' : d.tipo === 'TRANSFERENCIA' ? 'TRF' : 'BAJ';
    let destFn: any = null;
    if (d.tipo === 'TRANSFERENCIA') {
      destFn = await trx('core_funcionarios').where({ nombre: d.destino }).first();
      if (!destFn) fail('El funcionario destino no está registrado.');
    }
    let ubic = '';
    if (d.cod_edif) {
      const amb = await trx('af_ambientes as m').join('af_edificios as e', 'e.cod_edif', 'm.cod_edif').where({ 'm.cod_edif': d.cod_edif, 'm.cod_amb': d.cod_amb ?? 0 }).first('e.edificio', 'm.ambiente');
      if (!amb) fail('El ambiente no pertenece al edificio seleccionado.');
      ubic = `${amb.edificio} / ${amb.ambiente}`;
    }
    if (d.estado && !(await trx('af_estados').where({ estado: d.estado }).first())) fail(`El estado físico "${d.estado}" no existe.`);
    const nro = await nroAF(trx, prefijo);
    for (const c of [...new Set(d.codigos)]) {
      const a = await trx('af_activos').where({ codigo: c }).first();
      if (!a) fail(`No existe el activo ${c}.`);
      if (a.situacion === SIT_BAJA) fail(`El activo ${c} ya fue dado de baja.`);
      if (d.tipo === 'DEVOLUCIÓN' || d.tipo === 'TRANSFERENCIA') {
        if (a.situacion !== SIT_ASIGNADO) fail(`El activo ${c} no está asignado.`);
        if (norm(a.funcionario) !== norm(d.origen)) fail(`El activo ${c} está asignado a ${a.funcionario}, no a ${d.origen}.`);
      }
      const origen = a.situacion === SIT_ASIGNADO ? txt(a.funcionario) : 'ALMACÉN';
      const upd: Record<string, unknown> = {};
      let destinoTxt = '';
      if (d.tipo === 'DEVOLUCIÓN') {
        Object.assign(upd, { situacion: SIT_ALMACEN, funcionario: null, ci_func: null, nro_acta: nro, fecha_asig: null });
        destinoTxt = 'ALMACÉN';
      } else if (d.tipo === 'TRANSFERENCIA') {
        Object.assign(upd, { funcionario: destFn.nombre, ci_func: destFn.ci, nro_acta: nro, fecha_asig: d.fecha });
        destinoTxt = destFn.nombre;
      } else {
        Object.assign(upd, { situacion: SIT_BAJA, funcionario: null, ci_func: null });
        destinoTxt = 'BAJA';
      }
      if (d.cod_edif && d.tipo !== 'BAJA') Object.assign(upd, { edif_actual: d.cod_edif, amb_actual: d.cod_amb ?? 0 });
      if (d.estado) upd.estado = d.estado;
      await trx('af_activos').where({ codigo: c }).update(upd);
      await movimiento(trx, u, d.fecha, c, d.tipo, nro, origen, destinoTxt, `${txt(d.motivo)}${d.estado ? ' | Estado: ' + d.estado : ''}${ubic ? ' | Ubicación: ' + ubic : ''}`.trim());
    }
    await audit(trx, u, d.tipo, nro, `${new Set(d.codigos).size} activos${d.motivo ? ': ' + d.motivo : ''}`);
    return { nro, cantidad: new Set(d.codigos).size };
  });
}

/** Activos asignados a un funcionario (para cargar la grilla de devolución/transferencia). */
export async function activosDeFuncionario(db: Db, funcionario: string) {
  return db('af_activos').where({ situacion: SIT_ASIGNADO, funcionario }).orderBy('codigo');
}

export async function kardexActivo(db: Db, codigo: string) {
  return db('af_movimientos').where({ codigo }).orderBy(['fecha', 'id']);
}

// ───────────── Consultas / alertas ─────────────
export async function indicadoresAF(db: Db) {
  const all = await db('af_activos').select('situacion', 'valor', 'foto1', 'etq_impresa');
  const sol = Number((await db('af_solicitudes').whereIn('estado', ['PENDIENTE', 'ATENDIDA PARCIAL']).count({ n: '*' }).first())?.n);
  const vivos = all.filter((a: any) => a.situacion !== SIT_BAJA);
  return {
    total: all.length,
    en_almacen: all.filter((a: any) => a.situacion === SIT_ALMACEN).length,
    asignados: all.filter((a: any) => a.situacion === SIT_ASIGNADO).length,
    bajas: all.filter((a: any) => a.situacion === SIT_BAJA).length,
    valor_total: round(vivos.reduce((t: number, a: any) => t + num(a.valor), 0), 2),
    stickers_pendientes: all.filter((a: any) => a.etq_impresa !== 'SI' && a.situacion !== SIT_BAJA).length,
    sin_fotografia: vivos.filter((a: any) => !a.foto1).length,
    solicitudes_pendientes: sol,
  };
}

/** Depreciación lineal estimada (valor × factor de conservación no se usa: método de línea recta por vida útil). */
export function depreciacion(valor: number, vidaUtilAnios: number, fechaIngreso: string, hasta: string = today()) {
  if (!vidaUtilAnios || !isDate(fechaIngreso)) return { acumulada: 0, neto: valor };
  const anios = Math.max(0, diffDays(hasta, fechaIngreso) / 365.25);
  const acum = Math.min(valor, (valor / vidaUtilAnios) * anios);
  return { acumulada: round(acum, 2), neto: round(valor - acum, 2) };
}
void cfg;
