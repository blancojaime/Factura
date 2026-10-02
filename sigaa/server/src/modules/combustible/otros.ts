/** Turriles, viajes oficiales (fondos en avance), conciliación con proveedores, cronograma y tablero. */
import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, txt, year, month, addDays, today, fmt2, diffDays } from '../../core/util.js';
import { cfg, cfgNum, siguienteNro } from '../../core/services.js';
import { audit, costoPromTurril, descargosPendientes, itemTurril, kardexAdd, precioVigente, rendimientoVehiculo, saldoTurril, ultimaLectura, recalcularContratos } from './base.js';

// ───────────── TURRILES ─────────────
export async function ingresoTurril(db: Db, u: Usuario, d: { fecha: string; puesto: string; litros: number; precio: number; factura: string; proveedor?: string }) {
  const er = new Errores();
  er.add(!isDate(d.fecha), 'Fecha vacía o no válida.');
  er.add(!txt(d.puesto), 'Seleccione el puesto de turriles.');
  er.add(!(num(d.litros) > 0), 'Indique los litros recibidos.');
  er.add(!(num(d.precio) > 0), 'Indique el precio unitario (Bs/L).');
  er.add(!txt(d.factura), 'Indique el número de factura (compra directa a nombre y NIT del GAM).');
  er.throwIfAny('No se puede registrar:');
  return db.transaction(async (trx) => {
    const p = await trx('com_puestos').where({ codigo: d.puesto }).first();
    if (!p) fail('El puesto no está registrado.');
    if (p.estado !== 'Activo') fail('El puesto no está Activo.');
    const saldo = await saldoTurril(trx, d.puesto);
    if (num(p.capacidad_l) > 0 && saldo + num(d.litros) > num(p.capacidad_l) + 0.001) fail(`Se supera la capacidad del puesto (${fmt2(p.capacidad_l)} L). Saldo actual: ${fmt2(saldo)} L.`);
    const doc = await siguienteNro(trx, 'TI');
    await kardexAdd(trx, u, [{ fecha: d.fecha, tipo: 'INGRESO', doc, almacen: d.puesto, item: itemTurril(p.combustible), ent: num(d.litros), cu: num(d.precio), detalle: `Compra directa Fact. ${d.factura}${txt(d.proveedor) ? ' - ' + d.proveedor : ''}` }]);
    await audit(trx, u, 'INGRESO A TURRIL', doc, `${d.puesto} ${d.litros} L Bs/L ${d.precio}`);
    return { doc, saldo: await saldoTurril(trx, d.puesto) };
  });
}

export async function despachoTurril(db: Db, u: Usuario, d: { fecha: string; puesto: string; placa: string; operador: string; litros: number; lectura: number; apertura: string; obra: string }) {
  const er = new Errores();
  er.add(!isDate(d.fecha), 'Fecha vacía o no válida.');
  er.add(!txt(d.puesto), 'Seleccione el puesto de turriles.');
  er.add(!txt(d.placa), 'Seleccione el vehículo o equipo.');
  er.add(!txt(d.operador), 'Seleccione el operador / conductor.');
  er.add(!(num(d.litros) > 0), 'Indique los litros despachados.');
  er.add(!(num(d.lectura) > 0), 'Indique la lectura del km u horómetro (control de rendimiento).');
  er.add(!txt(d.apertura), 'Seleccione la apertura programática.');
  er.add(!txt(d.obra), 'Indique la obra o actividad.');
  er.throwIfAny('No se puede registrar el despacho:');
  return db.transaction(async (trx) => {
    const p = await trx('com_puestos').where({ codigo: d.puesto }).first();
    if (!p) fail('El puesto no está registrado.');
    const v = await trx('com_vehiculos').where({ placa: d.placa }).first();
    if (!v) fail('El vehículo/equipo no está registrado.');
    const er2 = new Errores();
    er2.add(v.estado !== 'Activo', 'El vehículo/equipo no está Activo.');
    er2.add(txt(v.combustible).toLowerCase() !== txt(p.combustible).toLowerCase(), `El vehículo usa ${v.combustible} y el puesto almacena ${p.combustible}.`);
    er2.add(num(v.capacidad_tanque) > 0 && num(d.litros) > num(v.capacidad_tanque), `Los litros superan la capacidad del tanque (${v.capacidad_tanque} L).`);
    er2.add(!(await trx('com_conductores').where({ nombre: d.operador }).first()), 'El operador no está registrado.');
    er2.add(!(await trx('core_aperturas').where({ apertura: d.apertura }).first()), 'La apertura no está registrada.');
    const saldo = await saldoTurril(trx, d.puesto);
    er2.add(num(d.litros) > saldo + 0.001, `Saldo insuficiente en el puesto: ${fmt2(saldo)} L.`);
    const ult = await ultimaLectura(trx, d.placa, d.fecha);
    er2.add(num(d.lectura) + 0.001 < ult, `La lectura (${d.lectura}) es MENOR que la última registrada del vehículo (${ult}).`);
    er2.throwIfAny('No se puede registrar el despacho:');
    const cu = await costoPromTurril(trx, d.puesto);
    const doc = await siguienteNro(trx, 'TD');
    await kardexAdd(trx, u, [{ fecha: d.fecha, tipo: 'DESPACHO', doc, almacen: d.puesto, item: itemTurril(p.combustible), sal: num(d.litros), cu, placa: d.placa, lectura: num(d.lectura), detalle: `${d.obra} - ${d.operador} - ${d.apertura}` }]);
    await audit(trx, u, 'DESPACHO DE TURRIL', doc, `${d.puesto} → ${d.placa} ${d.litros} L`);
    return { doc, saldo: await saldoTurril(trx, d.puesto), costo_unit: cu };
  });
}

// ───────────── VIAJES OFICIALES (fondos en avance, Anexos 4 y 6) ─────────────
export interface ViajeInput {
  fecha: string; placa: string; conductor: string; origen: string; destino: string; salida: string; retorno: string;
  km_estimado?: number; litros_estimados?: number; apertura: string; fondo: number; motivo: string; nota?: string; comprobante?: string; funcionarios?: string;
  confirmar?: boolean;
}
export async function registrarViaje(db: Db, u: Usuario, d: ViajeInput) {
  const er = new Errores();
  er.add(!isDate(d.fecha), 'Fecha de solicitud no válida.');
  er.add(!txt(d.placa), 'Seleccione el vehículo.');
  er.add(!txt(d.conductor), 'Seleccione el conductor.');
  er.add(!txt(d.origen) || !txt(d.destino), 'Indique el origen y el destino.');
  if (!isDate(d.salida) || !isDate(d.retorno)) er.add(true, 'Indique las fechas de salida y de retorno.');
  else er.add(d.retorno < d.salida, 'La fecha de retorno es anterior a la de salida.');
  er.add(!txt(d.apertura), 'Seleccione la apertura programática.');
  er.add(!(num(d.fondo) > 0), 'Indique el monto del fondo en avance (Bs).');
  er.add(!txt(d.motivo), 'Describa el motivo o comisión del viaje.');
  const v = txt(d.placa) ? await db('com_vehiculos').where({ placa: d.placa }).first() : null;
  if (txt(d.placa)) er.add(!v, 'El vehículo no está registrado.');
  er.add(!!v && v.estado !== 'Activo', 'El vehículo no está Activo.');
  const c = txt(d.conductor) ? await db('com_conductores').where({ nombre: d.conductor }).first() : null;
  if (txt(d.conductor)) er.add(!c, 'El conductor no está registrado.');
  if (c) {
    er.add(c.estado !== 'Activo', 'El conductor no está Activo.');
    er.add(!!c.vence_licencia && isDate(d.salida) && c.vence_licencia < d.salida, 'La licencia del conductor está VENCIDA.');
    if (isDate(d.salida)) er.add((await descargosPendientes(db, d.conductor, d.salida)) > 0, 'El conductor tiene descargos de vales VENCIDOS sin presentar.');
  }
  if (txt(d.apertura)) er.add(!(await db('core_aperturas').where({ apertura: d.apertura }).first()), 'La apertura no está registrada.');
  const avisos: string[] = [];
  for (const x of await db('com_viajes').where({ conductor: d.conductor, estado: 'En curso' })) {
    if (x.retorno && isDate(d.salida) && x.retorno < d.salida) er.add(true, `El conductor no presentó el descargo del viaje ${x.nro}.`);
    else avisos.push(`El conductor tiene el viaje ${x.nro} aún en curso.`);
  }
  er.throwIfAny('No se puede registrar el viaje:');
  if (avisos.length && !d.confirmar) return { ok: false, requiereConfirmacion: true, advertencias: avisos };
  return db.transaction(async (trx) => {
    const nro = await siguienteNro(trx, 'VJ');
    const ap = await trx('core_aperturas').where({ apertura: d.apertura }).first();
    await trx('com_viajes').insert({
      nro, fecha: d.fecha, placa: d.placa, conductor: d.conductor, origen: d.origen, destino: d.destino, salida: d.salida, retorno: d.retorno, km_estimado: num(d.km_estimado) || null, litros_estimados: num(d.litros_estimados) || null,
      apertura: d.apertura, desc_apertura: txt(ap?.descripcion), fondo: num(d.fondo), motivo: d.motivo, nota: txt(d.nota), comprobante: txt(d.comprobante), funcionarios: txt(d.funcionarios), estado: 'En curso', usuario: u.usuario, registrado: nowIso(),
    });
    await audit(trx, u, 'REGISTRO DE VIAJE', nro, `${d.placa} ${d.origen}→${d.destino} fondo Bs ${num(d.fondo).toFixed(2)}`);
    return { ok: true, data: { nro }, advertencias: avisos };
  });
}

export interface DescargoViajeInput {
  nro: string; fecha_descargo: string; actividades?: string; conclusiones?: string; confirmar?: boolean;
  tramos: { fecha: string; origen: string; destino: string; hora_salida?: string; hora_llegada?: string; km_inicial: number; km_final: number }[];
  compras: { fecha: string; estacion: string; factura: string; litros: number; total: number }[];
}
export async function descargoViaje(db: Db, u: Usuario, d: DescargoViajeInput) {
  const vj = await db('com_viajes').where({ nro: d.nro }).first();
  if (!vj) throw new NotFound(`No existe el viaje ${d.nro}.`);
  if (vj.estado !== 'En curso') fail(`El viaje está ${vj.estado}.`);
  const er = new Errores();
  er.add(!isDate(d.fecha_descargo), 'Fecha de descargo no válida.');
  const veh = await db('com_vehiculos').where({ placa: vj.placa }).first();
  const cap = num(veh?.capacidad_tanque);
  const rendRef = veh ? await rendimientoVehiculo(db, veh) : 0;
  const avisos: string[] = [];
  let recorrido = 0;
  let prevKf: number | null = null;
  const ult = await ultimaLectura(db, vj.placa, d.fecha_descargo);
  (d.tramos || []).forEach((t, i) => {
    const n = i + 1;
    if (!txt(t.origen) || !txt(t.destino)) er.add(true, `Tramo ${n}: indique origen y destino.`);
    if (!isDate(t.fecha)) er.add(true, `Tramo ${n}: fecha no válida.`);
    if (!(num(t.km_final) > 0) || t.km_inicial === undefined || t.km_inicial === null) return er.add(true, `Tramo ${n}: registre el km inicial y final.`);
    if (num(t.km_final) < num(t.km_inicial)) return er.add(true, `Tramo ${n}: el km final es menor que el inicial.`);
    if (prevKf === null) {
      if (num(t.km_inicial) + 0.001 < ult && ult > 0) er.add(true, `Tramo ${n}: el km inicial (${t.km_inicial}) es MENOR que la última lectura registrada (${ult}).`);
      else if (ult > 0 && num(t.km_inicial) - ult > 0.5) avisos.push(`Hay ${fmt2(num(t.km_inicial) - ult)} km entre la última lectura y el inicio del viaje.`);
    } else if (num(t.km_inicial) + 0.001 < prevKf) er.add(true, `Tramo ${n}: el km inicial es menor que el km final del tramo anterior.`);
    recorrido += num(t.km_final) - num(t.km_inicial);
    prevKf = num(t.km_final);
  });
  er.add(!(d.tramos || []).length, 'Registre al menos un tramo del viaje.');
  let litros = 0;
  let gastado = 0;
  const pv = await precioVigente(db, txt(veh?.combustible), d.fecha_descargo || today());
  (d.compras || []).forEach((c, i) => {
    const n = i + 1;
    if (!isDate(c.fecha)) er.add(true, `Compra ${n}: fecha no válida.`);
    if (!txt(c.estacion)) er.add(true, `Compra ${n}: indique la estación de servicio.`);
    if (!txt(c.factura)) er.add(true, `Compra ${n}: indique el Nº de factura (a nombre y NIT del GAM).`);
    if (!(num(c.litros) > 0) || !(num(c.total) > 0)) er.add(true, `Compra ${n}: indique los litros y el total en Bs.`);
    if (cap > 0 && num(c.litros) > cap) er.add(true, `Compra ${n}: ${c.litros} L supera la capacidad del tanque (${cap} L).`);
    if (pv > 0 && num(c.litros) > 0 && Math.abs(num(c.total) / num(c.litros) / pv - 1) > 0.1) avisos.push(`Compra ${n}: precio de Bs ${(num(c.total) / num(c.litros)).toFixed(2)} por litro difiere más del 10% del vigente (Bs ${pv}).`);
    litros += num(c.litros);
    gastado += num(c.total);
  });
  if (!(d.compras || []).length) avisos.push('No se registraron compras de combustible: todo el fondo debe devolverse.');
  er.throwIfAny('No se puede registrar el descargo del viaje:');
  const saldo = round(num(vj.fondo) - gastado, 2);
  let resultado = 'Conforme';
  const alertas: string[] = [];
  if (saldo < 0) {
    avisos.push(`El gasto supera el fondo en Bs ${fmt2(-saldo)} (reembolso sujeto a aprobación).`);
    resultado = 'Observado';
    alertas.push(`Gasto excede el fondo en Bs ${fmt2(-saldo)}`);
  }
  let rendReal = 0;
  if (recorrido > 0 && litros > 0 && rendRef > 0) {
    rendReal = litros / recorrido;
    const desv = rendReal / rendRef - 1;
    const tol = num(await cfg(db, 'TOLERANCIA_RENDIMIENTO', '0.2'));
    if (Math.abs(desv) > tol) {
      resultado = 'Observado';
      alertas.push(`Rendimiento ${rendReal.toFixed(3)} vs ${rendRef.toFixed(3)} (${desv >= 0 ? '+' : ''}${Math.round(desv * 100)}%)`);
      avisos.push(`RENDIMIENTO FUERA DE TOLERANCIA (${desv >= 0 ? '+' : ''}${Math.round(desv * 100)}%).`);
    }
  }
  const resumen = { km: recorrido, litros, gastado, saldo, resultado };
  if (avisos.length && !d.confirmar) return { ok: false, requiereConfirmacion: true, advertencias: avisos, resumen };
  return db.transaction(async (trx) => {
    for (const t of d.tramos) await trx('com_viajes_det').insert({ nro: d.nro, tipo: 'TRAMO', placa: vj.placa, fecha: t.fecha, origen: t.origen, destino: t.destino, hora_salida: txt(t.hora_salida), hora_llegada: txt(t.hora_llegada), km_inicial: t.km_inicial, km_final: t.km_final, recorrido: num(t.km_final) - num(t.km_inicial) });
    for (const c of d.compras || []) await trx('com_viajes_det').insert({ nro: d.nro, tipo: 'COMPRA', placa: vj.placa, fecha: c.fecha, estacion: c.estacion, factura: c.factura, litros: c.litros, total: c.total });
    await trx('com_viajes').where({ nro: d.nro }).update({
      estado: 'Descargado', fecha_descargo: d.fecha_descargo, km_recorrido: recorrido, litros_comprados: litros, gastado: round(gastado, 2), saldo, rendimiento_real: rendReal ? round(rendReal, 4) : null,
      resultado, alertas: alertas.join('; '), actividades: txt(d.actividades), conclusiones: txt(d.conclusiones),
    });
    await audit(trx, u, 'DESCARGO DE VIAJE', d.nro, `${resultado} - gastado Bs ${gastado.toFixed(2)} - saldo Bs ${saldo.toFixed(2)}`);
    return { ok: true, advertencias: avisos, resumen, data: { nro: d.nro, resultado, saldo } };
  });
}

// ───────────── CONCILIACIÓN CON EL PROVEEDOR ─────────────
export interface CobroInput { nro_vale: number; fecha?: string; placa?: string; litros?: number; monto: number; factura?: string }
export async function conciliarProveedor(db: Db, u: Usuario, d: { proveedor: string; contrato?: string; desde: string; hasta: string; cobros: CobroInput[] }) {
  const er = new Errores();
  er.add(!txt(d.proveedor), 'Seleccione el proveedor.');
  er.add(!isDate(d.desde) || !isDate(d.hasta), 'Indique el periodo (desde / hasta).');
  er.add(!(d.cobros || []).length, 'Cargue el detalle de vales cobrados por el proveedor.');
  er.throwIfAny('No se puede conciliar:');
  return db.transaction(async (trx) => {
    const nro = await siguienteNro(trx, 'CC');
    const filas: any[] = [];
    const vistos = new Map<number, number>();
    for (const c of d.cobros) vistos.set(Number(c.nro_vale), (vistos.get(Number(c.nro_vale)) ?? 0) + 1);
    const tocados = new Set<number>();
    let totalPagar = 0;
    let nConf = 0;
    let nObs = 0;
    for (const c of d.cobros) {
      const nv = Number(c.nro_vale);
      let resultado = '';
      let detalle = '';
      let pagable = false;
      let v: any = null;
      const cands = await trx('com_vales').where({ proveedor: d.proveedor, nro_vale: nv });
      v = cands.length > 1 ? cands.find((x: any) => num(x.corte) === num(c.monto)) ?? cands[0] : cands[0];
      if ((vistos.get(nv) ?? 0) > 1) { resultado = 'DUPLICADO'; detalle = 'El vale aparece más de una vez en el archivo del proveedor.'; }
      else if (!v) { resultado = 'NO REGISTRADO'; detalle = 'El número de vale no existe en el sistema para este proveedor.'; }
      else if (v.conciliacion) { resultado = 'YA CONCILIADO'; detalle = `El vale ya fue conciliado y pagado en ${v.conciliacion}.`; }
      else if (v.estado === 'Disponible') { resultado = 'NO ENTREGADO'; detalle = 'El vale figura en ALMACÉN (no fue entregado). Posible uso indebido: investigar.'; }
      else if (['Anulado', 'Vencido', 'Extraviado'].includes(v.estado)) { resultado = 'DADO DE BAJA'; detalle = `El vale está ${String(v.estado).toUpperCase()} en el sistema.`; }
      else if (Math.abs(num(c.monto) - num(v.corte)) > 0.005) { resultado = 'MONTO DIFERENTE'; detalle = `Cobrado Bs ${num(c.monto).toFixed(2)}; valor del vale Bs ${num(v.corte).toFixed(2)}.`; }
      else if (txt(c.placa) && txt(v.placa) && txt(c.placa).toUpperCase().replace(/[\s-]/g, '') !== txt(v.placa).toUpperCase().replace(/[\s-]/g, '')) { resultado = 'PLACA DIFERENTE'; detalle = `Cargado a ${c.placa} pero entregado a ${v.placa} (Art. 14).`; }
      else if (v.estado === 'Entregado') { resultado = 'SIN DESCARGO'; detalle = `Cobrado por el proveedor; el conductor aún no presentó el descargo de ${v.nro_emision}.`; }
      else if (v.estado === 'Utilizado') { resultado = 'CONFORME'; pagable = true; }
      else { resultado = 'REVISAR'; detalle = `Estado del vale: ${v.estado}`; }
      if (pagable) { totalPagar += num(c.monto); nConf++; tocados.add(v.id); } else nObs++;
      filas.push({ nro, fecha: today(), proveedor: d.proveedor, contrato: txt(d.contrato), desde: d.desde, hasta: d.hasta, nro_vale: nv, corte: v?.corte ?? null, monto_cobrado: num(c.monto), fecha_carga: c.fecha ?? null, placa_cobro: txt(c.placa), placa_sistema: v?.placa ?? null, estado_sistema: v?.estado ?? null, nro_emision: v?.nro_emision ?? null, resultado, detalle, pagable, factura: txt(c.factura), usuario: u.usuario });
    }
    // Vales utilizados en el periodo que el proveedor no cobró
    const cobrados = new Set(d.cobros.map((c) => Number(c.nro_vale)));
    const nocob = await trx('com_vales').where({ proveedor: d.proveedor, estado: 'Utilizado' }).whereNull('conciliacion').whereBetween('fecha_estado', [d.desde, d.hasta]);
    for (const v of nocob) if (!cobrados.has(Number(v.nro_vale)))
      filas.push({ nro, fecha: today(), proveedor: d.proveedor, contrato: txt(d.contrato), desde: d.desde, hasta: d.hasta, nro_vale: v.nro_vale, corte: v.corte, monto_cobrado: 0, placa_sistema: v.placa, estado_sistema: v.estado, nro_emision: v.nro_emision, resultado: 'NO COBRADO', detalle: 'Utilizado según el descargo pero no cobrado en este periodo.', pagable: false, usuario: u.usuario });
    await trx.batchInsert('com_conciliaciones', filas, 30);
    if (tocados.size) await trx('com_vales').whereIn('id', [...tocados]).update({ conciliacion: nro });
    await audit(trx, u, 'CONCILIACIÓN CON PROVEEDOR', nro, `${d.proveedor} - conformes ${nConf} (Bs ${totalPagar.toFixed(2)}), observados ${nObs}`);
    const resumen: Record<string, number> = {};
    for (const f of filas) resumen[f.resultado] = (resumen[f.resultado] ?? 0) + 1;
    return { nro, conformes: nConf, observados: nObs, total_pagar: round(totalPagar, 2), resumen };
  });
}

// ───────────── CRONOGRAMA ─────────────
export async function guardarCronograma(db: Db, u: Usuario, mes: string, filas: { placa: string; obra?: string; apertura?: string; dias?: number; km_horas: number; responsable?: string; observaciones?: string }[]) {
  const m = txt(mes).slice(0, 7) + '-01';
  if (!isDate(m)) fail('Indique el mes del cronograma.');
  return db.transaction(async (trx) => {
    await trx('com_cronograma').where({ mes: m }).delete();
    let n = 0;
    for (const f of filas) {
      const v = await trx('com_vehiculos').where({ placa: txt(f.placa).toUpperCase() }).first();
      if (!v) fail(`La placa ${f.placa} no está registrada.`);
      const rend = await rendimientoVehiculo(trx, v);
      await trx('com_cronograma').insert({ mes: m, placa: v.placa, obra: txt(f.obra), apertura: txt(f.apertura), dias: f.dias ?? null, km_horas: num(f.km_horas), litros_estimados: round(num(f.km_horas) * rend, 1), responsable: txt(f.responsable), observaciones: txt(f.observaciones) });
      n++;
    }
    await audit(trx, u, 'CRONOGRAMA MENSUAL', m.slice(0, 7), `${n} filas`);
    return { mes: m, filas: n };
  });
}
export async function listarCronograma(db: Db, mes?: string) {
  const q = db('com_cronograma as c').leftJoin('com_vehiculos as v', 'v.placa', 'c.placa').select('c.*', 'v.tipo', 'v.marca', 'v.medidor').orderBy(['c.mes', 'c.placa']);
  if (mes) q.where('c.mes', mes.slice(0, 7) + '-01');
  return q;
}

// ───────────── TABLERO ─────────────
export async function tablero(db: Db, gest?: number) {
  const g = gest ?? Number((await cfg(db, 'Gestion', String(year(today())))) || year(today()));
  const em = (await db('com_emisiones').whereNot({ estado: 'Anulado' })).filter((e: any) => year(e.fecha) === g);
  const mes = Array.from({ length: 12 }, (_, i) => ({ mes: i + 1, gasolina: 0, diesel: 0 }));
  const veh = new Map<string, number>();
  const ape = new Map<string, number>();
  let monto = 0;
  let litros = 0;
  for (const e of em) {
    const m = mes[month(e.fecha) - 1];
    if (String(e.combustible).toLowerCase().startsWith('di')) m.diesel += num(e.monto);
    else m.gasolina += num(e.monto);
    monto += num(e.monto);
    litros += num(e.litros);
    veh.set(e.placa, (veh.get(e.placa) ?? 0) + num(e.monto));
    ape.set(e.apertura, (ape.get(e.apertura) ?? 0) + num(e.monto));
  }
  const aperturas = await db('core_aperturas');
  const vales = await db('com_vales').where({ estado: 'Disponible' }).sum({ t: 'corte' }).first();
  const contratos = await db('com_contratos').where({ estado: 'Vigente' }).sum({ t: 'saldo' }).first();
  const plazo = await cfgNum(db, 'DIAS_PLAZO_DESCARGO', 3);
  const hoy = today();
  const vencidos = (await db('com_emisiones').where({ estado: 'Emitido' }).select('hasta')).filter((e: any) => e.hasta && addDays(e.hasta, plazo) < hoy).length;
  return {
    gestion: g, monto_emitido: round(monto, 2), litros_emitidos: round(litros, 2), emisiones: em.length, vales_disponibles_bs: num(vales?.t), saldo_contratos: num(contratos?.t), descargos_vencidos: vencidos,
    mensual: mes.map((m) => ({ ...m, gasolina: round(m.gasolina, 0), diesel: round(m.diesel, 0) })),
    top_vehiculos: [...veh.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([placa, monto]) => ({ placa, monto: round(monto, 2) })),
    aperturas: aperturas.map((a: any) => ({ apertura: a.apertura, descripcion: a.descripcion, presupuesto: num(a.presupuesto), ejecutado: round(ape.get(a.apertura) ?? 0, 2), porcentaje: num(a.presupuesto) > 0 ? round(((ape.get(a.apertura) ?? 0) / num(a.presupuesto)) * 100, 1) : 0 })),
  };
}
void diffDays;
void recalcularContratos;
