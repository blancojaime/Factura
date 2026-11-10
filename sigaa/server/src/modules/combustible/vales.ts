/** Recepción de vales, emisión, descargo (Anexo 3), movimientos (devolución/anulación/vencimiento/extravío). */
import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { addDays, isDate, nowIso, num, round, today, txt, fmt2, fmtDate } from '../../core/util.js';
import { cfg, cfgNum, siguienteNro } from '../../core/services.js';
import {
  ALM_VALES, audit, descargosPendientes, type MovK, itemTurril, itemVale, kardexAdd, litrosMaximos, precioVigente, recalcularContratos, rendimientoVehiculo, saldoTurril, ultimaLectura, cortesValidos,
} from './base.js';

/** "1001-1010, 1015" a partir de una lista de números. */
export function rangosTexto(nums: number[]): string {
  const a = [...nums].sort((x, y) => x - y);
  const out: string[] = [];
  let i = 0;
  while (i < a.length) {
    let j = i;
    while (j + 1 < a.length && a[j + 1] === a[j] + 1) j++;
    out.push(j > i ? `${a[i]}-${a[j]}` : `${a[i]}`);
    i = j + 1;
  }
  return out.join(', ');
}

// ───────────── RECEPCIÓN (ingreso de lotes de vales al almacén) ─────────────
export interface RecepcionInput {
  fecha: string;
  nro_contrato: string;
  factura?: string;
  fecha_factura?: string;
  nota_ref?: string;
  comprobante?: string;
  observaciones?: string;
  filas: { corte: number; desde: number; hasta: number }[];
}

export async function registrarRecepcion(db: Db, u: Usuario, d: RecepcionInput) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Fecha de recepción vacía o no válida.');
  e.add(!txt(d.nro_contrato), 'Seleccione el número de contrato.');
  e.throwIfAny('No se puede registrar la recepción:');
  const cortes = await cortesValidos(db);
  return db.transaction(async (trx) => {
    const ct = await trx('com_contratos').where({ nro: d.nro_contrato }).first();
    if (!ct) fail(`El contrato ${d.nro_contrato} no está registrado.`);
    const er = new Errores();
    if (!txt(ct.proveedor)) er.add(true, 'El contrato no tiene proveedor.');
    er.add(!txt(ct.combustible), 'El contrato no tiene combustible definido.');
    er.add(!txt(ct.modalidad), 'El contrato no tiene modalidad (Prepago/Postpago).');
    er.add(ct.estado !== 'Vigente', 'El contrato no está Vigente.');
    er.add(!!ct.vigencia_desde && d.fecha < ct.vigencia_desde, 'La fecha es anterior al inicio de vigencia del contrato.');
    er.add(!!ct.vigencia_hasta && d.fecha > ct.vigencia_hasta, 'La fecha es posterior al fin de vigencia del contrato.');
    er.add(ct.modalidad === 'Prepago' && !txt(d.factura), 'En contratos PREPAGO la factura es obligatoria.');
    er.add(!!txt(d.fecha_factura) && !isDate(d.fecha_factura), 'Fecha de factura no válida.');
    const filas = (d.filas || []).filter((f) => f && (f.corte || f.desde || f.hasta));
    er.add(!filas.length, 'Registre al menos una fila de vales (corte, Nº desde, Nº hasta).');
    let total = 0;
    let cantTot = 0;
    const vistos = new Set<string>();
    filas.forEach((f, i) => {
      const n = i + 1;
      if (!cortes.includes(Number(f.corte))) return er.add(true, `Fila ${n}: seleccione el corte del vale (${cortes.join(', ')}).`);
      const ok = Number.isInteger(f.desde) && Number.isInteger(f.hasta) && f.desde > 0 && f.hasta > 0;
      if (!ok) return er.add(true, `Fila ${n}: los números 'desde' y 'hasta' deben ser enteros positivos.`);
      if (f.hasta < f.desde) return er.add(true, `Fila ${n}: el número 'hasta' es menor que 'desde'.`);
      if (f.hasta - f.desde + 1 > 20000) return er.add(true, `Fila ${n}: más de 20.000 vales en una fila.`);
      const k = `${f.corte}`;
      for (const prev of filas.slice(0, i)) if (String(prev.corte) === k && !(f.hasta < prev.desde || f.desde > prev.hasta)) er.add(true, `Fila ${n}: la numeración se superpone con otra fila del mismo corte.`);
      vistos.add(k);
      const cant = f.hasta - f.desde + 1;
      cantTot += cant;
      total += cant * f.corte;
    });
    er.throwIfAny('No se puede registrar la recepción:');
    // duplicados de numeración para el proveedor/combustible/corte
    for (const f of filas) {
      const dup = await trx('com_vales').where({ proveedor: ct.proveedor, combustible: ct.combustible, corte: f.corte }).whereBetween('nro_vale', [f.desde, f.hasta]).first('nro_vale');
      if (dup) fail(`El vale Nº ${dup.nro_vale} de Bs ${f.corte} (${ct.combustible}) de este proveedor ya está registrado (numeración duplicada).`);
    }
    if (total > num(ct.saldo) + 1e-6) fail(`El monto recibido (Bs ${fmt2(total)}) supera el saldo del contrato (Bs ${fmt2(ct.saldo)}).`);
    const ni = await siguienteNro(trx, 'IV');
    let seq = Number(String((await trx('com_lotes').max({ m: 'id_lote' }).first())?.m ?? 'L0').slice(1));
    for (const f of filas) {
      const idLote = 'L' + String(++seq).padStart(6, '0');
      const cant = f.hasta - f.desde + 1;
      await trx('com_lotes').insert({
        id_lote: idLote, nro_ingreso: ni, fecha: d.fecha, nro_contrato: ct.nro, proveedor: ct.proveedor, modalidad: ct.modalidad, combustible: ct.combustible, corte: f.corte, desde: f.desde, hasta: f.hasta, cantidad: cant,
        monto: cant * f.corte, factura: txt(d.factura), fecha_factura: txt(d.fecha_factura).slice(0, 10) || null, nota_ref: txt(d.nota_ref), comprobante: txt(d.comprobante), observaciones: txt(d.observaciones), usuario: u.usuario, registrado: nowIso(),
      });
      const rows: any[] = [];
      for (let nro = f.desde; nro <= f.hasta; nro++)
        rows.push({ nro_vale: nro, id_lote: idLote, proveedor: ct.proveedor, combustible: ct.combustible, corte: f.corte, estado: 'Disponible', fecha_estado: d.fecha });
      await trx.batchInsert('com_vales', rows, 60);
      await kardexAdd(trx, u, [{ fecha: d.fecha, tipo: 'INGRESO', doc: ni, almacen: ALM_VALES, item: itemVale(ct.combustible, f.corte), ent: cant, cu: f.corte, detalle: `Lote ${idLote} - Nº ${f.desde} al ${f.hasta} - ${ct.proveedor}${txt(d.factura) ? ' Fact. ' + d.factura : ''}` }]);
    }
    await recalcularContratos(trx);
    await audit(trx, u, 'RECEPCIÓN DE LOTE (INGRESO)', ni, `${cantTot} vales - Bs ${total.toFixed(2)} - ${ct.proveedor}`);
    return { nro_ingreso: ni, cantidad: cantTot, monto: total };
  });
}

// ───────────── EMISIÓN ─────────────
export interface EmisionInput {
  fecha: string;
  destino: 'VEHICULO' | 'TURRIL';
  placa: string; // placa o código del puesto
  lectura?: number | null;
  conductor: string;
  solicitante: string;
  cargo_solicitante?: string;
  unidad: string;
  apertura: string;
  trabajo: string;
  desde: string;
  hasta: string;
  programado?: number;
  justificacion?: string;
  observaciones?: string;
  cantidades: Record<string, number>; // corte → cantidad de vales
  confirmar?: boolean; // aceptar las advertencias
}

export interface Resultado<T> {
  ok: boolean;
  requiereConfirmacion?: boolean;
  advertencias?: string[];
  resumen?: Record<string, unknown>;
  data?: T;
}

export async function emitirVales(db: Db, u: Usuario, d: EmisionInput): Promise<Resultado<{ nro: string; detalle: string; monto: number; litros: number; planilla: boolean }>> {
  const er = new Errores();
  const destino = txt(d.destino).toUpperCase();
  const placa = txt(d.placa);
  er.add(!isDate(d.fecha), 'Fecha de emisión vacía o no válida.');
  er.add(destino !== 'VEHICULO' && destino !== 'TURRIL', 'Seleccione el tipo de destino (VEHICULO o TURRIL).');
  er.add(!placa, 'Seleccione la placa del vehículo o el código del puesto.');
  er.add(!txt(d.conductor), 'Seleccione el conductor u operador que recibe los vales.');
  er.add(!txt(d.solicitante), 'Indique el nombre del solicitante.');
  er.add(!txt(d.unidad), 'Seleccione la unidad o área solicitante.');
  er.add(!txt(d.apertura), 'Seleccione la apertura programática.');
  er.add(!txt(d.trabajo), 'Describa el trabajo a realizar.');
  if (!isDate(d.desde) || !isDate(d.hasta)) er.add(true, 'Indique el periodo de utilización (desde / hasta).');
  else er.add(d.hasta < d.desde, "La fecha 'hasta' es anterior a 'desde'.");
  er.add(d.lectura !== null && d.lectura !== undefined && (d.lectura as any) !== '' && isNaN(Number(d.lectura)), 'El kilometraje/horómetro actual debe ser numérico.');
  const avisos: string[] = [];
  let comb = '';
  let uso = '';
  let descDest = '';
  let licencia = '';
  let descAp = '';
  let veh: any = null;
  let puesto: any = null;
  if (placa) {
    if (destino === 'VEHICULO') {
      veh = await db('com_vehiculos').where({ placa }).first();
      if (!veh) er.add(true, `La placa ${placa} no está registrada en VEHICULOS.`);
      else {
        er.add(veh.estado !== 'Activo', `El vehículo ${placa} no está Activo.`);
        comb = txt(veh.combustible);
        uso = txt(veh.uso);
        descDest = `${txt(veh.tipo)} ${txt(veh.marca)} ${txt(veh.modelo)}`.trim();
        er.add(!comb, 'El vehículo no tiene combustible definido en el catálogo.');
        er.add(!uso, 'El vehículo no tiene definido el uso (Ejecutivo/Operativo).');
        er.add(uso === 'Operativo' && !(num(d.programado) > 0), 'Vehículo de uso OPERATIVO: indique los km u horas programados.');
      }
    } else if (destino === 'TURRIL') {
      puesto = await db('com_puestos').where({ codigo: placa }).first();
      if (!puesto) er.add(true, `El puesto ${placa} no está registrado en PUESTOS.`);
      else {
        er.add(puesto.estado !== 'Activo', `El puesto ${placa} no está Activo.`);
        comb = txt(puesto.combustible);
        uso = 'Turril';
        descDest = `PUESTO ${puesto.nombre} - ${txt(puesto.ubicacion)}`;
        er.add(!comb, 'El puesto no tiene combustible definido.');
      }
    }
  }
  if (txt(d.conductor)) {
    const c = await db('com_conductores').where({ nombre: d.conductor }).first();
    if (!c) er.add(true, `El conductor ${d.conductor} no está registrado.`);
    else {
      er.add(c.estado !== 'Activo', 'El conductor no está Activo.');
      licencia = txt(c.licencia);
      er.add(destino === 'VEHICULO' && !licencia, 'El conductor no tiene número de licencia registrado.');
      er.add(!!c.vence_licencia && isDate(d.fecha) && c.vence_licencia < d.fecha, 'La licencia del conductor está VENCIDA.');
      if (isDate(d.fecha)) {
        const mx = await cfgNum(db, 'MAX_DESCARGOS_PENDIENTES', 2);
        const pend = await descargosPendientes(db, d.conductor, d.fecha);
        er.add(mx > 0 && pend >= mx, `El conductor tiene ${pend} descargos VENCIDOS sin presentar (máximo ${mx}). Debe presentar la bitácora (Anexo 3) antes de recibir nuevos vales.`);
      }
    }
  }
  if (txt(d.apertura)) {
    const ap = await db('core_aperturas').where({ apertura: d.apertura }).first();
    if (!ap) er.add(true, `La apertura ${d.apertura} no está registrada.`);
    else descAp = txt(ap.descripcion);
  }
  const cortes = await cortesValidos(db);
  const cant: Record<number, number> = {};
  let monto = 0;
  for (const k of cortes) {
    const v = d.cantidades?.[String(k)];
    if (v !== undefined && v !== null && (v as any) !== '') {
      if (!Number.isInteger(Number(v)) || Number(v) < 0) er.add(true, `La cantidad de vales de Bs ${k} debe ser un entero positivo.`);
      else cant[k] = Number(v);
    }
    cant[k] = cant[k] ?? 0;
    if (comb && cant[k] > 0) {
      const disp = Number((await db('com_vales').where({ estado: 'Disponible', corte: k }).whereRaw('lower(combustible) = ?', [comb.toLowerCase()]).count({ n: '*' }).first())?.n);
      er.add(cant[k] > disp, `Solo hay ${disp} vales de Bs ${k} (${comb}) disponibles.`);
    }
    monto += cant[k] * k;
  }
  er.add(monto <= 0, 'Indique la cantidad de vales a entregar.');
  let precio = 0;
  if (comb && isDate(d.fecha)) {
    precio = await precioVigente(db, comb, d.fecha);
    er.add(precio <= 0, `No hay precio registrado para ${comb} en CONFIG (tabla de precios).`);
  }
  const litros = precio > 0 ? monto / precio : 0;
  const lmax = await litrosMaximos(db, { placa, destino, desde: d.desde, hasta: d.hasta, programado: d.programado });
  if (lmax !== null && precio > 0 && litros > lmax + 0.001 && !txt(d.justificacion))
    er.add(true, `Los litros equivalentes (${fmt2(litros)} L) superan el máximo permitido (${fmt2(lmax)} L). Registre la JUSTIFICACIÓN DE EXCEDENTE (viaje, emergencia, etc.).`);
  if (destino === 'TURRIL' && puesto && litros > 0 && num(puesto.capacidad_l) > 0) {
    const s = await saldoTurril(db, placa);
    er.add(s + litros > num(puesto.capacidad_l) + 0.001, `La carga (${fmt2(litros)} L) supera la capacidad libre del puesto (capacidad ${fmt2(puesto.capacidad_l)} L, saldo actual ${fmt2(s)} L).`);
  }
  er.throwIfAny('No se puede emitir los vales:');

  // Advertencias (requieren confirmación)
  if ((Date.parse(d.hasta) - Date.parse(d.desde)) / 86400000 + 1 > 7) avisos.push('El periodo es mayor a una semana (el reglamento prevé programación semanal).');
  if (destino === 'VEHICULO' && uso === 'Operativo') {
    const mes = d.fecha.slice(0, 7) + '-01';
    const prog = await db('com_cronograma').where({ placa, mes }).first();
    if (!prog) avisos.push(`El vehículo no figura en el CRONOGRAMA de ${d.fecha.slice(5, 7)}/${d.fecha.slice(0, 4)}.`);
  }
  if (destino === 'VEHICULO' && num(d.lectura) > 0) {
    const ult = await ultimaLectura(db, placa, d.fecha);
    if (num(d.lectura) + 0.001 < ult) avisos.push(`El km/horómetro actual (${d.lectura}) es MENOR que la última lectura registrada (${ult}). Verifique el dato.`);
  }
  for (const x of await db('com_emisiones').where({ placa, estado: 'Emitido' })) {
    if (x.desde && x.hasta && x.desde <= d.hasta && x.hasta >= d.desde) avisos.push(`Ya existe la emisión ${x.nro} para ${placa} en un periodo que se superpone.`);
  }
  const resumen = { destino: `${placa} - ${descDest}`, conductor: d.conductor, combustible: comb, monto, litros: round(litros, 2), litros_max: lmax };
  if (avisos.length && !d.confirmar) return { ok: false, requiereConfirmacion: true, advertencias: avisos, resumen };

  return db.transaction(async (trx) => {
    const nro = await siguienteNro(trx, 'VC');
    const usados = new Set<number>();
    const detalle: string[] = [];
    const movs: MovK[] = [];
    for (const k of cortes) {
      if (cant[k] <= 0) continue;
      const cand = await trx('com_vales').where({ estado: 'Disponible', corte: k }).whereRaw('lower(combustible) = ?', [comb.toLowerCase()]).orderBy('id').limit(cant[k] + usados.size + 5000);
      const elegidos = cand.filter((v: any) => !usados.has(Number(v.nro_vale))).slice(0, cant[k]);
      if (elegidos.length < cant[k]) fail(`No hay suficientes vales de Bs ${k} con numeración distinta a los otros cortes de esta emisión. Emita los cortes en emisiones separadas.`);
      for (const v of elegidos) usados.add(Number(v.nro_vale));
      await trx('com_vales').whereIn('id', elegidos.map((v: any) => v.id)).update({ estado: 'Entregado', nro_emision: nro, destino, placa, conductor: d.conductor, fecha_entrega: d.fecha, fecha_estado: d.fecha });
      const rt = rangosTexto(elegidos.map((v: any) => Number(v.nro_vale)));
      detalle.push(`Bs ${k} x ${cant[k]}: ${rt}`);
      movs.push({ fecha: d.fecha, tipo: 'SALIDA', doc: nro, almacen: ALM_VALES, item: itemVale(comb, k), sal: cant[k], cu: k, placa, lectura: d.lectura ?? null, detalle: `Vales Nº ${rt} - ${d.conductor}` });
    }
    if (destino === 'TURRIL') movs.push({ fecha: d.fecha, tipo: 'INGRESO', doc: nro, almacen: placa, item: itemTurril(comb), ent: litros, cu: precio, detalle: `Carga con vales ${nro} - ${d.conductor}` });
    await kardexAdd(trx, u, movs);
    await trx('com_emisiones').insert({
      nro, fecha: d.fecha, destino, placa, descripcion_destino: descDest, uso, conductor: d.conductor, licencia, unidad: txt(d.unidad), solicitante: txt(d.solicitante), cargo_solicitante: txt(d.cargo_solicitante), combustible: comb,
      apertura: d.apertura, desc_apertura: descAp, trabajo: txt(d.trabajo), desde: d.desde, hasta: d.hasta, lectura_actual: d.lectura ?? null, programado: num(d.programado) || null,
      cant_vales: Object.values(cant).reduce((a, b) => a + b, 0), detalle_vales: detalle.join('; '), monto, precio_l: precio, litros: round(litros, 2), litros_max: lmax, justificacion: txt(d.justificacion), observaciones: txt(d.observaciones),
      estado: 'Emitido', usuario: u.usuario, registrado: nowIso(),
    });
    await audit(trx, u, 'EMISIÓN DE VALES', nro, `${placa} - Bs ${monto.toFixed(2)} - ${detalle.join('; ')}`);
    return { ok: true, advertencias: avisos, resumen, data: { nro, detalle: detalle.join('; '), monto, litros: round(litros, 2), planilla: destino === 'VEHICULO' && (await cfg(trx, 'PLANILLA_AL_EMITIR', 'SI')).toUpperCase() === 'SI' } };
  });
}

// ───────────── MOVIMIENTOS DE VALES ─────────────
export type AccionVale = 'Devolución' | 'Anulación' | 'Vencimiento' | 'Extravío';
const estadoRequerido: Record<AccionVale, string[]> = { Devolución: ['Entregado'], Anulación: ['Disponible'], Vencimiento: ['Disponible'], Extravío: ['Disponible', 'Entregado'] };
const nuevoEstado: Record<AccionVale, string> = { Devolución: 'Disponible', Anulación: 'Anulado', Vencimiento: 'Vencido', Extravío: 'Extraviado' };

/** Aplica la acción a los vales (filas de com_vales) y registra el kardex y el acta. */
export async function ejecutarMovimiento(db: Db, u: Usuario, accion: AccionVale, vales: any[], fecha: string, motivo: string, doc: string) {
  if (!vales.length) fail('No hay vales para procesar.');
  const porItem = new Map<string, { comb: string; corte: number; ent: number; sal: number; nums: number[] }>();
  for (const v of vales) {
    if (!estadoRequerido[accion].includes(v.estado)) fail(`El vale Nº ${v.nro_vale} está ${v.estado}; la acción ${accion} requiere: ${estadoRequerido[accion].join(' o ')}.`);
    const k = `${v.combustible}|${v.corte}`;
    const g: { comb: string; corte: number; ent: number; sal: number; nums: number[] } = porItem.get(k) ?? { comb: v.combustible, corte: v.corte, ent: 0, sal: 0, nums: [] };
    if (accion === 'Devolución') g.ent++;
    else if (v.estado === 'Disponible') g.sal++; // los entregados ya salieron del almacén
    g.nums.push(Number(v.nro_vale));
    porItem.set(k, g);
  }
  const upd: Record<string, unknown> = { estado: nuevoEstado[accion], fecha_estado: fecha, observaciones: `${accion}: ${motivo}`.slice(0, 300) };
  if (accion === 'Devolución') Object.assign(upd, { nro_emision: null, destino: null, placa: null, conductor: null, fecha_entrega: null });
  await db('com_vales').whereIn('id', vales.map((v) => v.id)).update(upd);
  const movs: MovK[] = [];
  for (const g of porItem.values()) {
    const detalle = `${accion}: ${motivo} - Nº ${rangosTexto(g.nums)}`;
    if (g.ent) movs.push({ fecha, tipo: 'DEVOLUCIÓN', doc, almacen: ALM_VALES, item: itemVale(g.comb, g.corte), ent: g.ent, cu: g.corte, detalle });
    if (g.sal) movs.push({ fecha, tipo: 'BAJA', doc, almacen: ALM_VALES, item: itemVale(g.comb, g.corte), sal: g.sal, cu: g.corte, detalle });
  }
  await kardexAdd(db, u, movs);
}

export async function movimientoPorRango(
  db: Db, u: Usuario,
  d: { fecha: string; accion: AccionVale; proveedor: string; combustible: string; corte: number; desde: number; hasta: number; motivo: string },
) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Fecha no válida.');
  e.add(!estadoRequerido[d.accion], 'Acción no válida.');
  e.add(!txt(d.motivo), 'Indique el motivo.');
  e.add(!d.desde || !d.hasta || d.hasta < d.desde, "Indique el rango de numeración ('desde' ≤ 'hasta').");
  e.throwIfAny('No se puede procesar el movimiento:');
  return db.transaction(async (trx) => {
    const vales = await trx('com_vales').where({ proveedor: d.proveedor, corte: d.corte }).whereRaw('lower(combustible) = ?', [d.combustible.toLowerCase()]).whereBetween('nro_vale', [d.desde, d.hasta]);
    const esperado = d.hasta - d.desde + 1;
    if (vales.length !== esperado) fail(`En el rango ${d.desde}-${d.hasta} solo existen ${vales.length} de ${esperado} vales registrados para ese proveedor, combustible y corte.`);
    const doc = await siguienteNro(trx, 'MV');
    await ejecutarMovimiento(trx, u, d.accion, vales, d.fecha, d.motivo, doc);
    await audit(trx, u, `VALES: ${d.accion.toUpperCase()}`, doc, `${vales.length} vales Bs ${d.corte} Nº ${d.desde}-${d.hasta}: ${d.motivo}`);
    return { doc, cantidad: vales.length };
  });
}

/** Anula una emisión completa: devuelve los vales al almacén y revierte el ingreso a turril. */
export async function anularEmision(db: Db, u: Usuario, nro: string, motivo: string) {
  if (!txt(motivo)) fail('Indique el motivo de la anulación.');
  return db.transaction(async (trx) => {
    const em = await trx('com_emisiones').where({ nro }).first();
    if (!em) throw new NotFound(`No existe la emisión ${nro}.`);
    if (em.estado !== 'Emitido') fail(`La emisión ${nro} está en estado ${em.estado} y no puede anularse.`);
    const vales = await trx('com_vales').where({ nro_emision: nro });
    const otros = vales.filter((v: any) => v.estado !== 'Entregado').length;
    if (otros) fail(`La emisión tiene ${otros} vale(s) que ya no están en estado Entregado.`);
    const doc = await siguienteNro(trx, 'MV');
    const fecha = today();
    await ejecutarMovimiento(trx, u, 'Devolución', vales, fecha, `Anulación de emisión ${nro}: ${motivo}`, doc);
    if (em.destino === 'TURRIL') await kardexAdd(trx, u, [{ fecha, tipo: 'BAJA', doc, almacen: em.placa, item: itemTurril(em.combustible), sal: num(em.litros), cu: num(em.precio_l), detalle: `Anulación de carga ${nro}` }]);
    await trx('com_emisiones').where({ nro }).update({ estado: 'Anulado', observaciones: `${txt(em.observaciones)} | ANULADA: ${motivo}`.trim() });
    await audit(trx, u, 'ANULACIÓN DE EMISIÓN', nro, motivo);
    return { nro, estado: 'Anulado', vales: vales.length };
  });
}

// ───────────── DESCARGO (Anexo 3) ─────────────
export interface DescargoInput {
  nro_emision: string;
  fecha: string;
  devolver_automaticamente?: boolean;
  observaciones?: string;
  lineas: { fecha: string; ruta?: string; lectura_salida?: number; lectura_llegada?: number; nro_vale?: number | null; litros?: number; factura?: string; estacion?: string }[];
  confirmar?: boolean;
}

export async function registrarDescargo(db: Db, u: Usuario, d: DescargoInput): Promise<Resultado<{ nro: string; estado: string; alertas: string }>> {
  const er = new Errores();
  er.add(!txt(d.nro_emision), 'Indique el número de emisión a descargar.');
  er.add(!isDate(d.fecha), 'Fecha de descargo vacía o no válida.');
  er.throwIfAny('No se puede registrar el descargo:');
  const em = await db('com_emisiones').where({ nro: d.nro_emision }).first();
  if (!em) fail(`No existe la emisión ${d.nro_emision}.`);
  if (em.estado !== 'Emitido') fail(`La emisión está en estado ${em.estado}; solo se descargan emisiones en estado Emitido.`);
  const vales = await db('com_vales').where({ nro_emision: d.nro_emision, estado: 'Entregado' });
  if (!vales.length) fail(`La emisión ${d.nro_emision} no tiene vales en estado Entregado para descargar.`);
  const veh = em.destino === 'VEHICULO' ? await db('com_vehiculos').where({ placa: em.placa }).first() : null;
  const medidor = veh ? txt(veh.medidor) || 'Km' : '';
  const cap = num(veh?.capacidad_tanque);
  const rendRef = veh ? await rendimientoVehiculo(db, veh) : 0;
  const tol = num(await cfg(db, 'TOLERANCIA_RENDIMIENTO', '0.2'));
  const plazo = await cfgNum(db, 'DIAS_PLAZO_DESCARGO', 3);
  const porNro = new Map<number, any>(vales.map((v: any) => [Number(v.nro_vale), v]));
  const precio = num(em.precio_l) || (await precioVigente(db, em.combustible, em.fecha));
  const avisos: string[] = [];
  const usados = new Set<number>();
  let litros = 0;
  let recorrido = 0;
  let montoUsado = 0;
  let lecIni: number | null = null;
  let lecFin: number | null = null;
  let prevLl: number | null = null;
  const filas = (d.lineas || []).filter((l) => l && (txt(l.fecha) || num(l.litros) || l.nro_vale || num(l.lectura_salida) || num(l.lectura_llegada)));
  if (!filas.length) er.add(true, 'Registre al menos una fila en la bitácora.');
  const ult = veh ? await ultimaLectura(db, em.placa, d.fecha) : 0;
  let n = 0;
  for (const l of filas) {
    n++;
    if (!isDate(l.fecha)) er.add(true, `Fila ${n}: fecha no válida.`);
    else if (l.fecha < em.desde || l.fecha > addDays(em.hasta, plazo)) avisos.push(`Fila ${n}: la fecha está fuera del periodo de la emisión.`);
    if (veh) {
      const ls = l.lectura_salida;
      const ll = l.lectura_llegada;
      if (!(num(ls) > 0 || ls === 0) || !(num(ll) > 0)) er.add(true, `Fila ${n}: registre la lectura de salida y de llegada (${medidor}).`);
      else {
        if (num(ll) < num(ls)) er.add(true, `Fila ${n}: la lectura de llegada es menor que la de salida.`);
        if (prevLl === null) {
          if (num(ls) + 0.001 < ult) er.add(true, `Fila ${n}: la lectura de salida (${ls}) es MENOR que la última lectura registrada del vehículo (${ult}). El ${medidor === 'Horas' ? 'horómetro' : 'km'} no puede retroceder.`);
          else if (ult > 0 && num(ls) - ult > 0.5) avisos.push(`Hay ${fmt2(num(ls) - ult)} ${medidor} entre la última lectura conocida (${ult}) y la primera salida, que no están registrados.`);
          lecIni = num(ls);
        } else {
          if (num(ls) + 0.001 < prevLl) er.add(true, `Fila ${n}: la lectura de salida es menor que la llegada de la fila anterior (${prevLl}).`);
          else if (num(ls) - prevLl > 0.5) avisos.push(`Fila ${n}: hay ${fmt2(num(ls) - prevLl)} ${medidor} sin registrar respecto a la fila anterior.`);
        }
        recorrido += Math.max(0, num(ll) - num(ls));
        prevLl = num(ll);
        lecFin = num(ll);
      }
    }
    const nv = l.nro_vale ? Number(l.nro_vale) : 0;
    const lit = num(l.litros);
    if (nv) {
      const v = porNro.get(nv);
      if (!v) er.add(true, `Fila ${n}: el vale Nº ${nv} NO fue entregado en la emisión ${d.nro_emision} (prohibido usar vales de otro vehículo o emisión - Art. 14).`);
      else if (usados.has(nv)) er.add(true, `Fila ${n}: el vale Nº ${nv} está repetido.`);
      else {
        usados.add(nv);
        if (!(lit > 0)) er.add(true, `Fila ${n}: indique los litros cargados con el vale ${nv}.`);
        if (!txt(l.factura)) er.add(true, `Fila ${n}: indique el Nº de factura de la estación de servicio.`);
        if (cap > 0 && lit > cap) er.add(true, `Fila ${n}: ${lit} L supera la capacidad del tanque (${cap} L).`);
        const esperado = precio > 0 ? num(v.corte) / precio : 0;
        if (esperado > 0 && lit > 0 && Math.abs(lit / esperado - 1) > 0.05) avisos.push(`Fila ${n}: ${lit.toFixed(2)} L no corresponde al valor del vale (Bs ${v.corte} = ${esperado.toFixed(2)} L).`);
        montoUsado += num(v.corte);
      }
    } else if (lit > 0) er.add(true, `Fila ${n}: hay litros cargados sin número de vale.`);
    litros += lit;
  }
  if (usados.size === 0 && !er.any) er.add(true, 'No se registró ninguna carga con vale. Si no se usó ningún vale, anule la emisión en DEVOLUCIÓN / BAJA.');
  const sinUsar = vales.filter((v: any) => !usados.has(Number(v.nro_vale)));
  if (sinUsar.length && !d.devolver_automaticamente && !er.any) er.add(true, `Hay ${sinUsar.length} vales sin utilizar. Marque 'Devolver automáticamente' o regístrelos en la bitácora.`);
  er.throwIfAny('No se puede registrar el descargo:');

  let estado = 'Conforme';
  let alertas = '';
  let rendReal = 0;
  let desv = 0;
  if (veh && recorrido > 0 && litros > 0 && rendRef > 0) {
    rendReal = litros / recorrido;
    desv = rendReal / rendRef - 1;
    if (Math.abs(desv) > tol) {
      estado = 'Observado';
      alertas = `Rendimiento ${rendReal.toFixed(3)} vs referencia ${rendRef.toFixed(3)} (${desv >= 0 ? '+' : ''}${Math.round(desv * 100)}%)`;
      avisos.push(`RENDIMIENTO FUERA DE TOLERANCIA: ${alertas}. El descargo quedará OBSERVADO.`);
    }
  } else if (veh && litros > 0 && recorrido <= 0) {
    estado = 'Observado';
    alertas = 'Litros cargados sin recorrido registrado';
    avisos.push(`Se cargaron ${litros.toFixed(2)} L sin recorrido registrado. El descargo quedará OBSERVADO.`);
  }
  const resumen = { vales_usados: usados.size, monto_usado: montoUsado, litros: round(litros, 2), recorrido, estado, devueltos: sinUsar.length };
  if (avisos.length && !d.confirmar) return { ok: false, requiereConfirmacion: true, advertencias: avisos, resumen };

  return db.transaction(async (trx) => {
    const nro = await siguienteNro(trx, 'DS');
    const lineaPorVale = new Map<number, any>();
    for (const l of filas) if (l.nro_vale) lineaPorVale.set(Number(l.nro_vale), l);
    for (const v of vales) {
      if (!usados.has(Number(v.nro_vale))) continue;
      const l = lineaPorVale.get(Number(v.nro_vale));
      await trx('com_vales').where({ id: v.id }).update({ estado: 'Utilizado', fecha_estado: d.fecha, observaciones: `Utilizado ${fmtDate(l.fecha)} ${num(l.litros)} L fact. ${txt(l.factura)}`.slice(0, 300) });
    }
    if (sinUsar.length) await ejecutarMovimiento(trx, u, 'Devolución', sinUsar, d.fecha, `Vales no utilizados - descargo ${nro}`, nro);
    for (const l of filas)
      await trx('com_descargo_lineas').insert({ nro, fecha: l.fecha, ruta: txt(l.ruta), lectura_salida: l.lectura_salida ?? null, lectura_llegada: l.lectura_llegada ?? null, nro_vale: l.nro_vale ?? null, litros: num(l.litros) || null, factura: txt(l.factura), estacion: txt(l.estacion) });
    await trx('com_descargos').insert({
      nro, fecha: d.fecha, nro_emision: d.nro_emision, placa: em.placa, conductor: em.conductor, medidor, lectura_inicial: lecIni, lectura_final: lecFin, recorrido: veh ? recorrido : null, litros: round(litros, 2), vales_usados: usados.size, monto_usado: montoUsado,
      vales_devueltos: sinUsar.length, rendimiento_real: rendReal ? round(rendReal, 4) : null, rendimiento_ref: rendRef || null, desviacion: rendReal ? round(desv, 4) : null, estado, alertas, observaciones: txt(d.observaciones), usuario: u.usuario, registrado: nowIso(),
    });
    await trx('com_emisiones').where({ nro: d.nro_emision }).update({ estado: 'Descargado', nro_descargo: nro });
    await audit(trx, u, 'DESCARGO DE VALES', nro, `${d.nro_emision} - ${usados.size} vales Bs ${montoUsado.toFixed(2)} - ${estado}`);
    return { ok: true, advertencias: avisos, resumen, data: { nro, estado, alertas } };
  });
}

// ───────────── Consultas ─────────────
export async function resumenVales(db: Db) {
  const rows: any[] = await db('com_vales').groupBy('combustible', 'corte', 'estado').select('combustible', 'corte', 'estado').count({ n: '*' });
  const out: Record<string, Record<string, number>> = {};
  for (const r of rows) {
    const k = `${r.combustible}|${r.corte}`;
    out[k] = out[k] ?? {};
    out[k][r.estado] = Number(r.n);
  }
  const lista = Object.entries(out).map(([k, v]) => {
    const [combustible, corte] = k.split('|');
    return { combustible, corte: Number(corte), ...v, disponible: v['Disponible'] ?? 0 };
  });
  const alertas: string[] = [];
  for (const x of lista) {
    const min = num(await cfg(db, `STOCK_MIN_${x.corte}`, '0'));
    if (min > 0 && (x.disponible as number) <= min) alertas.push(`Stock bajo de vales ${x.combustible} Bs ${x.corte}: ${x.disponible} disponibles (mínimo ${min}).`);
  }
  return { lista, alertas };
}
