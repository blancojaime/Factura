import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, sumarDiasHabiles, today, txt } from '../../core/util.js';
import { cfgNum, siguienteNro } from '../../core/services.js';
import { bitacoraUsuario, requerirBodega } from './helpers.js';
import { consumirPEPS, stockDe } from './stock.js';

export interface BajaInput {
  nro?: string;
  fecha: string;
  cod_bod: string;
  causal: string;
  responsable: string;
  justificacion: string;
  nro_ra?: string;
  fecha_ra?: string;
  items: { cod_item: string; cantidad: number; id_lote?: string }[];
  pasos?: { orden: number; referencia?: string; fecha?: string; estado?: string; respaldo?: string }[];
}

/** Trámite del expediente según el grupo de la causal (A: hurto/robo/siniestro; B: merma/vencimiento/deterioro). */
export async function tramiteDeCausal(db: Db, causal: string) {
  const c = await db('alm_causales').where({ causal }).first();
  if (!c) fail('La causal de baja no existe.');
  const pasos = await db('alm_pasos').where({ grupo: c.grupo }).orderBy('orden');
  return pasos.map((p: any) => ({ orden: p.orden, paso: p.paso + (p.obligatorio === 'SI' ? '  (*)' : ''), doc: p.doc, clase: p.clase, referencia: '', fecha: '', estado: 'PENDIENTE', respaldo: '' }));
}

export async function guardarBaja(db: Db, u: Usuario, d: BajaInput) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha de solicitud.');
  e.add(!txt(d.causal), 'Seleccione la causal de baja.');
  e.add(!txt(d.responsable), 'Registre al responsable de la solicitud.');
  e.add(!txt(d.justificacion), 'Registre la justificación o descripción del hecho.');
  e.add(!!txt(d.fecha_ra) && !isDate(d.fecha_ra), 'La fecha de la Resolución Administrativa no es válida.');
  e.throwIfAny('Expediente incompleto:');
  const bod = await requerirBodega(db, d.cod_bod);
  return db.transaction(async (trx) => {
    const causal = await trx('alm_causales').where({ causal: d.causal }).first();
    if (!causal) fail('La causal de baja no existe.');
    let nro = txt(d.nro);
    if (nro) {
      const ex = await trx('alm_bajas').where({ nro }).first();
      if (ex && ex.estado === 'ANULADO') fail('El expediente está ANULADO.');
    }
    const filas: any[] = [];
    const vistos = new Set<string>();
    let j = 0;
    for (const it of d.items || []) {
      if (!txt(it.cod_item) && !num(it.cantidad)) continue;
      j++;
      const cod = txt(it.cod_item);
      const cat = await trx('alm_catalogo').where({ codigo: cod }).first();
      if (!cat) fail(`Ítem ${j}: el código '${cod}' no existe en el catálogo.`);
      const cant = num(it.cantidad);
      if (!(cant > 0)) fail(`Ítem ${j}: registre la cantidad a dar de baja.`);
      const idL = txt(it.id_lote);
      let saldo: number;
      if (idL) {
        const l = await trx('alm_lotes').where({ id_lote: idL }).first();
        if (!l) fail(`Ítem ${j}: el lote ${idL} no existe.`);
        if (l.cod_item !== cod || l.cod_bod !== bod) fail(`Ítem ${j}: el lote ${idL} no corresponde al ítem o a la bodega.`);
        saldo = num(l.saldo);
      } else saldo = await stockDe(trx, bod, cod);
      const ex = nro ? await trx('alm_bajas').where({ nro }).first() : null;
      if (cant > saldo + 1e-6 && ex?.estado !== 'BAJA EJECUTADA') fail(`Ítem ${j}: la cantidad (${cant}) excede el saldo disponible (${saldo}).`);
      const k = cod + '|' + idL;
      if (vistos.has(k)) fail(`Ítem ${j}: está repetido; sume las cantidades.`);
      vistos.add(k);
      filas.push({ item: j, cod_item: cod, descripcion: cat.descripcion, unidad: cat.unidad, id_lote: idL, cantidad: cant, precio_unit: 0, total: 0 });
    }
    if (!filas.length) fail('Registre al menos un ítem a dar de baja.');
    // Valoración estimada al precio promedio
    let totalEst = 0;
    for (const f of filas) {
      const rows = await trx('alm_lotes').where({ cod_bod: bod, cod_item: f.cod_item, estado: 'ACTIVO' }).modify((q) => f.id_lote && q.where({ id_lote: f.id_lote }));
      const q = rows.reduce((t: number, r: any) => t + num(r.saldo), 0);
      const v = rows.reduce((t: number, r: any) => t + num(r.saldo) * num(r.precio_unit), 0);
      const pu = q > 0 ? round(v / q, 4) : num((await trx('alm_catalogo').where({ codigo: f.cod_item }).first('precio_ref'))?.precio_ref);
      f.precio_unit = pu;
      f.total = round(pu * f.cantidad, 2);
      totalEst += f.total;
    }
    const cab = {
      fecha: d.fecha, cod_bod: bod, causal: d.causal, grupo: causal.grupo, responsable: txt(d.responsable), justificacion: txt(d.justificacion),
      nro_ra: txt(d.nro_ra), fecha_ra: txt(d.fecha_ra).slice(0, 10) || null,
    };
    const existente = nro ? await trx('alm_bajas').where({ nro }).first() : null;
    if (existente) {
      if (existente.estado === 'EN TRÁMITE') {
        await trx('alm_bajas').where({ nro }).update({ ...cab, total: round(totalEst, 2) });
        await trx('alm_bajas_det').where({ nro }).delete();
        for (const f of filas) await trx('alm_bajas_det').insert({ nro, ...f });
      } else {
        await trx('alm_bajas').where({ nro }).update({ nro_ra: cab.nro_ra, fecha_ra: cab.fecha_ra });
      }
    } else {
      nro = nro || (await siguienteNro(trx, 'BAJ'));
      await trx('alm_bajas').insert({ nro, ...cab, total: round(totalEst, 2), estado: 'EN TRÁMITE', fecha_reg: nowIso() });
      for (const f of filas) await trx('alm_bajas_det').insert({ nro, ...f });
      const pasos = await tramiteDeCausal(trx, d.causal);
      for (const p of pasos) await trx('alm_bajas_paso').insert({ nro, ...p });
    }
    // Pasos del trámite
    for (const p of d.pasos || []) {
      const row = await trx('alm_bajas_paso').where({ nro, orden: p.orden }).first();
      if (!row) fail(`El paso ${p.orden} no existe en el trámite.`);
      const estado = txt(p.estado).toUpperCase() || 'PENDIENTE';
      if (estado === 'HECHO') {
        if (txt(p.fecha) && !isDate(p.fecha)) fail(`Paso ${p.orden}: la fecha no es válida.`);
        if (row.clase === 'PUBLICACION') {
          if (!isDate(p.fecha)) fail(`Paso ${p.orden}: registre la fecha de inicio de la publicación.`);
          const dias = await cfgNum(trx, 'DiasPublicacion', 15);
          const limite = sumarDiasHabiles(String(p.fecha).slice(0, 10), dias);
          if (limite > today()) fail(`Paso ${p.orden}: el plazo mínimo de publicación de ${dias} días hábiles vence el ${limite}.`);
        }
        if (row.clase === 'RA' && (!txt(cab.nro_ra) || !cab.fecha_ra)) fail(`Paso ${p.orden}: registre el Nº y la fecha de la Resolución Administrativa en la cabecera.`);
      }
      await trx('alm_bajas_paso').where({ id: row.id }).update({ referencia: txt(p.referencia), fecha: txt(p.fecha).slice(0, 10) || null, estado, respaldo: txt(p.respaldo) });
    }
    await bitacoraUsuario(trx, u, 'REGISTRO DE EXPEDIENTE DE BAJA', nro, `${d.causal} - Bs ${totalEst.toFixed(2)}`);
    return { nro, total: round(totalEst, 2) };
  });
}

/** Ejecuta la baja física y contable (descarga los lotes por PEPS, aun vencidos). Requiere RA y pasos previos HECHOS. */
export async function ejecutarBaja(db: Db, u: Usuario, nro: string) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_bajas').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el expediente ${nro}.`);
    if (h.estado !== 'EN TRÁMITE') fail(`El expediente está ${h.estado}; la baja solo se ejecuta una vez, desde EN TRÁMITE.`);
    if (!txt(h.nro_ra) || !isDate(h.fecha_ra)) fail('No se puede dar de baja sin la Resolución Administrativa (art. 30-II): registre su Nº y fecha y márquela como HECHA en el trámite.');
    const pasos = await trx('alm_bajas_paso').where({ nro }).orderBy('orden');
    if (!pasos.length) fail('Cargue el trámite del expediente.');
    const pb = pasos.find((p: any) => p.clase === 'BAJA');
    if (!pb) fail('El trámite no tiene el paso de baja de registros.');
    const defs = await trx('alm_pasos').where({ grupo: h.grupo });
    const falt = pasos.filter((p: any) => p.orden < pb.orden && defs.find((x: any) => x.orden === p.orden)?.obligatorio === 'SI' && p.estado !== 'HECHO').map((p: any) => '  - ' + p.paso);
    if (falt.length) fail('Antes de dar de baja los registros deben estar HECHOS los pasos obligatorios previos:\n' + falt.join('\n'));
    const det = await trx('alm_bajas_det').where({ nro }).orderBy('item');
    let tot = 0;
    for (const x of det) {
      const impo = await consumirPEPS(trx, u.usuario, {
        bod: h.cod_bod, cod: x.cod_item, cant: num(x.cantidad), fecha: today(), tipoMov: 'BAJA', doc: nro, refer: `${h.causal} - RA ${h.nro_ra}`, idLote: x.id_lote || '', permitirVencidos: true,
      });
      await trx('alm_bajas_det').where({ id: x.id }).update({ precio_unit: round(impo / num(x.cantidad), 4), total: round(impo, 2) });
      tot += round(impo, 2);
    }
    await trx('alm_bajas').where({ nro }).update({ total: round(tot, 2), estado: 'BAJA EJECUTADA' });
    await trx('alm_bajas_paso').where({ id: pb.id }).update({ estado: 'HECHO', referencia: `RA ${h.nro_ra}`, fecha: today() });
    await bitacoraUsuario(trx, u, 'BAJA EJECUTADA', nro, `${h.causal} - Bs ${tot.toFixed(2)} - RA ${h.nro_ra}`);
    return { nro, estado: 'BAJA EJECUTADA', total: round(tot, 2) };
  });
}

/** Concluye el expediente cuando todos los pasos obligatorios están HECHOS (archivo de la documentación). */
export async function concluirBaja(db: Db, u: Usuario, nro: string) {
  const h = await db('alm_bajas').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el expediente ${nro}.`);
  if (h.estado !== 'BAJA EJECUTADA') fail('Primero ejecute la baja.');
  const defs = await db('alm_pasos').where({ grupo: h.grupo });
  const pend = (await db('alm_bajas_paso').where({ nro })).filter((p: any) => defs.find((x: any) => x.orden === p.orden)?.obligatorio === 'SI' && p.estado !== 'HECHO' && p.estado !== 'NO APLICA');
  if (pend.length) fail('Quedan pasos obligatorios pendientes:\n' + pend.map((p: any) => '  - ' + p.paso).join('\n'));
  await db('alm_bajas').where({ nro }).update({ estado: 'CONCLUIDO' });
  await bitacoraUsuario(db, u, 'EXPEDIENTE DE BAJA CONCLUIDO', nro, '');
  return { nro, estado: 'CONCLUIDO' };
}

export async function anularBaja(db: Db, u: Usuario, nro: string, motivo: string) {
  if (!txt(motivo)) fail('La anulación requiere un motivo.');
  const h = await db('alm_bajas').where({ nro }).first();
  if (!h) throw new NotFound(`No existe el expediente ${nro}.`);
  if (h.estado !== 'EN TRÁMITE') fail('Solo se anulan expedientes EN TRÁMITE (la baja ejecutada no es reversible).');
  await db('alm_bajas').where({ nro }).update({ estado: 'ANULADO' });
  await bitacoraUsuario(db, u, 'ANULACIÓN DE EXPEDIENTE DE BAJA', nro, motivo);
  return { nro, estado: 'ANULADO' };
}

export async function obtenerBaja(db: Db, nro: string) {
  const h = await db('alm_bajas as j').leftJoin('alm_bodegas as b', 'b.cod', 'j.cod_bod').where('j.nro', nro).select('j.*', 'b.nombre as bodega').first();
  if (!h) throw new NotFound(`No existe el expediente ${nro}.`);
  return { ...h, items: await db('alm_bajas_det').where({ nro }).orderBy('item'), pasos: await db('alm_bajas_paso').where({ nro }).orderBy('orden') };
}
export async function listarBajas(db: Db) {
  return db('alm_bajas as j').leftJoin('alm_bodegas as b', 'b.cod', 'j.cod_bod').select('j.*', 'b.nombre as bodega').orderBy('j.nro', 'desc');
}
