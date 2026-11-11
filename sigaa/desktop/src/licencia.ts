/**
 * Licenciamiento de SIGAA Escritorio: clave de activación firmada (Ed25519).
 * - La clave la emite el proveedor con su clave PRIVADA (herramienta tools/licencias); la aplicación solo trae la clave PÚBLICA
 *   y por eso no puede fabricar claves nuevas.
 * - La clave puede atarse a un equipo (ID del equipo) y/o a una fecha de vencimiento; si no, es perpetua para cualquier equipo.
 * - Sin clave, la aplicación funciona en modo de PRUEBA durante 30 días.
 * Nota honesta: un licenciamiento local desalienta el uso no autorizado, pero no es infalible frente a quien modifique el programa.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

export const PREFIJO = 'SIGAA1-';
export const DIAS_PRUEBA = 30;
export const AVISO_VENCIMIENTO_DIAS = 30;

export interface DatosLicencia {
  v: 1;
  n: string; // entidad
  m: string; // ID de equipo o '*' (cualquier equipo)
  e: string; // vencimiento AAAA-MM-DD o '' (perpetua)
  t: string; // tipo: ANUAL | PERPETUA | ...
  i: string; // fecha de emisión
}
export type Estado =
  | { estado: 'ACTIVA'; entidad: string; tipo: string; vence: string; diasRestantes: number | null; equipo: string }
  | { estado: 'PRUEBA'; diasRestantes: number; equipo: string }
  | { estado: 'SIN_LICENCIA' | 'VENCIDA' | 'INVALIDA' | 'OTRO_EQUIPO' | 'PRUEBA_TERMINADA'; mensaje: string; equipo: string };

const b64u = (b: Buffer) => b.toString('base64url');
const hoyIso = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const diasEntre = (a: string, b: string) => Math.round((Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / 86400000);

/** Identificador estable del equipo: GUID de Windows (MachineGuid) o, si no existe, nombre + MAC del equipo. Se muestra como XXXX-XXXX-XXXX-XXXX. */
export function idEquipo(): string {
  let base = '';
  if (process.platform === 'win32') {
    try {
      const out = execFileSync('reg', ['query', 'HKLM\\SOFTWARE\\Microsoft\\Cryptography', '/v', 'MachineGuid'], { encoding: 'utf8', windowsHide: true });
      base = (out.match(/MachineGuid\s+REG_SZ\s+(\S+)/i) || [])[1] || '';
    } catch { /* se usa la alternativa */ }
  }
  if (!base) {
    const macs = Object.values(os.networkInterfaces()).flat().filter((x) => x && !x.internal && x.mac && x.mac !== '00:00:00:00:00:00').map((x) => x!.mac).sort();
    base = `${os.hostname()}|${macs[0] || ''}|${os.platform()}`;
  }
  const h = crypto.createHash('sha256').update('sigaa-equipo|' + base).digest('hex').slice(0, 16).toUpperCase();
  return h.match(/.{4}/g)!.join('-');
}

/** Verifica la firma de una clave y devuelve sus datos (o lanza Error con el motivo). */
export function leerClave(clave: string, clavePublicaPem: string): DatosLicencia {
  const t = String(clave || '').replace(/\s+/g, '');
  if (!t.startsWith(PREFIJO)) throw new Error('La clave no tiene el formato de SIGAA. Cópiela completa, tal como la recibió.');
  const [p, s] = t.slice(PREFIJO.length).split('.');
  if (!p || !s) throw new Error('La clave está incompleta. Cópiela completa.');
  let ok = false;
  try { ok = crypto.verify(null, Buffer.from(p, 'base64url'), crypto.createPublicKey(clavePublicaPem), Buffer.from(s, 'base64url')); } catch { ok = false; }
  if (!ok) throw new Error('La clave no es válida (firma incorrecta). Verifique que esté completa o solicite una nueva.');
  const d = JSON.parse(Buffer.from(p, 'base64url').toString('utf8')) as DatosLicencia;
  if (d.v !== 1 || typeof d.m !== 'string') throw new Error('Versión de clave no reconocida.');
  return d;
}

/** Evalúa una clave contra el equipo y la fecha actual. */
export function evaluarClave(clave: string, clavePublicaPem: string, equipo: string, hoy = hoyIso()): Estado {
  let d: DatosLicencia;
  try { d = leerClave(clave, clavePublicaPem); } catch (e: any) { return { estado: 'INVALIDA', mensaje: e.message, equipo }; }
  if (d.m !== '*' && d.m.replace(/-/g, '').toUpperCase() !== equipo.replace(/-/g, '')) return { estado: 'OTRO_EQUIPO', mensaje: `Esta clave fue emitida para otro equipo (${d.m}). El ID de este equipo es ${equipo}.`, equipo };
  if (d.e) {
    const dias = diasEntre(hoy, d.e);
    if (dias < 0) return { estado: 'VENCIDA', mensaje: `La licencia venció el ${d.e.split('-').reverse().join('/')}. Solicite la renovación.`, equipo };
    return { estado: 'ACTIVA', entidad: d.n, tipo: d.t, vence: d.e, diasRestantes: dias, equipo };
  }
  return { estado: 'ACTIVA', entidad: d.n, tipo: d.t || 'PERPETUA', vence: '', diasRestantes: null, equipo };
}

// ───────── Modo de prueba (30 días), protegido contra edición simple del archivo y retroceso del reloj ─────────
const firma = (equipo: string, ini: string, ult: string) => crypto.createHmac('sha256', 'sigaa-prueba|' + equipo).update(`${ini}|${ult}`).digest('hex');

export function estadoPrueba(archivo: string, equipo: string, hoy = hoyIso()): Estado {
  let ini = hoy, ult = hoy, alterado = false;
  if (fs.existsSync(archivo)) {
    try {
      const j = JSON.parse(fs.readFileSync(archivo, 'utf8'));
      if (j.f !== firma(equipo, j.ini, j.ult)) alterado = true;
      else { ini = j.ini; ult = j.ult; }
    } catch { alterado = true; }
  }
  if (alterado) return { estado: 'PRUEBA_TERMINADA', mensaje: 'El registro del período de prueba fue alterado. Solicite una clave de activación.', equipo };
  if (diasEntre(ult, hoy) < -1) return { estado: 'PRUEBA_TERMINADA', mensaje: 'Se detectó que la fecha del equipo fue retrocedida. Solicite una clave de activación.', equipo };
  const ultimo = hoy > ult ? hoy : ult;
  try { fs.writeFileSync(archivo, JSON.stringify({ ini, ult: ultimo, f: firma(equipo, ini, ultimo) })); } catch { /* sin permiso de escritura: se evalúa igual */ }
  const restan = DIAS_PRUEBA - diasEntre(ini, hoy);
  if (restan <= 0) return { estado: 'PRUEBA_TERMINADA', mensaje: `Terminó el período de prueba de ${DIAS_PRUEBA} días. Ingrese su clave de activación.`, equipo };
  return { estado: 'PRUEBA', diasRestantes: restan, equipo };
}

/** Estado completo: primero la clave guardada; si no hay, el período de prueba. */
export function estadoLicencia(dir: string, clavePublicaPem: string, hoy = hoyIso(), equipo = idEquipo()): Estado {
  const f = path.join(dir, 'licencia.key');
  if (fs.existsSync(f)) {
    const e = evaluarClave(fs.readFileSync(f, 'utf8'), clavePublicaPem, equipo, hoy);
    if (e.estado === 'ACTIVA') return e;
    if (e.estado !== 'INVALIDA') return e; // vencida u otro equipo: se informa tal cual
  }
  return estadoPrueba(path.join(dir, 'prueba.dat'), equipo, hoy);
}

/** Valida y guarda una clave nueva. Lanza Error si no sirve para este equipo. */
export function activar(dir: string, clave: string, clavePublicaPem: string, equipo = idEquipo(), hoy = hoyIso()): Estado {
  const e = evaluarClave(clave, clavePublicaPem, equipo, hoy);
  if (e.estado !== 'ACTIVA') throw new Error('mensaje' in e ? e.mensaje : 'La clave no es válida.');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'licencia.key'), String(clave).replace(/\s+/g, '') + '\n');
  return e;
}

export const permiteUsar = (e: Estado) => e.estado === 'ACTIVA' || e.estado === 'PRUEBA';
export { b64u };
