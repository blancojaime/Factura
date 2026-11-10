/**
 * Adaptador SIGAA → VSIAF: lee los activos y movimientos de SIGAA y produce las filas normalizadas (`Libro`) que entiende el
 * motor de importación. No escribe en el VSIAF ni inventa datos: lo que falta queda en blanco (el motor lo rechaza) y se informa
 * en `faltantes` para que el usuario lo complete (equivalencias o campos de SIGAA).
 *
 * Reglas aprobadas (decisiones D1–D8):
 *  - Se envía el responsable/oficina **actuales** de cada activo (no se reproduce todo el historial).
 *  - Un activo EN ALMACÉN va a la oficina «ALMACÉN» con el encargado de almacenes de Configuración como responsable.
 *  - Oficina = «EDIFICIO / AMBIENTE» (≤ 65). Una sola unidad administrativa por defecto (equivalencias por sector si luego se separa).
 *  - Marca, modelo, serie, color e ingreso van en OBSERV (memo).
 *  - Un activo ya enviado no se vuelve a enviar: los cambios posteriores viajan como TRANSFERENCIA y la baja como BAJA.
 */
import type { Db } from '../core/context.js';
import { cfg } from '../core/services.js';
import type { Fila, Libro } from './importador.js';
import { norm } from './instalacion.js';

// ───────────── equivalencias ─────────────
export const TIPOS_EQUIV = ['grupo', 'estado', 'org_fin', 'unidad', 'motivo_baja', 'oficina', 'resp_nombre', 'resp_cargo', 'auxiliar'] as const;
export type TipoEquiv = (typeof TIPOS_EQUIV)[number];
export type Equivalencias = Record<TipoEquiv, Map<string, string>>;

/** Estados físicos de SIGAA → los 3 del VSIAF (editable). */
export const ESTADO_POR_DEFECTO: Record<string, string> = { Nuevo: 'Bueno', Bueno: 'Bueno', Regular: 'Regular', Malo: 'Malo', 'Pésimo': 'Malo' };

export async function cargarEquivalencias(db: Db): Promise<Equivalencias> {
  const eq = Object.fromEntries(TIPOS_EQUIV.map((t) => [t, new Map<string, string>()])) as Equivalencias;
  for (const r of await db('af_vsiaf_equiv')) if ((TIPOS_EQUIV as readonly string[]).includes(r.tipo)) eq[r.tipo as TipoEquiv].set(r.clave, r.valor);
  return eq;
}

// ───────────── tipos de salida ─────────────
export interface Faltante { tipo: string; clave: string; detalle: string; sugerencia?: string }
export interface Omitido { codigo: string; motivo: string }
/** Qué se envió de cada fila (para registrar el envío y para mostrar mensajes con el código de SIGAA). */
export interface InfoFila { tipo: 'ACTIVO' | 'TRANSFERENCIA' | 'BAJA' | 'OFICINA' | 'RESPONSABLE' | 'AUXILIAR'; codigo: string; unidad: string; codigoVsiaf?: string; oficina?: string; responsable?: string }
export interface SalidaAdaptador {
  libro: Libro;
  info: Map<string, InfoFila>;
  omitidos: Omitido[];
  faltantes: Faltante[];
  resumen: { activos: number; transferencias: number; bajas: number; oficinas: number; responsables: number; auxiliares: number };
}

export interface ParamsLote {
  /** Activos de SIGAA a enviar; vacío = todos los pendientes según `filtros`. */
  codigos?: string[];
  filtros?: { desde?: string; hasta?: string; id_cta?: number; cod_edif?: number; texto?: string; situacion?: string };
  /** Activos EN ALMACÉN (D3): se envían a la oficina «ALMACÉN». Por defecto sí. */
  incluirAlmacen?: boolean;
  /** Unidad administrativa del VSIAF por defecto. */
  unidad?: string;
  /** Estado de las altas (D4): ELABORADO por defecto. */
  estadoRegistro?: 'ELABORADO' | 'APROBADO';
  /** Enviar también transferencias y bajas de activos ya enviados. Por defecto sí. */
  movimientos?: boolean;
}

/** Lo que ya existe en el VSIAF (para no proponer maestros repetidos). Opcional. */
export interface ExistenteVsiaf {
  oficina?: (unidad: string, nombre: string) => boolean;
  responsable?: (unidad: string, oficina: string, nombre: string) => boolean;
  auxiliar?: (unidad: string, grupo: number, nombre: string) => boolean;
}

/** Clave de equivalencia para los ingresos sin fuente de financiamiento. */
export const SIN_FUENTE = '(sin fuente de financiamiento)';
const ALMACEN = 'ALMACÉN';
const MAX_OFICINA = 65;

const k = (...p: (string | number)[]) => p.join('\u0001');
const t = (v: unknown) => (v === null || v === undefined ? '' : String(v).trim());

export async function armarLote(db: Db, p: ParamsLote, existente: ExistenteVsiaf = {}): Promise<SalidaAdaptador> {
  const eq = await cargarEquivalencias(db);
  const unidadDefecto = t(p.unidad) || t(await cfg(db, 'VSIAF_UNIDAD', ''));
  const nombreAlm = t(await cfg(db, 'NombreALM', ''));
  const cargoAlm = t(await cfg(db, 'CargoALM', ''));
  const incluirAlmacen = p.incluirAlmacen !== false;
  const estadoRegistro = p.estadoRegistro ?? 'ELABORADO';

  const cuentas = new Map<number, any>((await db('af_cuentas')).map((c: any) => [c.id_cta, c]));
  const auxs = new Map<string, any>((await db('af_auxiliares')).map((a: any) => [k(a.id_cta, a.id_aux), a]));
  const edifs = new Map<number, any>((await db('af_edificios')).map((e: any) => [e.cod_edif, e]));
  const ambs = new Map<string, any>((await db('af_ambientes')).map((a: any) => [k(a.cod_edif, a.cod_amb), a]));
  const funcs = new Map<string, any>((await db('core_funcionarios')).map((f: any) => [norm(f.nombre), f]));
  const ingresos = new Map<string, any>((await db('af_ingresos')).map((i: any) => [i.nro, i]));
  const envios = await db('af_vsiaf_envios').orderBy('id');
  const ultimo = new Map<string, any>(); // último estado enviado de cada activo (ACTIVO o TRANSFERENCIA)
  const enviado = new Set<string>();
  const baja = new Set<string>();
  for (const e of envios) {
    if (e.tipo === 'ACTIVO') { enviado.add(e.codigo); ultimo.set(e.codigo, e); }
    else if (e.tipo === 'TRANSFERENCIA') ultimo.set(e.codigo, e);
    else if (e.tipo === 'BAJA') baja.add(e.codigo);
  }

  const out: SalidaAdaptador = { libro: {}, info: new Map(), omitidos: [], faltantes: [], resumen: { activos: 0, transferencias: 0, bajas: 0, oficinas: 0, responsables: 0, auxiliares: 0 } };
  const faltante = (f: Faltante) => { if (!out.faltantes.some((x) => x.tipo === f.tipo && x.clave === f.clave)) out.faltantes.push(f); };

  // ---- cálculo de cada concepto VSIAF a partir de SIGAA ----
  const unidadDe = (cod_edif: number): string => {
    const sector = t(edifs.get(cod_edif)?.sector);
    return eq.unidad.get(sector) ?? unidadDefecto;
  };
  const grupoDe = (id_cta: number): string => eq.grupo.get(String(id_cta)) ?? (cuentas.get(id_cta)?.cod_vsiaf ? String(cuentas.get(id_cta).cod_vsiaf) : '');
  const oficinaDe = (a: any, almacen: boolean): string => {
    if (almacen) return ALMACEN;
    const ed = a.edif_actual ?? a.cod_edif;
    const am = a.amb_actual ?? a.cod_amb;
    const e = t(edifs.get(ed)?.edificio);
    const amb = am ? t(ambs.get(k(ed, am))?.ambiente) : '';
    const nat = amb ? `${e} / ${amb}` : e;
    return eq.oficina.get(nat) ?? nat;
  };
  const responsableDe = (a: any, almacen: boolean): { nombre: string; cargo: string; ci: string; origen: string } => {
    if (almacen) {
      const nombre = eq.resp_nombre.get(nombreAlm) ?? nombreAlm;
      return { nombre, cargo: eq.resp_cargo.get(nombreAlm) ?? cargoAlm, ci: '', origen: nombreAlm };
    }
    const f = funcs.get(norm(a.funcionario));
    const nom = t(a.funcionario);
    return { nombre: eq.resp_nombre.get(nom) ?? nom, cargo: eq.resp_cargo.get(nom) ?? t(f?.cargo), ci: t(f?.ci ?? a.ci_func), origen: nom };
  };
  const enAlmacen = (a: any) => a.situacion === 'EN ALMACEN';

  // ---- maestros a crear (se deduplican y se omiten los que ya existen en el VSIAF) ----
  const ofis = new Map<string, Fila>();
  const resps = new Map<string, Fila>();
  const auxis = new Map<string, Fila>();
  const maestros = (unidad: string, oficina: string, resp: { nombre: string; cargo: string; ci: string }, grupo: string, nomAux: string, ref: string) => {
    if (oficina && !existente.oficina?.(unidad, oficina) && !ofis.has(k(unidad, norm(oficina)))) {
      ofis.set(k(unidad, norm(oficina)), { ref: `OFICINA:${oficina}`, datos: { unidad, oficina } });
      out.info.set(`OFICINA:${oficina}`, { tipo: 'OFICINA', codigo: oficina, unidad });
    }
    if (resp.nombre && oficina && !existente.responsable?.(unidad, oficina, resp.nombre) && !resps.has(k(unidad, norm(oficina), norm(resp.nombre)))) {
      resps.set(k(unidad, norm(oficina), norm(resp.nombre)), { ref: `RESPONSABLE:${oficina}|${resp.nombre}`, datos: { unidad, oficina, responsable: resp.nombre, cargo: resp.cargo, ci: resp.ci } });
      out.info.set(`RESPONSABLE:${oficina}|${resp.nombre}`, { tipo: 'RESPONSABLE', codigo: resp.nombre, unidad });
    }
    if (grupo && nomAux && !existente.auxiliar?.(unidad, Number(grupo), nomAux) && !auxis.has(k(unidad, grupo, norm(nomAux)))) {
      auxis.set(k(unidad, grupo, norm(nomAux)), { ref: `AUXILIAR:${grupo}|${nomAux}`, datos: { unidad, grupo_contable: grupo, auxiliar: nomAux } });
      out.info.set(`AUXILIAR:${grupo}|${nomAux}`, { tipo: 'AUXILIAR', codigo: nomAux, unidad });
    }
    void ref;
  };

  // ───────────── 1. ALTAS ─────────────
  const q = db('af_activos').orderBy('codigo');
  if (p.codigos?.length) q.whereIn('codigo', p.codigos);
  const f = p.filtros ?? {};
  if (f.desde) q.where('fecha_ingreso', '>=', f.desde);
  if (f.hasta) q.where('fecha_ingreso', '<=', f.hasta);
  if (f.id_cta) q.where('id_cta', f.id_cta);
  if (f.cod_edif) q.where('cod_edif', f.cod_edif);
  if (f.situacion) q.where('situacion', f.situacion);
  if (f.texto) q.where((b) => b.where('codigo', 'like', `%${f.texto}%`).orWhere('descripcion', 'like', `%${f.texto}%`));
  const candidatos: any[] = await q;
  const altas: Fila[] = [];
  for (const a of candidatos) {
    if (enviado.has(a.codigo)) { if (p.codigos?.length) out.omitidos.push({ codigo: a.codigo, motivo: 'Ya fue enviado al VSIAF.' }); continue; }
    if (a.situacion === 'BAJA') { out.omitidos.push({ codigo: a.codigo, motivo: 'Está dado de baja en SIGAA y nunca se envió: no se registra en el VSIAF.' }); continue; }
    const alm = enAlmacen(a);
    if (alm && !incluirAlmacen) { out.omitidos.push({ codigo: a.codigo, motivo: 'Está en almacén (no incluido en este envío).' }); continue; }
    const unidad = unidadDe(a.cod_edif);
    const grupo = grupoDe(a.id_cta);
    const nomAux = t(eq.auxiliar.get(`${a.id_cta}:${a.id_aux}`) ?? auxs.get(k(a.id_cta, a.id_aux))?.auxiliar ?? a.auxiliar);
    const oficina = oficinaDe(a, alm);
    const resp = responsableDe(a, alm);
    const ing = a.nro_ingreso ? ingresos.get(a.nro_ingreso) : null;
    const fuente = t(ing?.fuente_fin);
    const org = t(ing?.org_fin) || t(eq.org_fin.get(fuente || SIN_FUENTE));
    if (!unidad) faltante({ tipo: 'unidad', clave: t(edifs.get(a.cod_edif)?.sector) || '(sin sector)', detalle: 'Falta la unidad administrativa del VSIAF para este sector.' });
    if (!grupo) faltante({ tipo: 'grupo', clave: String(a.id_cta), detalle: `La cuenta «${t(cuentas.get(a.id_cta)?.cuenta)}» no tiene grupo contable del VSIAF.` });
    if (!org) {
      const sug = /\b(\d{3})\b/.exec(fuente)?.[1];
      faltante({ tipo: 'org_fin', clave: fuente || SIN_FUENTE, detalle: `Falta el organismo financiador (ingreso ${a.nro_ingreso ?? 'directo'}).`, sugerencia: sug });
    }
    if (!resp.nombre) faltante({ tipo: 'responsable', clave: a.codigo, detalle: alm ? 'Configure el Encargado de Almacenes (NombreALM) en Administración.' : 'El activo no tiene funcionario asignado.' });
    const estado = eq.estado.get(t(a.estado)) ?? ESTADO_POR_DEFECTO[t(a.estado)] ?? t(a.estado);
    const obs = [
      t(a.marca) && `Marca: ${t(a.marca)}`, t(a.modelo) && `Modelo: ${t(a.modelo)}`, t(a.serie) && `Serie: ${t(a.serie)}`, t(a.color) && `Color: ${t(a.color)}`,
      a.nro_ingreso && `Ingreso ${a.nro_ingreso}`, t(a.observaciones),
    ].filter(Boolean).join('; ');
    maestros(unidad, oficina, resp, grupo, nomAux, a.codigo);
    const ref = `ACTIVO:${a.codigo}`;
    altas.push({
      ref,
      datos: {
        unidad, codigo: a.codigo, descripcion: t(a.descripcion) || nomAux, grupo_contable: grupo, auxiliar: nomAux, oficina, responsable: resp.nombre,
        estado_bien: estado, fecha_incorporacion: t(a.fecha_ingreso) || t(a.fecha_codif), costo_inicial: a.valor, organismo_financiador: org, observaciones: obs, estado_registro: estadoRegistro,
      },
    });
    out.info.set(ref, { tipo: 'ACTIVO', codigo: a.codigo, unidad, codigoVsiaf: a.codigo.toUpperCase(), oficina, responsable: resp.nombre });
  }

  // ───────────── 2. TRANSFERENCIAS y 3. BAJAS (activos ya enviados) ─────────────
  const transfer: Fila[] = [];
  const bajas: Fila[] = [];
  if (p.movimientos !== false && enviado.size) {
    const sent: any[] = await db('af_activos').whereIn('codigo', [...enviado]).orderBy('codigo');
    for (const a of sent) {
      const prev = ultimo.get(a.codigo);
      if (a.situacion === 'BAJA') {
        if (baja.has(a.codigo)) continue;
        const mov = await db('af_movimientos').where({ codigo: a.codigo, tipo: 'BAJA' }).orderBy('id', 'desc').first();
        const mot = mov?.motivo_cod ?? eq.motivo_baja.get(t(mov?.detalle).split(' | ')[0]) ?? '';
        const ref = `BAJA:${a.codigo}`;
        if (!mov?.resolucion) faltante({ tipo: 'baja_resolucion', clave: a.codigo, detalle: `La baja de ${a.codigo} no tiene resolución / disposición de respaldo.` });
        if (!mot) faltante({ tipo: 'baja_motivo', clave: a.codigo, detalle: `La baja de ${a.codigo} no tiene motivo del VSIAF (1 a 9).` });
        bajas.push({ ref, datos: { unidad: prev.unidad, codigo: prev.codigo_vsiaf, fecha_baja: mov?.fecha, motivo_baja: mot, disposicion_respaldo: t(mov?.resolucion), observaciones: t(mov?.detalle).split(' | ')[0] } });
        out.info.set(ref, { tipo: 'BAJA', codigo: a.codigo, unidad: prev.unidad, codigoVsiaf: prev.codigo_vsiaf });
        continue;
      }
      const alm = enAlmacen(a);
      if (alm && !incluirAlmacen && !prev) continue;
      const oficina = oficinaDe(a, alm);
      const resp = responsableDe(a, alm);
      if (norm(oficina) === norm(prev.oficina) && norm(resp.nombre) === norm(prev.responsable)) continue; // sin cambios desde el último envío
      const unidad = prev.unidad;
      maestros(unidad, oficina, resp, '', '', a.codigo);
      const ref = `TRANSFERENCIA:${a.codigo}`;
      transfer.push({ ref, datos: { unidad_origen: prev.unidad, codigo: prev.codigo_vsiaf, unidad_destino: unidad, oficina_destino: oficina, responsable_destino: resp.nombre } });
      out.info.set(ref, { tipo: 'TRANSFERENCIA', codigo: a.codigo, unidad, codigoVsiaf: prev.codigo_vsiaf, oficina, responsable: resp.nombre });
    }
  }

  out.libro = {
    OFICINAS: [...ofis.values()], RESPONSABLES: [...resps.values()], AUXILIARES: [...auxis.values()], ACTIVOS: altas, TRANSFERENCIAS: transfer, BAJAS: bajas,
  };
  out.resumen = { activos: altas.length, transferencias: transfer.length, bajas: bajas.length, oficinas: ofis.size, responsables: resps.size, auxiliares: auxis.size };
  return out;
}

// ───────────── mensajes comprensibles ─────────────
export const ETIQUETA_COLUMNA: Record<string, string> = {
  unidad: 'Unidad administrativa', codigo: 'Código', descripcion: 'Descripción', grupo_contable: 'Grupo contable', auxiliar: 'Auxiliar', oficina: 'Oficina', responsable: 'Responsable',
  estado_bien: 'Estado del bien', fecha_incorporacion: 'Fecha de ingreso', costo_inicial: 'Valor (costo)', vida_util: 'Vida útil', organismo_financiador: 'Organismo financiador',
  observaciones: 'Observaciones', estado_registro: 'Estado de registro', fecha_baja: 'Fecha de baja', motivo_baja: 'Motivo de baja (VSIAF)', disposicion_respaldo: 'Resolución / disposición',
  oficina_destino: 'Oficina destino', responsable_destino: 'Responsable destino', unidad_destino: 'Unidad destino', cargo: 'Cargo', ci: 'CI',
};

/** Reescribe los mensajes del motor (que hablan de las hojas del libro Excel) con el lenguaje de SIGAA. */
export function amigable(msg: string): string {
  return msg
    .replace(/ \((créel[oa]|cree) en la hoja [A-Z]+\)/g, '')
    .replace(/\(use el código 1-40 o el nombre de la hoja CATALOGOS\)/g, '(revise el grupo contable de la cuenta en las equivalencias)')
    .replace(/\(códigos 1-9, ver hoja CATALOGOS\)/g, '(elija un motivo del 1 al 9 al dar de baja)')
    .replace(/Falta la unidad: complete la columna o elija una unidad por defecto en el importador\./g, 'Falta la unidad administrativa del VSIAF: elíjala en «Destino» o defínala en las equivalencias.')
    .replace(/ni en la hoja UNIDADES/g, 'y SIGAA no crea unidades: créela primero en el VSIAF')
    .replace(/El importador no puede saltarse/g, 'SIGAA no puede saltarse')
    .replace(/Este equipo no tiene/g, 'Esta PC no tiene')
    .replace(/en este libro/g, 'en este envío')
    .replace(/ de este libro/g, ' de este envío')
    .replace(/Hay (\d+) error\(es\)\. Corríjalos o active «importar solo filas válidas»\./g, 'Hay $1 error(es). Corríjalos o elija «importar solo las filas válidas».');
}
