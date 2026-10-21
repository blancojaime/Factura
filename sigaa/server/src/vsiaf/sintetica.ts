/**
 * Base sintética de ensayo: reproduce la estructura de las tablas del VSIAF 2.0 (vacías, con sus catálogos) para
 * probar la importación **sin tocar una instalación real**. Se usa en las pruebas automáticas y como «base de práctica».
 */
import fs from 'node:fs';
import path from 'node:path';
import { crearTabla, DbfTabla } from './dbf.js';
import { ESPECIFICACIONES } from './especificaciones.js';
import { catalogosIncluidos } from './instalacion.js';

export function crearInstalacionSintetica(raiz: string, opciones: { entidad?: string; entidadNombre?: string; unidad?: string; unidadDesc?: string } = {}): string {
  const entidad = opciones.entidad ?? '9999';
  const entidadNombre = opciones.entidadNombre ?? 'ENTIDAD DE DEMOSTRACION';
  const unidad = opciones.unidad ?? '1';
  const unidadDesc = opciones.unidadDesc ?? 'UNIDAD ADMINISTRATIVA DEMO';
  const dbfs = path.join(raiz, 'dbfs');
  fs.mkdirSync(dbfs, { recursive: true });
  fs.mkdirSync(path.join(raiz, 'backups'), { recursive: true });
  for (const [nombre, sp] of Object.entries(ESPECIFICACIONES)) crearTabla(path.join(dbfs, nombre + '.DBF'), sp.campos, sp.lang, 64, sp.version);
  const cat = catalogosIncluidos();
  const llenar = (nombre: string, filas: Record<string, unknown>[]) => {
    const t = new DbfTabla(path.join(dbfs, nombre + '.DBF'));
    for (const f of filas) t.agregar(f);
    t.guardar();
  };
  llenar('CODCONT', cat.grupos.map((g) => ({ CODCONT: g.codcont, NOMBRE: g.nombre, VIDAUTIL: Math.trunc(g.vida_util), DEPRECIAR: g.depreciar, ACTUALIZAR: g.actualizar })));
  llenar('ESTADO', cat.estados.map((r) => ({ CODESTADO: r.codigo, NOMESTADO: r.nombre })));
  llenar('BAJA', cat.motivos_baja.map((r) => ({ CODBAJA: r.codigo, DESCBAJA: r.nombre })));
  llenar('ORGANISMO_FIN', cat.organismos_financiadores.map((r) => ({ GESTION: 2013, OF: r.codigo, DES: r.nombre, SIGLA: r.sigla })));
  llenar('CLA_DEPTS', cat.departamentos.map((r) => ({ CODIGO: r.codigo, DESC: r.nombre, SIGLA: r.sigla })));
  llenar('CONFIG', [{ ENTIDAD: entidad, DESCENT: entidadNombre, UNIDAD: unidad, DESCUNI: unidadDesc, USUARIO: 'admin' }]);
  llenar('UNIDADADMIN', [{ ENTIDAD: entidad, UNIDAD: unidad, DESCRIP: unidadDesc, CIUDAD: 'LA PAZ', ESTADOUNI: 1 }]);
  return raiz;
}
