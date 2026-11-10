/**
 * Importación inversa: trae del VSIAF (tablas DBF) los activos que SIGAA aún no tiene.
 * El VSIAF no guarda todo lo que usa SIGAA (fotos, marca, modelo, serie, ficha técnica): se importa lo que hay.
 */
import type { Db, Usuario } from '../core/context.js';
import { BusinessError, fail } from '../core/errors.js';
import { bitacora } from '../core/services.js';
import { nowIso, norm, today, txt } from '../core/util.js';
import { insertarActivos, type FilaActivo } from '../modules/activos/importar.js';
import { BdVsiaf, InstalacionError, detectarInstalacion, vsiafAbierto } from './instalacion.js';
import { leerConfigVsiaf } from './servicio.js';

const nk = (s: unknown) => norm(s).replace(/[^A-Z0-9]+/g, ' ').trim();
const str = (v: unknown) => String(v ?? '').replace(/¥/g, 'Ñ').trim();

export interface ParamsDesdeVsiaf {
  ruta?: string;
  /** Unidad administrativa del VSIAF a leer (vacío = todas). */
  unidad?: string;
  /** Edificio de SIGAA donde quedarán los activos, y ambiente (0 = sin asignar). */
  cod_edif?: number;
  cod_amb?: number;
  /** TODOS | APROBADOS */
  estado?: string;
  crearAuxiliares?: boolean;
  crearFuncionarios?: boolean;
  confirmar?: boolean;
}

interface ActivoVsiaf {
  codigo: string; unidad: string; codcont: number; grupo: string; codaux: number; auxiliar: string; descripcion: string; costo: number; fecha: string;
  oficina: string; responsable: string; cargo: string; ci: string; estado: string; apiEstado: number; observ: string;
}

function abrir(ruta: string): BdVsiaf {
  if (!ruta) fail('Indique la carpeta de instalación del VSIAF (por ejemplo C:\\vsiaf).');
  try { return new BdVsiaf(ruta); } catch (e) { if (e instanceof InstalacionError) throw new BusinessError(e.message); throw e; }
}

function leer(bd: BdVsiaf, unidad?: string): ActivoVsiaf[] {
  const ent = bd.entidad;
  const grupos = new Map(bd.grupos().map((g) => [g.codcont, g.nombre]));
  const estados = new Map(bd.estados().map((e) => [e.codigo, e.nombre]));
  const aux = new Map<string, string>();
  for (const r of bd.tabla('AUXILIAR').registros()) if (str(r.valores.ENTIDAD) === ent) aux.set(`${str(r.valores.UNIDAD)}|${Number(r.valores.CODCONT)}|${Number(r.valores.CODAUX)}`, str(r.valores.NOMAUX));
  const ofi = new Map<string, string>();
  if (bd.existeTabla('OFICINA')) for (const r of bd.tabla('OFICINA').registros()) if (str(r.valores.ENTIDAD) === ent) ofi.set(`${str(r.valores.UNIDAD)}|${Number(r.valores.CODOFIC)}`, str(r.valores.NOMOFIC));
  const resp = new Map<string, { nombre: string; cargo: string; ci: string }>();
  if (bd.existeTabla('RESP')) for (const r of bd.tabla('RESP').registros()) if (str(r.valores.ENTIDAD) === ent) resp.set(`${str(r.valores.UNIDAD)}|${Number(r.valores.CODOFIC)}|${Number(r.valores.CODRESP)}`, { nombre: str(r.valores.NOMRESP), cargo: str(r.valores.CARGO), ci: str(r.valores.CI) });
  const out: ActivoVsiaf[] = [];
  for (const r of bd.tabla('ACTUAL').registros()) {
    const v = r.valores;
    if (str(v.ENTIDAD) !== ent) continue;
    const u = str(v.UNIDAD);
    if (unidad && u !== unidad) continue;
    const cc = Number(v.CODCONT), ca = Number(v.CODAUX), co = Number(v.CODOFIC);
    const rs = resp.get(`${u}|${co}|${Number(v.CODRESP)}`);
    const d = Number(v.DIA), m = Number(v.MES), a = Number(v.ANO);
    const fecha = a > 1900 && m >= 1 && m <= 12 && d >= 1 && d <= 31 ? `${a}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}` : today();
    out.push({
      codigo: str(v.CODIGO).toUpperCase(), unidad: u, codcont: cc, grupo: grupos.get(cc) ?? `Grupo ${cc}`, codaux: ca, auxiliar: aux.get(`${u}|${cc}|${ca}`) ?? `AUXILIAR ${ca}`, descripcion: str(v.DESCRIP), costo: Number(v.COSTO) || 0, fecha,
      oficina: ofi.get(`${u}|${co}`) ?? '', responsable: rs?.nombre ?? '', cargo: rs?.cargo ?? '', ci: rs?.ci ?? '', estado: estados.get(Number(v.CODESTADO)) ?? '', apiEstado: Number(v.API_ESTADO), observ: str(v.OBSERV),
    });
  }
  return out;
}

export async function infoDesdeVsiaf(db: Db, ruta?: string) {
  const conf = await leerConfigVsiaf(db);
  const r = (ruta ?? conf.ruta) || detectarInstalacion() || '';
  const bd = abrir(r);
  return { ruta: bd.carpeta, entidad: bd.entidadNombre || bd.entidad, unidades: bd.unidades(), vsiafAbierto: vsiafAbierto() };
}

async function preparar(db: Db, p: ParamsDesdeVsiaf) {
  const conf = await leerConfigVsiaf(db);
  const bd = abrir((p.ruta ?? conf.ruta) || detectarInstalacion() || '');
  let todos = leer(bd, p.unidad || undefined);
  if ((p.estado ?? 'TODOS') === 'APROBADOS') todos = todos.filter((a) => a.apiEstado === 3);
  const cuentas = await db('af_cuentas');
  const auxs = await db('af_auxiliares');
  const estadosSigaa = await db('af_estados');
  const existentes = new Set((await db('af_activos').select('codigo')).map((x: any) => String(x.codigo).toUpperCase()));
  const funcs = await db('core_funcionarios');
  const problemas: { codigo: string; mensaje: string }[] = [];
  const yaExisten: string[] = [];
  const listos: { a: ActivoVsiaf; cta: any; aux?: any }[] = [];
  const sinCuenta = new Map<number, string>();
  const auxNuevos = new Map<string, { id_cta: number; nombre: string }>();
  const funcNuevos = new Map<string, { nombre: string; cargo: string; ci: string }>();
  for (const a of todos) {
    if (!a.codigo) continue;
    if (existentes.has(a.codigo)) { yaExisten.push(a.codigo); continue; }
    const cta = cuentas.find((c: any) => Number(c.cod_vsiaf) === a.codcont);
    if (!cta) { sinCuenta.set(a.codcont, a.grupo); continue; }
    let aux = auxs.find((x: any) => x.id_cta === cta.id_cta && nk(x.auxiliar) === nk(a.auxiliar));
    if (!aux) {
      if (p.crearAuxiliares === false) { problemas.push({ codigo: a.codigo, mensaje: `El auxiliar «${a.auxiliar}» no existe en la cuenta ${cta.id_cta} - ${cta.cuenta}.` }); continue; }
      auxNuevos.set(`${cta.id_cta}|${nk(a.auxiliar)}`, { id_cta: cta.id_cta, nombre: a.auxiliar });
    }
    if (a.responsable && !funcs.some((f: any) => nk(f.nombre) === nk(a.responsable))) {
      if (p.crearFuncionarios === false) { problemas.push({ codigo: a.codigo, mensaje: `El responsable «${a.responsable}» no está en Catálogos → Funcionarios.` }); continue; }
      funcNuevos.set(nk(a.responsable), { nombre: a.responsable, cargo: a.cargo, ci: a.ci });
    }
    if (!a.descripcion) { problemas.push({ codigo: a.codigo, mensaje: 'No tiene descripción en el VSIAF.' }); continue; }
    listos.push({ a, cta, aux });
  }
  for (const [cc, g] of sinCuenta) problemas.push({ codigo: '', mensaje: `El grupo contable ${cc} (${g}) del VSIAF no tiene cuenta equivalente en SIGAA: complete «Cód. VSIAF» de la cuenta en Catálogos → Cuentas contables. Sus activos no se importan.` });
  return { bd, todos, listos, yaExisten, problemas, auxNuevos, funcNuevos, estadosSigaa, funcs, auxs };
}

export async function previsualizarDesdeVsiaf(db: Db, p: ParamsDesdeVsiaf) {
  const r = await preparar(db, p);
  const porGrupo = new Map<string, { grupo: string; cantidad: number; costo: number }>();
  for (const { a } of r.listos) { const g = porGrupo.get(a.grupo) ?? { grupo: a.grupo, cantidad: 0, costo: 0 }; g.cantidad++; g.costo += a.costo; porGrupo.set(a.grupo, g); }
  return {
    leidos: r.todos.length, nuevos: r.listos.length, yaExisten: r.yaExisten.length, auxiliaresNuevos: r.auxNuevos.size, funcionariosNuevos: r.funcNuevos.size,
    problemas: r.problemas, porGrupo: [...porGrupo.values()].map((g) => ({ ...g, costo: Math.round(g.costo * 100) / 100 })),
    muestra: r.listos.slice(0, 200).map(({ a }) => ({ codigo: a.codigo, descripcion: a.descripcion, grupo: a.grupo, auxiliar: a.auxiliar, oficina: a.oficina, responsable: a.responsable, fecha: a.fecha, costo: a.costo, aprobado: a.apiEstado === 3 })),
  };
}

export async function traerDesdeVsiaf(db: Db, u: Usuario, p: ParamsDesdeVsiaf) {
  if (!p.confirmar) fail('Confirme la importación.');
  const ed = p.cod_edif ? await db('af_edificios').where({ cod_edif: p.cod_edif }).first() : null;
  if (!ed) fail('Elija el edificio de SIGAA donde quedarán los activos importados.');
  const r = await preparar(db, p);
  if (!r.listos.length) fail('No hay activos nuevos para traer del VSIAF.');
  const ambDefecto = Number(p.cod_amb ?? 0);
  const ambientes = await db('af_ambientes').where({ cod_edif: ed.cod_edif });
  if (!ambientes.some((a: any) => a.cod_amb === ambDefecto)) fail('El ambiente elegido no pertenece al edificio.');
  return db.transaction(async (trx) => {
    for (const f of r.funcNuevos.values()) await trx('core_funcionarios').insert({ nombre: f.nombre.slice(0, 140), ci: f.ci || null, cargo: f.cargo || null, estado: 'ACTIVO' });
    const funcs = await trx('core_funcionarios');
    for (const x of r.auxNuevos.values()) {
      const max = await trx('af_auxiliares').where({ id_cta: x.id_cta }).max({ m: 'id_aux' }).first();
      const id = Number((max as any)?.m ?? 0) + 1;
      if (id > 999) fail(`La cuenta ${x.id_cta} ya no admite más auxiliares (máximo 999).`);
      await trx('af_auxiliares').insert({ id_cta: x.id_cta, id_aux: id, auxiliar: x.nombre.slice(0, 160) });
    }
    const auxs = await trx('af_auxiliares');
    const filas: FilaActivo[] = r.listos.map(({ a, cta }, i) => {
      const aux = auxs.find((x: any) => x.id_cta === cta.id_cta && nk(x.auxiliar) === nk(a.auxiliar))!;
      const est = r.estadosSigaa.find((e: any) => nk(e.estado) === nk(a.estado))?.estado ?? 'Bueno';
      const f = a.responsable ? funcs.find((x: any) => nk(x.nombre) === nk(a.responsable)) : undefined;
      const amb = ambientes.find((x: any) => a.oficina && nk(x.ambiente) === nk(a.oficina))?.cod_amb ?? ambDefecto;
      const obs = [`Importado del VSIAF (unidad ${a.unidad}, ${a.apiEstado === 3 ? 'APROBADO' : 'ELABORADO'})`, a.oficina && `Oficina: ${a.oficina}`, `Grupo: ${a.grupo}`, a.observ].filter(Boolean).join(' · ');
      return { fila: i + 1, codigo: a.codigo, descripcion: a.descripcion.slice(0, 240), id_cta: cta.id_cta, id_aux: aux.id_aux, auxiliar: aux.auxiliar, cod_edif: ed.cod_edif, cod_amb: amb, estado: est, valor: a.costo, fecha_ingreso: a.fecha, observaciones: obs, funcionario: f?.nombre, ci: f?.ci ?? a.ci };
    });
    const creados = await insertarActivos(trx, u, filas, 'IMPORT. VSIAF');
    // Quedan registrados como «ya enviados»: no se vuelven a mandar al VSIAF (ya están allí).
    const lr: any = await trx('af_vsiaf_lotes').insert({ fecha: nowIso(), usuario: u.usuario, destino: r.bd.carpeta, unidad: p.unidad ? p.unidad.slice(0, 5) : null, estado_registro: null, resultado: 'TRAÍDO', mensaje: `Activos traídos del VSIAF a SIGAA (${creados.length})`, resumen: JSON.stringify({ resumen: { activos: creados.length, transferencias: 0, bajas: 0 } }) }).returning('id');
    const lote = Number(Array.isArray(lr) ? (typeof lr[0] === 'object' ? lr[0].id : lr[0]) : lr);
    for (const [i, c] of creados.entries()) {
      const a = r.listos[i].a;
      await trx('af_vsiaf_envios').insert({ lote, tipo: 'ACTIVO', codigo: c.codigo, unidad: a.unidad, codigo_vsiaf: a.codigo, oficina: a.oficina || null, responsable: a.responsable || null, fecha: nowIso(), usuario: u.usuario });
    }
    await bitacora(trx, u, 'ACTIVOS FIJOS', 'IMPORTACIÓN DESDE VSIAF', `LOTE-${lote}`, `${creados.length} activo(s), ${r.auxNuevos.size} auxiliar(es) y ${r.funcNuevos.size} funcionario(s) nuevos`);
    return { lote, importados: creados.length, yaExistian: r.yaExisten.length, auxiliaresNuevos: r.auxNuevos.size, funcionariosNuevos: r.funcNuevos.size, problemas: r.problemas };
  });
}
void txt;
