/**
 * Núcleo del módulo: valida las filas, arma el plan y lo escribe en las tablas DBF del VSIAF reproduciendo lo que hacen
 * sus pantallas (Activos Fijos, Revalúo técnico, Transferencia, Dar de baja, Oficinas, Responsables, Auxiliares).
 *
 * Es **independiente de SIGAA**: recibe filas normalizadas (`Libro`) con los mismos nombres de columna del libro Excel del
 * «Importador Excel → VSIAF», y devuelve un `Resultado` con incidencias, operaciones planificadas y cálculos. Así se prueba sin
 * pantallas y sirve igual para la importación directa y para la exportación a Excel.
 */
import fs from 'node:fs';
import { comoFecha, comoNumero, comoTexto, vacio } from './coercion.js';
import { DbfError, DbfTabla } from './dbf.js';
import { Fecha, dmy, hoy as hoyIso, partes, sumarDias } from './fecha.js';
import { BdVsiaf, incorporacionEspecialHabilitada, norm, vsiafAbierto } from './instalacion.js';
import { hacerRespaldo } from './respaldo.js';
import { UfvFaltante, TablaUfv } from './ufv.js';
import { valuar, Valuacion } from './calc.js';

export const ERROR = 'ERROR';
export const AVISO = 'AVISO';
export const INFO = 'INFO';
export type Nivel = typeof ERROR | typeof AVISO | typeof INFO;
/** Texto que el VSIAF guarda en OBSERV al dar de baja. */
export const DADO_DE_BAJA = 'DADO DE BAJA';

export type Hoja = 'UNIDADES' | 'OFICINAS' | 'RESPONSABLES' | 'AUXILIARES' | 'ACTIVOS' | 'REVALUOS' | 'TRANSFERENCIAS' | 'BAJAS';
export const ORDEN_HOJAS: Hoja[] = ['UNIDADES', 'OFICINAS', 'RESPONSABLES', 'AUXILIARES', 'ACTIVOS', 'REVALUOS', 'TRANSFERENCIAS', 'BAJAS'];

/** Una fila de entrada: `ref` identifica la fila para el usuario (n.º de fila de Excel o id de SIGAA). */
export interface Fila { ref: number | string; datos: Record<string, unknown> }
export type Libro = Partial<Record<Hoja, Fila[]>>;
/** Problemas de estructura del libro (hojas/columnas), si el origen es un Excel. */
export interface LibroConProblemas { libro: Libro; problemas?: string[] }

export interface Incidencia { hoja: string; ref: number | string; columna: string; nivel: Nivel; mensaje: string }

export interface Opciones {
  unidadPorDefecto?: string;
  usuario?: string;
  fechaCalculo?: Fecha;
  /** Estado de los activos si la fila no lo indica. */
  estadoPorDefecto?: 'ELABORADO' | 'APROBADO';
  /** Importar solo las filas válidas aunque haya errores. */
  soloValidas?: boolean;
  respaldar?: boolean;
  /** null/undefined = lo que indique el registro de Windows (llave de la DGCF). */
  permitirIncorporacionEspecial?: boolean | null;
  hoy?: Fecha;
  /** Solo pruebas: no comprobar si vsiaf.exe está abierto. */
  omitirProceso?: boolean;
  /** Solo pruebas: simular un fallo a mitad de la escritura. */
  fallaSimulada?: (donde: string) => void;
}

export interface Resultado {
  incidencias: Incidencia[];
  conteos: Record<string, number>;
  omitidas: Record<string, number>;
  calculos: Record<string, Record<string, unknown>[]>;
  aplicado: boolean;
  rutaRespaldo: string | null;
  notas: string[];
}
export const errores = (r: Resultado) => r.incidencias.filter((i) => i.nivel === ERROR).length;
export const avisos = (r: Resultado) => r.incidencias.filter((i) => i.nivel === AVISO).length;

export class ImportacionAbortada extends Error {}

type Reg = Record<string, any>;
type Op = { tipo: 'unidad' | 'oficina' | 'resp' | 'aux' | 'actual_new' | 'reval' | 'trasfe' | 'baja'; d: any; ref: number | string };

// ───────────── contexto de fila ─────────────
class Ctx {
  ok = true;
  constructor(private res: Resultado, readonly hoja: string, readonly fila: Fila) {}
  err(col: string, msg: string) { this.ok = false; this.res.incidencias.push({ hoja: this.hoja, ref: this.fila.ref, columna: col, nivel: ERROR, mensaje: msg }); }
  warn(col: string, msg: string) { this.res.incidencias.push({ hoja: this.hoja, ref: this.fila.ref, columna: col, nivel: AVISO, mensaje: msg }); }
  raw(col: string): unknown { return this.fila.datos[col]; }
  text(col: string, max?: number, req = false): string {
    const v = comoTexto(this.raw(col));
    if (req && !v) this.err(col, 'Dato obligatorio vacío.');
    if (max && [...v].length > max) this.err(col, `Excede el largo máximo de ${max} caracteres (${[...v].length}).`);
    return v;
  }
  number(col: string, req = false): number | null {
    let v: number | null = null;
    try { v = comoNumero(this.raw(col)); } catch (e) { this.err(col, (e as Error).message); return null; }
    if (v === null && req) this.err(col, 'Dato obligatorio vacío.');
    return v;
  }
  date(col: string, req = false): Fecha | null {
    let v: Fecha | null = null;
    try { v = comoFecha(this.raw(col)); } catch (e) { this.err(col, (e as Error).message); return null; }
    if (v === null && req) this.err(col, 'Dato obligatorio vacío.');
    return v;
  }
  yesno(col: string): boolean {
    const v = norm(comoTexto(this.raw(col)));
    if (['', 'NO', 'N', '0', 'FALSO', 'FALSE'].includes(v)) return false;
    if (['SI', 'S', '1', 'VERDADERO', 'TRUE', 'X'].includes(v)) return true;
    this.err(col, `Valor «${v}» no válido: use SI o NO.`);
    return false;
  }
}

const k2 = (a: string | number, b: string | number) => `${a}\u0001${b}`;
const k3 = (a: string | number, b: string | number, c: string | number) => `${a}\u0001${b}\u0001${c}`;

// ───────────── estado virtual de la BD ─────────────
class Estado {
  entidad: string;
  unidades = new Map<string, Reg>();
  oficinas = new Map<string, Reg>(); // unidad|cod
  ofPorNombre = new Map<string, number>(); // unidad|nombre
  resp = new Map<string, Reg>(); // unidad|ofic|cod
  respPorNombre = new Map<string, number>();
  aux = new Map<string, string>(); // unidad|grupo|cod
  auxPorNombre = new Map<string, number>();
  activos = new Map<string, Reg>(); // unidad|codigo
  codigosBaja = new Set<string>();
  revalKeys = new Set<string>();

  constructor(db: BdVsiaf) {
    this.entidad = db.entidad;
    const ent = this.entidad;
    for (const u of db.unidades()) this.unidades.set(u.unidad, { ...u, nueva: false });
    for (const r of db.tabla('OFICINA').registros()) {
      const v = r.valores;
      if (String(v.ENTIDAD ?? '').trim() !== ent) continue;
      const u = String(v.UNIDAD ?? '').trim(), c = Number(v.CODOFIC);
      this.oficinas.set(k2(u, c), { nom: v.NOMOFIC, api: v.API_ESTADO, nueva: false });
      this.ofPorNombre.set(k2(u, norm(v.NOMOFIC)), c);
    }
    for (const r of db.tabla('RESP').registros()) {
      const v = r.valores;
      if (String(v.ENTIDAD ?? '').trim() !== ent) continue;
      const u = String(v.UNIDAD ?? '').trim(), o = Number(v.CODOFIC), c = Number(v.CODRESP);
      this.resp.set(k3(u, o, c), { nom: v.NOMRESP, api: v.API_ESTADO, nueva: false });
      this.respPorNombre.set(k3(u, o, norm(v.NOMRESP)), c);
    }
    for (const r of db.tabla('AUXILIAR').registros()) {
      const v = r.valores;
      if (String(v.ENTIDAD ?? '').trim() !== ent) continue;
      const u = String(v.UNIDAD ?? '').trim(), g = Number(v.CODCONT), c = Number(v.CODAUX);
      this.aux.set(k3(u, g, c), String(v.NOMAUX ?? ''));
      this.auxPorNombre.set(k3(u, g, norm(v.NOMAUX)), c);
    }
    for (const r of db.tabla('ACTUAL').registros(true)) {
      const v = r.valores;
      if (String(v.ENTIDAD ?? '').trim() !== ent) continue;
      const key = k2(String(v.UNIDAD ?? '').trim(), String(v.CODIGO ?? '').trim().toUpperCase());
      if (r.borrado) { this.codigosBaja.add(key); continue; }
      this.activos.set(key, { ...v, _new: false, _src: 'VSIAF' });
    }
    for (const r of db.tabla('REVAL').registros()) {
      const v = r.valores;
      if (String(v.ENTIDAD ?? '').trim() === ent) this.revalKeys.add(k3(String(v.UNIDAD ?? '').trim(), String(v.CODIGO ?? '').trim().toUpperCase(), norm(v.RESOLUCION)));
    }
    for (const r of db.tabla('BAJAS').registros()) {
      const v = r.valores;
      if (String(v.ENTIDAD ?? '').trim() === ent) this.codigosBaja.add(k2(String(v.UNIDAD ?? '').trim(), String(v.CODIGO ?? '').trim().toUpperCase()));
    }
  }
  private max(vals: number[]): number { return vals.length ? Math.max(...vals) : 0; }
  siguienteOficina(u: string): number { return this.max([...this.oficinas.keys()].filter((k) => k.startsWith(u + '\u0001')).map((k) => Number(k.split('\u0001')[1]))) + 1; }
  siguienteResp(u: string, o: number): number { return this.max([...this.resp.keys()].filter((k) => k.startsWith(k2(u, o) + '\u0001')).map((k) => Number(k.split('\u0001')[2]))) + 1; }
  siguienteAux(u: string, g: number): number { return this.max([...this.aux.keys()].filter((k) => k.startsWith(k2(u, g) + '\u0001')).map((k) => Number(k.split('\u0001')[2]))) + 1; }
}

// ───────────── importador ─────────────
export class Importador {
  res: Resultado = { incidencias: [], conteos: {}, omitidas: {}, calculos: {}, aplicado: false, rutaRespaldo: null, notas: [] };
  readonly opt: Required<Pick<Opciones, 'usuario' | 'estadoPorDefecto' | 'soloValidas' | 'respaldar' | 'hoy' | 'fechaCalculo'>> & Opciones;
  private estado: Estado;
  private grupos = new Map<number, ReturnType<BdVsiaf['grupos']>[number]>();
  private gruposPorNombre = new Map<string, number>();
  private estados = new Map<string, number>();
  private estadosCodigos = new Set<number>();
  private motivos = new Map<number, string>();
  private motivosPorNombre = new Map<string, number>();
  private orgCodigos = new Set<string>();
  private deptos = new Map<string, number>();
  private incEspOk: boolean;
  private ops: Op[] = [];
  filasTotales: Record<string, number> = {};

  constructor(private db: BdVsiaf, private ufv: TablaUfv, opciones: Opciones = {}, private log: (m: string) => void = () => {}) {
    const hoy = opciones.hoy ?? hoyIso();
    this.opt = { usuario: 'admin', estadoPorDefecto: 'ELABORADO', soloValidas: false, respaldar: true, ...opciones, hoy, fechaCalculo: opciones.fechaCalculo ?? hoy };
    this.estado = new Estado(db);
    for (const g of db.grupos()) { this.grupos.set(g.codcont, g); this.gruposPorNombre.set(norm(g.nombre), g.codcont); }
    for (const e of db.estados()) { this.estados.set(norm(e.nombre), e.codigo); this.estadosCodigos.add(e.codigo); }
    for (const m of db.motivosBaja()) { this.motivos.set(m.codigo, m.nombre); this.motivosPorNombre.set(norm(m.nombre), m.codigo); }
    for (const o of db.organismos()) this.orgCodigos.add(o.codigo);
    for (const d of db.departamentos()) { this.deptos.set(norm(d.sigla), d.codigo); this.deptos.set(norm(d.nombre), d.codigo); this.deptos.set(String(d.codigo), d.codigo); }
    this.incEspOk = this.opt.permitirIncorporacionEspecial ?? incorporacionEspecialHabilitada();
  }

  // ------------------------------------------------------------------ utilidades
  private unidad(ctx: Ctx, col = 'unidad'): string | null {
    const u = comoTexto(ctx.raw(col)).trim() || this.opt.unidadPorDefecto || '';
    if (!u) { ctx.err(col, 'Falta la unidad: complete la columna o elija una unidad por defecto en el importador.'); return null; }
    if ([...u].length > 5) { ctx.err(col, 'El código de unidad excede 5 caracteres.'); return null; }
    if (!this.estado.unidades.has(u)) { ctx.err(col, `La unidad «${u}» no existe en el VSIAF ni en la hoja UNIDADES.`); return null; }
    return u;
  }

  private grupo(ctx: Ctx, col = 'grupo_contable') {
    const v = comoTexto(ctx.raw(col));
    if (!v) { ctx.err(col, 'Dato obligatorio vacío.'); return null; }
    if (/^\d+$/.test(v) && this.grupos.has(Number(v))) return this.grupos.get(Number(v))!;
    const n = norm(v);
    if (this.gruposPorNombre.has(n)) return this.grupos.get(this.gruposPorNombre.get(n)!)!;
    const cand = n.length >= 5 ? [...this.gruposPorNombre].filter(([k]) => k.startsWith(n)).map(([, c]) => c) : [];
    if (cand.length === 1) return this.grupos.get(cand[0])!;
    ctx.err(col, `Grupo contable «${v}» no reconocido (use el código 1-40 o el nombre de la hoja CATALOGOS).`);
    return null;
  }

  private oficina(ctx: Ctx, unidad: string, col: string, exigirActiva = true): number | null {
    const v = comoTexto(ctx.raw(col));
    if (!v) { ctx.err(col, 'Dato obligatorio vacío.'); return null; }
    const c = this.estado.ofPorNombre.get(k2(unidad, norm(v)));
    if (c === undefined) { ctx.err(col, `La oficina «${v}» no existe en la unidad ${unidad} (créela en la hoja OFICINAS).`); return null; }
    if (exigirActiva && this.estado.oficinas.get(k2(unidad, c))!.api !== 1) { ctx.err(col, `La oficina «${v}» está INACTIVA.`); return null; }
    return c;
  }

  private responsable(ctx: Ctx, unidad: string, ofic: number, col: string): number | null {
    const v = comoTexto(ctx.raw(col));
    if (!v) { ctx.err(col, 'Dato obligatorio vacío.'); return null; }
    const c = this.estado.respPorNombre.get(k3(unidad, ofic, norm(v)));
    if (c === undefined) { ctx.err(col, `El responsable «${v}» no existe en esa oficina (créelo en la hoja RESPONSABLES).`); return null; }
    if (this.estado.resp.get(k3(unidad, ofic, c))!.api !== 1) { ctx.err(col, `El responsable «${v}» está INACTIVO.`); return null; }
    return c;
  }

  private activo(ctx: Ctx, colUnidad: string, exigirAprobado = true): { key: string; unidad: string; codigo: string; a: Reg } | null {
    const unidad = this.unidad(ctx, colUnidad);
    const codigo = ctx.text('codigo', 15, true).toUpperCase();
    if (!unidad || !codigo) return null;
    const key = k2(unidad, codigo);
    const a = this.estado.activos.get(key);
    if (!a) { ctx.err('codigo', `No existe el activo «${codigo}» en la unidad ${unidad}${this.estado.codigosBaja.has(key) ? ' (ya fue dado de baja).' : '.'}`); return null; }
    if (exigirAprobado && a.API_ESTADO !== 3) {
      ctx.err('codigo', `El activo «${codigo}» está ELABORADO: apruébelo primero (el VSIAF solo permite revalúos, transferencias y bajas de activos APROBADOS).`);
      return null;
    }
    return { key, unidad, codigo, a };
  }

  private valuacion(a: Reg, calc: Fecha): Valuacion {
    const g = this.grupos.get(Number(a.CODCONT)) ?? { depreciar: true, actualizar: true };
    const inc = `${String(a.ANO).padStart(4, '0')}-${String(a.MES).padStart(2, '0')}-${String(a.DIA).padStart(2, '0')}`;
    return valuar(this.ufv, Number(a.COSTO ?? 0), Number(a.DEPACU ?? 0), Number(a.VIDAUTIL ?? 0), inc, calc, g.depreciar, g.actualizar);
  }
  private fechaBase(a: Reg): Fecha { return `${String(a.ANO).padStart(4, '0')}-${String(a.MES).padStart(2, '0')}-${String(a.DIA).padStart(2, '0')}`; }
  private omitir(hoja: string) { this.res.omitidas[hoja] = (this.res.omitidas[hoja] ?? 0) + 1; }

  // ------------------------------------------------------------------ UNIDADES
  private hojaUnidades(filas: Fila[]) {
    for (const f of filas) {
      const c = new Ctx(this.res, 'UNIDADES', f);
      const u = c.text('unidad', 5, true);
      const desc = c.text('descripcion', 120, true);
      const ciudad = c.text('ciudad', 20);
      if (c.ok && this.estado.unidades.has(u)) { c.warn('unidad', `La unidad ${u} ya existe: se omite.`); continue; }
      if (!c.ok) { this.omitir('UNIDADES'); continue; }
      this.estado.unidades.set(u, { unidad: u, descripcion: desc, ciudad, estado: 1, nueva: true });
      this.ops.push({ ref: f.ref, tipo: 'unidad', d: { ENTIDAD: this.estado.entidad, UNIDAD: u, DESCRIP: desc, CIUDAD: ciudad, ESTADOUNI: 1 } });
    }
  }

  // ------------------------------------------------------------------ OFICINAS
  private hojaOficinas(filas: Fila[]) {
    for (const f of filas) {
      const c = new Ctx(this.res, 'OFICINAS', f);
      const unidad = this.unidad(c);
      const nom = c.text('oficina', 65, true);
      const obs = c.text('observacion');
      if (!c.ok || !unidad) { this.omitir('OFICINAS'); continue; }
      if (this.estado.ofPorNombre.has(k2(unidad, norm(nom)))) { c.warn('oficina', `La oficina «${nom}» ya existe en la unidad ${unidad}: se omite.`); continue; }
      const cod = this.estado.siguienteOficina(unidad);
      this.estado.oficinas.set(k2(unidad, cod), { nom, api: 1, nueva: true });
      this.estado.ofPorNombre.set(k2(unidad, norm(nom)), cod);
      this.ops.push({ ref: f.ref, tipo: 'oficina', d: { ENTIDAD: this.estado.entidad, UNIDAD: unidad, CODOFIC: cod, NOMOFIC: nom, OBSERV: obs || null, FEULT: this.opt.hoy, USUAR: this.opt.usuario, API_ESTADO: 1 } });
    }
  }

  // ------------------------------------------------------------------ RESPONSABLES
  private hojaResponsables(filas: Fila[]) {
    for (const f of filas) {
      const c = new Ctx(this.res, 'RESPONSABLES', f);
      const unidad = this.unidad(c);
      const nom = c.text('responsable', 35, true);
      const cargo = c.text('cargo', 35, true);
      const ci = c.text('ci', 20);
      const exp = c.text('expedido');
      const obs = c.text('observacion');
      const ofic = unidad ? this.oficina(c, unidad, 'oficina', false) : null;
      let codExp = 0;
      if (exp) {
        codExp = this.deptos.get(norm(exp)) ?? 0;
        if (!codExp) c.err('expedido', `Departamento «${exp}» no reconocido (LPZ, CBB, SCZ, ORU, PTS, CHQ, TAR, BEN, PAN, OTR).`);
      }
      if (!c.ok || ofic === null || !unidad) { this.omitir('RESPONSABLES'); continue; }
      if (this.estado.respPorNombre.has(k3(unidad, ofic, norm(nom)))) { c.warn('responsable', `«${nom}» ya existe en esa oficina: se omite.`); continue; }
      const cod = this.estado.siguienteResp(unidad, ofic);
      this.estado.resp.set(k3(unidad, ofic, cod), { nom, api: 1, nueva: true });
      this.estado.respPorNombre.set(k3(unidad, ofic, norm(nom)), cod);
      this.ops.push({ ref: f.ref, tipo: 'resp', d: { ENTIDAD: this.estado.entidad, UNIDAD: unidad, CODOFIC: ofic, CODRESP: cod, NOMRESP: nom, CARGO: cargo, OBSERV: obs || null, CI: ci, FEULT: this.opt.hoy, USUAR: this.opt.usuario, COD_EXP: codExp, API_ESTADO: 1 } });
    }
  }

  // ------------------------------------------------------------------ AUXILIARES
  private hojaAuxiliares(filas: Fila[]) {
    for (const f of filas) {
      const c = new Ctx(this.res, 'AUXILIARES', f);
      const unidad = this.unidad(c);
      const g = this.grupo(c);
      const nom = c.text('auxiliar', 50, true);
      const obs = c.text('observacion');
      if (!c.ok || !g || !unidad) { this.omitir('AUXILIARES'); continue; }
      if (this.estado.auxPorNombre.has(k3(unidad, g.codcont, norm(nom)))) { c.warn('auxiliar', `El auxiliar «${nom}» ya existe en el grupo ${g.codcont}: se omite.`); continue; }
      const cod = this.estado.siguienteAux(unidad, g.codcont);
      if (cod > 999) { c.err('auxiliar', `El grupo ${g.codcont} ya tiene 999 auxiliares: no caben más.`); this.omitir('AUXILIARES'); continue; }
      this.estado.aux.set(k3(unidad, g.codcont, cod), nom);
      this.estado.auxPorNombre.set(k3(unidad, g.codcont, norm(nom)), cod);
      this.ops.push({ ref: f.ref, tipo: 'aux', d: { ENTIDAD: this.estado.entidad, UNIDAD: unidad, CODCONT: g.codcont, CODAUX: cod, NOMAUX: nom, OBSERV: obs || null, FEULT: this.opt.hoy, USUAR: this.opt.usuario } });
    }
  }

  // ------------------------------------------------------------------ ACTIVOS
  private hojaActivos(filas: Fila[]) {
    const out: Record<string, unknown>[] = [];
    for (const f of filas) {
      const c = new Ctx(this.res, 'ACTIVOS', f);
      const unidad = this.unidad(c);
      const codigo = c.text('codigo', 15, true).toUpperCase();
      const codSec = c.text('codigo_adicional', 15).toUpperCase();
      const desc = c.text('descripcion', 150, true);
      const g = this.grupo(c);
      const nomAux = c.text('auxiliar', undefined, true);
      const ofic = unidad ? this.oficina(c, unidad, 'oficina') : null;
      const resp = unidad && ofic !== null ? this.responsable(c, unidad, ofic, 'responsable') : null;
      const estTxt = c.text('estado_bien', undefined, true);
      const inc = c.date('fecha_incorporacion', true);
      const costo = c.number('costo_inicial', true);
      const vidaIn = c.number('vida_util');
      const depIn = c.number('dep_acumulada_inicial') || 0;
      const rube = c.text('cod_rube', 15);
      let org = c.text('organismo_financiador', undefined, true);
      const conv = c.text('nro_convenio', 10);
      const obs = c.text('observaciones');
      const estReg = norm(c.text('estado_registro')) || this.opt.estadoPorDefecto;
      const incEsp = c.yesno('incorporacion_especial');

      // código único
      if (unidad && codigo) {
        const key = k2(unidad, codigo);
        const prev = this.estado.activos.get(key);
        if (prev) c.err('codigo', `El código «${codigo}» ya existe ${!prev._new ? 'en el VSIAF' : `en la fila ${prev._src} de este libro`} (unidad ${unidad}).`);
        else if (this.estado.codigosBaja.has(key)) c.warn('codigo', `El código «${codigo}» corresponde a un activo dado de baja; verifique que no sea un duplicado.`);
      }
      // estado del bien
      let codEstado: number | null = null;
      if (estTxt) {
        codEstado = this.estados.get(norm(estTxt)) ?? null;
        if (codEstado === null && /^\d+$/.test(estTxt) && this.estadosCodigos.has(Number(estTxt))) codEstado = Number(estTxt);
        if (codEstado === null) c.err('estado_bien', `Estado «${estTxt}» no válido (Bueno, Regular o Malo).`);
      }
      // organismo financiador
      if (org) {
        const o = norm(org) === 'NC' ? '000' : /^\d+$/.test(org) ? org.padStart(3, '0') : org;
        if (!this.orgCodigos.has(o)) c.err('organismo_financiador', `Organismo financiador «${org}» no existe en el clasificador.`);
        org = o;
      }
      // estado de registro
      if (!['ELABORADO', 'APROBADO'].includes(estReg)) c.err('estado_registro', 'Use ELABORADO o APROBADO.');
      // auxiliar
      let codAux: number | null = null;
      if (g && unidad && nomAux) {
        codAux = this.estado.auxPorNombre.get(k3(unidad, g.codcont, norm(nomAux))) ?? null;
        if (codAux === null) c.err('auxiliar', `El auxiliar «${nomAux}» no existe en el grupo «${g.nombre}» de la unidad ${unidad} (créelo en la hoja AUXILIARES).`);
      }
      // fecha
      if (inc !== null) {
        if (inc > this.opt.hoy) c.err('fecha_incorporacion', 'La fecha de incorporación no puede ser futura.');
        else if (!this.ufv.tiene(inc)) c.err('fecha_incorporacion', `No hay UFV registrada para ${dmy(inc)} (el VSIAF no permite operar sin índice).`);
        else if (partes(inc).y < partes(this.opt.hoy).y) c.warn('fecha_incorporacion', 'Activo de una gestión anterior: el VSIAF recalcula su actualización y depreciación desde esa fecha; revise el Reporte 6 luego de importar.');
      }
      // costo / vida útil / dep. acumulada
      let vida = 0;
      let banderas = '0';
      if (costo !== null && costo <= 0) c.err('costo_inicial', 'El costo debe ser mayor a cero.');
      if (g) {
        const vg = Number(g.vida_util);
        if (incEsp) {
          if (!this.incEspOk) c.err('incorporacion_especial', 'Este equipo no tiene habilitadas las Incorporaciones Especiales (llave de la DGCF). El importador no puede saltarse esa autorización.');
          else if (vidaIn === null && g.depreciar) c.err('vida_util', 'Indique la vida útil de la incorporación especial.');
          vida = Number(vidaIn ?? vg);
          banderas = '1';
        } else {
          if (vidaIn !== null && Math.abs(vidaIn - vg) > 1e-9) c.err('vida_util', `La vida útil (${vidaIn}) difiere de la del grupo (${vg} años). Solo se permite como Incorporación Especial autorizada por la DGCF.`);
          vida = vg;
          if (depIn) c.err('dep_acumulada_inicial', 'El VSIAF solo admite depreciación acumulada inicial en incorporaciones especiales (en un alta normal la calcula desde la fecha).');
        }
        if (g.depreciar && vida <= 0) c.err('vida_util', 'La vida útil no puede ser cero en un grupo que se deprecia.');
        if (!g.depreciar) {
          vida = 0;
          if (depIn) c.err('dep_acumulada_inicial', 'El grupo no se deprecia.');
        }
        if (costo !== null && depIn > costo) c.err('dep_acumulada_inicial', 'La depreciación acumulada no puede superar el costo.');
      }
      if (!c.ok || !unidad || !g || inc === null || costo === null) { this.omitir('ACTIVOS'); continue; }

      const rec = {
        UNIDAD: unidad, ENTIDAD: this.estado.entidad, CODIGO: codigo, CODCONT: g.codcont, CODAUX: codAux, VIDAUTIL: vida, DESCRIP: desc, COSTO: costo, DEPACU: depIn,
        MES: partes(inc).m, ANO: partes(inc).y, B_REV: false, DIA: partes(inc).d, CODOFIC: ofic, CODRESP: resp, OBSERV: obs || null, BAND_UFV: false, CODESTADO: codEstado,
        COD_RUBE: rube, NRO_CONV: conv, ORG_FIN: org, FEULT: this.opt.hoy, USUAR: this.opt.usuario, API_ESTADO: estReg === 'APROBADO' ? 3 : 1,
        CODIGOSEC: codSec, BANDERAS: banderas, USU_MOD: '',
      };
      this.estado.activos.set(k2(unidad, codigo), { ...rec, _new: true, _src: f.ref });
      this.ops.push({ ref: f.ref, tipo: 'actual_new', d: rec });
      try {
        const v = this.valuacion(rec, this.opt.fechaCalculo > inc ? this.opt.fechaCalculo : inc);
        out.push(filaCalculo(f.ref, rec, g.nombre, v, estReg));
      } catch (e) {
        if (e instanceof UfvFaltante) c.warn('fecha_incorporacion', `No se pudo calcular la vista previa: ${e.message}`);
        else throw e;
      }
    }
    this.res.calculos.ACTIVOS = out;
  }

  // ------------------------------------------------------------------ REVALUOS
  private hojaRevaluos(filas: Fila[]) {
    const out: Record<string, unknown>[] = [];
    const orden = filas.map((f, i) => ({ f, i, d: (() => { try { return comoFecha(f.datos.fecha_revaluo); } catch { return null; } })() ?? '9999-12-31' }));
    orden.sort((a, b) => (a.d < b.d ? -1 : a.d > b.d ? 1 : a.i - b.i));
    for (const { f } of orden) {
      const c = new Ctx(this.res, 'REVALUOS', f);
      const got = this.activo(c, 'unidad');
      const fecha = c.date('fecha_revaluo', true);
      const costoN = c.number('nuevo_costo', true);
      const vidaN = c.number('nueva_vida_util', true);
      const resol = c.text('disposicion_respaldo', 16, true);
      const motivo = c.text('motivo');
      if (!got || !c.ok) { this.omitir('REVALUOS'); continue; }
      const { key, unidad, codigo, a } = got;
      const g = this.grupos.get(Number(a.CODCONT)) ?? { depreciar: true, actualizar: true, nombre: '' };
      const base = this.fechaBase(a);
      if (fecha !== null) {
        if (fecha > this.opt.hoy) c.err('fecha_revaluo', 'La fecha del revalúo no puede ser futura.');
        else if (fecha < base) c.err('fecha_revaluo', `La fecha del revalúo es anterior a la fecha base del activo (${dmy(base)}).`);
        else if (!(this.ufv.tiene(fecha) && this.ufv.tiene(sumarDias(fecha, 1)))) c.err('fecha_revaluo', `No hay UFV registrada para ${dmy(fecha)} (o el día siguiente).`);
      }
      if (costoN !== null && costoN <= 0) c.err('nuevo_costo', 'El nuevo costo debe ser mayor a cero.');
      if (vidaN !== null && vidaN <= 0 && g.depreciar) c.err('nueva_vida_util', 'La nueva vida útil no puede ser cero.');
      if (resol && this.estado.revalKeys.has(k3(unidad, codigo, norm(resol)))) c.err('disposicion_respaldo', `Ya existe un revalúo del activo con la disposición «${resol}».`);
      if (!c.ok || fecha === null) { this.omitir('REVALUOS'); continue; }
      let v: Valuacion;
      try { v = this.valuacion(a, fecha); } catch (e) {
        if (e instanceof UfvFaltante) { c.err('fecha_revaluo', e.message); this.omitir('REVALUOS'); continue; }
        throw e;
      }
      const nuevaBase = sumarDias(fecha, 1);
      const rv = {
        ENTIDAD: this.estado.entidad, UNIDAD: unidad, CODIGO: codigo, COSTO: a.COSTO, DEPACU_ANT: a.DEPACU || 0, D_REVAL: partes(fecha).d, DIA: a.DIA, M_REVAL: partes(fecha).m, MES: a.MES,
        A_REVAL: partes(fecha).y, ANO: a.ANO, VIDAUTIL: a.VIDAUTIL, RESOLUCION: resol, OBSERV: motivo || null, USUAR: this.opt.usuario, FEULT: this.opt.hoy,
        DEPACU: v.snapDepacu, ACTUA: v.snapActua, DEPGESTION: v.depGestion, USU_MOD: '',
      };
      const upd = { DIA: partes(nuevaBase).d, MES: partes(nuevaBase).m, ANO: partes(nuevaBase).y, B_REV: true, COSTO: costoN, VIDAUTIL: g.depreciar ? vidaN : 0, DEPACU: 0 };
      this.ops.push({ ref: f.ref, tipo: 'reval', d: { row: rv, key, unidad, codigo, update: upd } });
      this.estado.revalKeys.add(k3(unidad, codigo, norm(resol)));
      Object.assign(a, upd);
      out.push({ fila: f.ref, unidad, codigo, fecha_revaluo: fecha, costo_anterior: rv.COSTO, vida_anterior: rv.VIDAUTIL, valor_actualizado: v.valorActualizado, dep_gestion: v.depGestion,
        dep_acumulada_anterior: v.snapDepacu, valor_neto_anterior: v.snapActua, nuevo_costo: costoN, nueva_vida: upd.VIDAUTIL, nueva_fecha_base: nuevaBase, resolucion: resol });
    }
    this.res.calculos.REVALUOS = out;
  }

  // ------------------------------------------------------------------ TRANSFERENCIAS
  private hojaTransferencias(filas: Fila[]) {
    const out: Record<string, unknown>[] = [];
    for (const f of filas) {
      const c = new Ctx(this.res, 'TRANSFERENCIAS', f);
      const got = this.activo(c, 'unidad_origen');
      const destTxt = comoTexto(c.raw('unidad_destino')).trim();
      if (!got) { this.omitir('TRANSFERENCIAS'); continue; }
      const { key, unidad, codigo, a } = got;
      const dest = destTxt || unidad;
      if (!this.estado.unidades.has(dest)) c.err('unidad_destino', `La unidad destino «${dest}» no existe.`);
      const ofic = this.estado.unidades.has(dest) ? this.oficina(c, dest, 'oficina_destino') : null;
      const resp = ofic !== null ? this.responsable(c, dest, ofic, 'responsable_destino') : null;
      let codAux = Number(a.CODAUX);
      const auxTxt = c.text('auxiliar_destino');
      if (dest !== unidad) {
        if (this.estado.activos.has(k2(dest, codigo))) c.err('unidad_destino', `Ya existe un activo «${codigo}» en la unidad ${dest}: no se puede transferir (el VSIAF lo impide).`);
        if (!auxTxt) c.err('auxiliar_destino', 'Al transferir entre unidades se debe indicar el auxiliar de destino.');
        else {
          const n = this.estado.auxPorNombre.get(k3(dest, Number(a.CODCONT), norm(auxTxt)));
          if (n === undefined) c.err('auxiliar_destino', `El auxiliar «${auxTxt}» no existe en el grupo del activo en la unidad ${dest}.`);
          else codAux = n;
        }
      }
      if (!c.ok || ofic === null || resp === null) { this.omitir('TRANSFERENCIAS'); continue; }
      if (dest === unidad && ofic === a.CODOFIC && resp === a.CODRESP) { c.warn('codigo', 'La oficina y el responsable de destino son los mismos que los actuales: se omite.'); continue; }
      this.ops.push({ ref: f.ref, tipo: 'trasfe', d: { key, codigo, update: { CODOFIC: ofic, CODRESP: resp, UNIDAD: dest, CODAUX: codAux },
        row: { ENTIDAD: this.estado.entidad, UNIDAD: dest, CODIGO: codigo, CODOFIC: ofic, CODRESP: resp, FEULT: this.opt.hoy, USUAR: this.opt.usuario, UNIDADINI: unidad } } });
      this.estado.activos.delete(key);
      Object.assign(a, { UNIDAD: dest, CODOFIC: ofic, CODRESP: resp, CODAUX: codAux });
      this.estado.activos.set(k2(dest, codigo), a);
      out.push({ fila: f.ref, codigo, unidad_origen: unidad, unidad_destino: dest, oficina: this.estado.oficinas.get(k2(dest, ofic))!.nom, responsable: this.estado.resp.get(k3(dest, ofic, resp))!.nom });
    }
    this.res.calculos.TRANSFERENCIAS = out;
  }

  // ------------------------------------------------------------------ BAJAS
  private hojaBajas(filas: Fila[]) {
    const out: Record<string, unknown>[] = [];
    const orden = filas.map((f, i) => ({ f, i, d: (() => { try { return comoFecha(f.datos.fecha_baja); } catch { return null; } })() ?? '9999-12-31' }));
    orden.sort((a, b) => (a.d < b.d ? -1 : a.d > b.d ? 1 : a.i - b.i));
    for (const { f } of orden) {
      const c = new Ctx(this.res, 'BAJAS', f);
      const got = this.activo(c, 'unidad');
      const fecha = c.date('fecha_baja', true);
      const motTxt = c.text('motivo_baja', undefined, true);
      const resol = c.text('disposicion_respaldo', 16, true);
      const obs = c.text('observaciones', 120);
      let codBaja: number | null = null;
      if (motTxt) {
        if (/^\d+$/.test(motTxt) && this.motivos.has(Number(motTxt))) codBaja = Number(motTxt);
        else {
          codBaja = this.motivosPorNombre.get(norm(motTxt)) ?? null;
          if (codBaja === null) { const cand = [...this.motivosPorNombre].filter(([n]) => n.startsWith(norm(motTxt))).map(([, k]) => k); codBaja = cand.length === 1 ? cand[0] : null; }
        }
        if (codBaja === null) c.err('motivo_baja', `Motivo de baja «${motTxt}» no reconocido (códigos 1-9, ver hoja CATALOGOS).`);
      }
      if (!got || !c.ok) { this.omitir('BAJAS'); continue; }
      const { key, unidad, codigo, a } = got;
      const base = this.fechaBase(a);
      if (fecha !== null) {
        if (fecha > this.opt.hoy) c.err('fecha_baja', 'La fecha de baja no puede ser futura.');
        else if (fecha < base) c.err('fecha_baja', `La fecha de baja es anterior a la fecha base del activo (${dmy(base)}).`);
        else if (!this.ufv.tiene(fecha)) c.err('fecha_baja', `No hay UFV registrada para ${dmy(fecha)}.`);
      }
      if (codBaja === 9 && fecha !== null && partes(base).y !== partes(fecha).y) c.err('motivo_baja', '«Error de transcripción» solo puede aplicarse a activos incorporados en la gestión vigente (el VSIAF exige regularizarlo con la DGCF).');
      if (!c.ok || fecha === null || codBaja === null) { this.omitir('BAJAS'); continue; }
      let v: Valuacion;
      try { v = this.valuacion(a, fecha); } catch (e) {
        if (e instanceof UfvFaltante) { c.err('fecha_baja', e.message); this.omitir('BAJAS'); continue; }
        throw e;
      }
      if ([...String(a.DESCRIP)].length > 120) c.warn('codigo', 'La descripción se recorta a 120 caracteres en la tabla BAJAS (igual que el VSIAF).');
      const bj = {
        ENTIDAD: this.estado.entidad, UNIDAD: unidad, CODIGO: codigo, CODBAJA: codBaja, CODCONT: a.CODCONT, CODAUX: a.CODAUX, CODOFIC: a.CODOFIC, CODRESP: a.CODRESP, COSTO: a.COSTO,
        DEPACU_ANT: v.depAcumuladaIni, DESCRIP: [...String(a.DESCRIP)].slice(0, 120).join(''), D_BAJA: partes(fecha).d, DIA: a.DIA, M_BAJA: partes(fecha).m, MES: a.MES, A_BAJA: partes(fecha).y, ANO: a.ANO,
        B_REV: !!a.B_REV, VIDAUTIL: a.VIDAUTIL, RESOLUCION: resol, OBSERV: DADO_DE_BAJA, MOTIVO: obs, DEPACU: v.snapDepacu, ACTUA: v.snapActua, DEPGESTION: v.depGestion,
        COSBAJINI: v.valorActualizadoIni, COSDAINI: v.depAcumuladaIni, COSACTBAJ: v.valorActualizado, ACTDABAJ: v.actualizacionDep, USUAR: this.opt.usuario, FEULT: this.opt.hoy, USU_MOD: '',
      };
      this.ops.push({ ref: f.ref, tipo: 'baja', d: { row: bj, key, unidad, codigo } });
      this.estado.activos.delete(key);
      this.estado.codigosBaja.add(key);
      out.push({ fila: f.ref, unidad, codigo, fecha_baja: fecha, motivo: this.motivos.get(codBaja), costo: a.COSTO, costo_actualizado: v.valorActualizado, dep_gestion: v.depGestion,
        dep_acumulada: v.depAcumulada, valor_neto: v.valorNeto, resolucion: resol });
    }
    this.res.calculos.BAJAS = out;
  }

  // ------------------------------------------------------------------ validación / plan
  plan(entrada: Libro | LibroConProblemas): Resultado {
    const libro: Libro = 'libro' in entrada ? entrada.libro : entrada;
    for (const p of ('libro' in entrada ? entrada.problemas ?? [] : [])) {
      this.res.incidencias.push({ hoja: '(estructura)', ref: 0, columna: '', nivel: /falta la columna|ninguna hoja/.test(p) ? ERROR : AVISO, mensaje: p });
    }
    if (this.ufv.origen.toLowerCase().endsWith('.csv')) {
      this.res.incidencias.push({ hoja: '(UFV)', ref: 0, columna: '', nivel: AVISO, mensaje: 'No se encontró tipocambio.app en la instalación: se usan las UFV incluidas en SIGAA, que son aproximadas desde 2021. La vista previa de cálculo puede diferir del VSIAF; las fechas sin UFV también se rechazan.' });
    }
    const dias = this.ufv.diasDesdeUltimoCambio(this.opt.fechaCalculo);
    if (dias !== null && dias > 75) {
      this.res.incidencias.push({ hoja: '(UFV)', ref: 0, columna: '', nivel: AVISO, mensaje: `Las UFV del VSIAF parecen desactualizadas: el último cambio de índice es del ${dmy(this.ufv.ultimoCambio!)}. Ejecute el actualizador de UFV del Ministerio (cada día 10) para que el módulo y el VSIAF calculen con índices vigentes.` });
    }
    if (this.db.gestionCerrada()) this.res.incidencias.push({ hoja: '(BD)', ref: 0, columna: '', nivel: ERROR, mensaje: 'La gestión de esta base está CERRADA: el VSIAF no permite modificarla.' });
    const manejadores: [Hoja, (f: Fila[]) => void][] = [
      ['UNIDADES', (f) => this.hojaUnidades(f)], ['OFICINAS', (f) => this.hojaOficinas(f)], ['RESPONSABLES', (f) => this.hojaResponsables(f)], ['AUXILIARES', (f) => this.hojaAuxiliares(f)],
      ['ACTIVOS', (f) => this.hojaActivos(f)], ['REVALUOS', (f) => this.hojaRevaluos(f)], ['TRANSFERENCIAS', (f) => this.hojaTransferencias(f)], ['BAJAS', (f) => this.hojaBajas(f)],
    ];
    for (const [nombre, fn] of manejadores) {
      const filas = libro[nombre] ?? [];
      this.filasTotales[nombre] = filas.length;
      if (filas.length) { this.log(`Validando ${nombre} (${filas.length} filas)…`); fn(filas); }
    }
    const tipos: Record<Op['tipo'], string> = { unidad: 'UNIDADES', oficina: 'OFICINAS', resp: 'RESPONSABLES', aux: 'AUXILIARES', actual_new: 'ACTIVOS', reval: 'REVALUOS', trasfe: 'TRANSFERENCIAS', baja: 'BAJAS' };
    for (const o of this.ops) this.res.conteos[tipos[o.tipo]] = (this.res.conteos[tipos[o.tipo]] ?? 0) + 1;
    return this.res;
  }

  /** Operaciones planificadas (para registrar qué filas de origen se importaron). */
  planificadas(): { hoja: Hoja; ref: number | string }[] {
    const hojas: Record<Op['tipo'], Hoja> = { unidad: 'UNIDADES', oficina: 'OFICINAS', resp: 'RESPONSABLES', aux: 'AUXILIARES', actual_new: 'ACTIVOS', reval: 'REVALUOS', trasfe: 'TRANSFERENCIAS', baja: 'BAJAS' };
    return this.ops.map((o) => ({ hoja: hojas[o.tipo], ref: o.ref }));
  }

  // ------------------------------------------------------------------ aplicar
  /** Escribe el plan en la BD. Debe llamarse después de `plan`. */
  aplicar(descripcion = 'Importación desde SIGAA'): Resultado {
    const res = this.res;
    const bloqueantes = res.incidencias.filter((i) => i.nivel === ERROR && (i.hoja === '(BD)' || i.hoja === '(estructura)'));
    if (bloqueantes.length) throw new ImportacionAbortada(bloqueantes[0].mensaje);
    const nErr = errores(res);
    if (nErr && !this.opt.soloValidas) throw new ImportacionAbortada(`Hay ${nErr} error(es). Corríjalos o active «importar solo filas válidas».`);
    if (!this.ops.length) throw new ImportacionAbortada('No hay nada que importar.');
    if (!this.opt.omitirProceso && vsiafAbierto()) throw new ImportacionAbortada('El VSIAF está abierto. Ciérrelo antes de importar.');
    const db = this.db;
    if (this.opt.respaldar) {
      res.rutaRespaldo = hacerRespaldo(db, descripcion);
      this.log(`Respaldo creado: ${res.rutaRespaldo}`);
    }
    const originales = new Map<string, Buffer>();
    for (const p of db.archivosAfectados()) if (fs.existsSync(p)) originales.set(p, fs.readFileSync(p));
    try {
      this.escribir();
      this.opt.fallaSimulada?.('antes-de-guardar');
      db.guardarTodo();
      this.opt.fallaSimulada?.('despues-de-guardar');
      this.verificar();
    } catch (e) {
      for (const [p, data] of originales) fs.writeFileSync(p, data); // deshacer: restaurar los archivos tal como estaban
      db.recargar();
      throw e;
    }
    res.aplicado = true;
    return res;
  }

  private escribir(): void {
    const db = this.db;
    const tAct = db.tabla('ACTUAL'), tRev = db.tabla('REVAL'), tBaj = db.tabla('BAJAS'), tTra = db.tabla('TRASFE');
    const recno = new Map<string, number>();
    const ent = this.estado.entidad;
    for (const r of tAct.registros(true)) {
      if (String(r.valores.ENTIDAD ?? '').trim() === ent && !r.borrado) recno.set(k2(String(r.valores.UNIDAD ?? '').trim(), String(r.valores.CODIGO ?? '').trim().toUpperCase()), r.recno);
    }
    const tablas: Record<string, string> = { unidad: 'UNIDADADMIN', oficina: 'OFICINA', resp: 'RESP', aux: 'AUXILIAR' };
    let n = 0;
    for (const o of this.ops) {
      this.opt.fallaSimulada?.(`op-${n++}`);
      if (tablas[o.tipo]) db.tabla(tablas[o.tipo]).agregar(o.d);
      else if (o.tipo === 'actual_new') recno.set(k2(o.d.UNIDAD, o.d.CODIGO), tAct.agregar(o.d));
      else if (o.tipo === 'reval') { tRev.agregar(o.d.row); tAct.actualizar(recno.get(o.d.key)!, o.d.update); }
      else if (o.tipo === 'trasfe') {
        tTra.agregar(o.d.row);
        const r = recno.get(o.d.key)!;
        recno.delete(o.d.key);
        tAct.actualizar(r, o.d.update);
        recno.set(k2(o.d.update.UNIDAD, o.d.codigo), r);
      } else if (o.tipo === 'baja') {
        tBaj.agregar(o.d.row);
        const r = recno.get(o.d.key)!;
        recno.delete(o.d.key);
        tAct.actualizar(r, { OBSERV: DADO_DE_BAJA });
        tAct.marcarBorrado(r, true);
      }
    }
  }

  /** Relee los archivos desde el disco y comprueba que el resultado coincide con el plan. */
  private verificar(): void {
    const quiere: Record<string, number> = { actual_new: 0, reval: 0, baja: 0, trasfe: 0, oficina: 0, resp: 0, aux: 0, unidad: 0 };
    for (const o of this.ops) quiere[o.tipo]++;
    const archivos: Record<string, string> = { ACTUAL: 'actual_new', REVAL: 'reval', BAJAS: 'baja', TRASFE: 'trasfe', OFICINA: 'oficina', RESP: 'resp', AUXILIAR: 'aux', UNIDADADMIN: 'unidad' };
    for (const [nombre, tipo] of Object.entries(archivos)) {
      const t = this.db.tabla(nombre);
      const fresca = new DbfTabla(t.ruta);
      if (fresca.nrec !== t.nrec) throw new DbfError(`Verificación fallida en ${nombre}: ${fresca.nrec} registros en disco, se esperaban ${t.nrec}.`);
      if (quiere[tipo]) for (let n = Math.max(1, fresca.nrec - quiere[tipo] + 1); n <= fresca.nrec; n++) fresca.leer(n); // decodifica campos y memos recién escritos
    }
  }
}

function filaCalculo(fila: number | string, rec: Reg, grupo: string, v: Valuacion, estado: string): Record<string, unknown> {
  return {
    fila, unidad: rec.UNIDAD, codigo: rec.CODIGO, grupo, codcont: rec.CODCONT, estado, incorporacion: `${rec.ANO}-${String(rec.MES).padStart(2, '0')}-${String(rec.DIA).padStart(2, '0')}`,
    vida_util: rec.VIDAUTIL, costo_historico: v.costo, factor: v.factor, costo_actualizado_inicial: v.valorActualizadoIni, actualizacion_gestion: v.actualizacionGestion,
    costo_total_actualizado: v.valorActualizado, dep_gestion: v.depGestion, dep_acumulada_inicial: v.depAcumuladaIni, actualizacion_dep_acumulada: v.actualizacionDep,
    dep_acumulada: v.depAcumulada, valor_neto: v.valorNeto, dias: v.diasTotales,
  };
}
