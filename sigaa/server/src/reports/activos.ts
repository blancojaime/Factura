/** Reportes de Activos Fijos: informe a Contabilidad, inventarios por funcionario/ubicación, resumen por cuenta, incompletos. */
import type { Db } from '../core/context.js';
import { fail } from '../core/errors.js';
import { fmtDate, isDate, num, round, today, txt, addDays } from '../core/util.js';
import { cfgAll } from '../core/services.js';
import { depreciacion } from '../modules/activos/service.js';
import { registrar, sumCol, type Params, type Tabla } from './types.js';

const base = (a: any) => [a.codigo, a.descripcion, a.auxiliar, a.marca, a.modelo, a.serie, a.estado, num(a.valor)];
const COLS_ACT = [{ header: 'Código', w: 1.5 }, { header: 'Descripción', w: 3.5 }, { header: 'Auxiliar', w: 2 }, { header: 'Marca', w: 1.2 }, { header: 'Modelo', w: 1.2 }, { header: 'Serie', w: 1.2 }, { header: 'Estado', w: 0.9 }, { header: 'Valor Bs', w: 1.1, num: 'money' as const }];

registrar(
  {
    id: 'af-contabilidad',
    nombre: 'Informe de movimientos a Contabilidad (semanal — Procedimiento 5)',
    modulo: 'af',
    params: [{ name: 'desde', label: 'Desde (fecha)', type: 'date' }, { name: 'hasta', label: 'Hasta (fecha)', type: 'date' }],
    async ejecutar(db, p): Promise<Tabla> {
      const hasta = isDate(p.hasta) ? p.hasta! : today();
      const desde = isDate(p.desde) ? p.desde! : addDays(hasta, -4);
      if (hasta < desde) fail('La fecha HASTA no puede ser anterior a la fecha DESDE.');
      const rows = await db('af_movimientos as m').join('af_activos as a', 'a.codigo', 'm.codigo').leftJoin('af_cuentas as c', 'c.id_cta', 'a.id_cta').whereBetween('m.fecha', [desde, hasta]).select('m.*', 'a.descripcion', 'a.valor', 'a.auxiliar', 'c.cuenta', 'c.partida').orderBy(['m.tipo', 'm.fecha', 'm.codigo']);
      const filas = (rows as any[]).map((m) => [m.tipo, fmtDate(m.fecha), m.documento, m.codigo, `${m.auxiliar ?? ''} - ${m.descripcion}`, m.cuenta, num(m.valor), m.origen, m.destino]);
      const resumen = new Map<string, { n: number; v: number }>();
      for (const m of rows as any[]) {
        const a = resumen.get(m.tipo) ?? { n: 0, v: 0 };
        a.n++; a.v += num(m.valor);
        resumen.set(m.tipo, a);
      }
      const fr = [...resumen.entries()].map(([k, a]) => [k, a.n, round(a.v, 2)]);
      const c = await cfgAll(db);
      return {
        titulo: 'Informe de movimientos de activos fijos', subtitulo: `Del ${fmtDate(desde)} al ${fmtDate(hasta)} · Para: ${c.NombreContab ?? c.NombreCON}, ${c.CargoCON}`, unidad: 'UnidadAF', landscape: true,
        cols: [{ header: 'Movimiento', w: 1.6 }, { header: 'Fecha', w: 1 }, { header: 'Documento', w: 1.2 }, { header: 'Código', w: 1.4 }, { header: 'Activo', w: 3.4 }, { header: 'Cuenta contable', w: 2.2 }, { header: 'Valor Bs', w: 1, num: 'money' }, { header: 'Origen', w: 1.8 }, { header: 'Destino', w: 1.8 }],
        filas, totales: ['TOTAL', '', '', '', '', '', sumCol(filas, 6), '', ''],
        extra: [{ titulo: 'Resumen por tipo de movimiento', cols: [{ header: 'Movimiento', w: 3 }, { header: 'Cantidad', w: 1, num: 'int' }, { header: 'Valor Bs', w: 1.2, num: 'money' }], filas: fr, totales: ['TOTAL', sumCol(fr, 1), sumCol(fr, 2)] }],
        firmas: [{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }, { nombre: c.NombreCON, cargo: c.CargoCON, rol: 'RECIBE — CONTABILIDAD' }],
      };
    },
  },
  {
    id: 'af-inv-funcionario',
    nombre: 'Inventario de activos por funcionario',
    modulo: 'af',
    params: [{ name: 'funcionario', label: 'Funcionario', type: 'funcionario' }],
    async ejecutar(db, p): Promise<Tabla> {
      if (!txt(p.funcionario)) fail('Seleccione el funcionario.');
      const f = await db('core_funcionarios').where({ nombre: p.funcionario }).first();
      const rows = (await db('af_activos').where({ situacion: 'ASIGNADO', funcionario: p.funcionario }).orderBy('codigo')) as any[];
      const filas = rows.map(base);
      const c = await cfgAll(db);
      return {
        titulo: 'Inventario de activos fijos asignados', subtitulo: `${p.funcionario} — ${txt(f?.cargo)} (${txt(f?.unidad)}) · CI ${txt(f?.ci)} · Al ${fmtDate(today())}`, unidad: 'UnidadAF', landscape: true,
        cols: COLS_ACT, filas, totales: ['TOTAL', '', '', '', '', '', '', sumCol(filas, 7)],
        nota: 'El servidor público declara haber recibido los activos fijos detallados y se compromete a su custodia y buen uso (Reglamento de Manejo de Bienes).',
        firmas: [{ nombre: p.funcionario, cargo: txt(f?.cargo), rol: 'SERVIDOR PÚBLICO' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }],
      };
    },
  },
  {
    id: 'af-inv-ubicacion',
    nombre: 'Inventario de activos por edificio / ambiente',
    modulo: 'af',
    params: [{ name: 'cod_edif', label: 'Edificio', type: 'edificio' }, { name: 'cod_amb', label: 'Ambiente (opcional, código)', type: 'text' }],
    async ejecutar(db, p): Promise<Tabla> {
      if (!txt(p.cod_edif)) fail('Seleccione el edificio.');
      const e = await db('af_edificios').where({ cod_edif: Number(p.cod_edif) }).first();
      if (!e) fail('El edificio no existe.');
      const q = db('af_activos as a').leftJoin('af_ambientes as m', (j) => j.on('m.cod_edif', 'a.edif_actual').andOn('m.cod_amb', 'a.amb_actual')).where('a.edif_actual', e.cod_edif).whereNot('a.situacion', 'BAJA').select('a.*', 'm.ambiente').orderBy(['a.amb_actual', 'a.codigo']);
      if (txt(p.cod_amb)) q.where('a.amb_actual', Number(p.cod_amb));
      const rows = (await q) as any[];
      const filas = rows.map((a) => [a.ambiente, ...base(a), a.funcionario]);
      const c = await cfgAll(db);
      return {
        titulo: 'Inventario de activos fijos por ubicación', subtitulo: `${e.edificio}${txt(p.cod_amb) ? ' · Ambiente ' + p.cod_amb : ''} · Responsable: ${e.responsable ?? ''} · Al ${fmtDate(today())}`, unidad: 'UnidadAF', landscape: true,
        cols: [{ header: 'Ambiente', w: 1.8 }, ...COLS_ACT, { header: 'Funcionario', w: 2 }], filas, totales: ['TOTAL', '', '', '', '', '', '', '', sumCol(filas, 8), ''],
        firmas: [{ nombre: e.responsable, cargo: 'RESPONSABLE DEL ESTABLECIMIENTO', rol: 'RESPONSABLE' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }],
      };
    },
  },
  {
    id: 'af-resumen-cuentas',
    nombre: 'Resumen por cuenta contable (cantidad, valor y depreciación estimada)',
    modulo: 'af',
    params: [],
    async ejecutar(db): Promise<Tabla> {
      const cuentas = (await db('af_cuentas').orderBy('id_cta')) as any[];
      const acts = (await db('af_activos').whereNot({ situacion: 'BAJA' })) as any[];
      const filas = cuentas
        .map((c) => {
          const a = acts.filter((x) => x.id_cta === c.id_cta);
          const val = a.reduce((t, x) => t + num(x.valor), 0);
          const dep = a.reduce((t, x) => t + depreciacion(num(x.valor), num(c.vida_util), x.fecha_ingreso ?? x.fecha_codif).acumulada, 0);
          return [String(c.id_cta).padStart(2, '0'), c.cuenta, c.partida, c.vida_util, a.length, a.filter((x) => x.situacion === 'ASIGNADO').length, a.filter((x) => x.situacion === 'EN ALMACEN').length, round(val, 2), round(dep, 2), round(val - dep, 2)];
        })
        .filter((f) => Number(f[4]) > 0);
      return {
        titulo: 'Resumen de activos fijos por cuenta contable', subtitulo: `Al ${fmtDate(today())} · Depreciación estimada por línea recta (vida útil de la cuenta)`, unidad: 'UnidadAF', landscape: true,
        cols: [{ header: 'Cta.', w: 0.6, align: 'center' }, { header: 'Cuenta contable', w: 3.5 }, { header: 'Partida', w: 0.9 }, { header: 'Vida útil', w: 0.8, num: 'int' }, { header: 'Cant.', w: 0.7, num: 'int' }, { header: 'Asignados', w: 0.9, num: 'int' }, { header: 'En almacén', w: 0.9, num: 'int' }, { header: 'Valor Bs', w: 1.2, num: 'money' }, { header: 'Deprec. acum.', w: 1.2, num: 'money' }, { header: 'Valor neto', w: 1.2, num: 'money' }],
        filas, totales: ['', 'TOTAL', '', '', sumCol(filas, 4), sumCol(filas, 5), sumCol(filas, 6), sumCol(filas, 7), sumCol(filas, 8), sumCol(filas, 9)],
      };
    },
  },
  {
    id: 'af-kardex',
    nombre: 'Kardex (historial) de un activo',
    modulo: 'af',
    params: [{ name: 'codigo', label: 'Código del activo', type: 'text' }],
    async ejecutar(db, p): Promise<Tabla> {
      if (!txt(p.codigo)) fail('Escriba el código del activo.');
      const a = await db('af_activos').where({ codigo: p.codigo }).first();
      if (!a) fail(`No existe el activo ${p.codigo}.`);
      const filas = ((await db('af_movimientos').where({ codigo: p.codigo }).orderBy(['fecha', 'id'])) as any[]).map((m) => [fmtDate(m.fecha), m.tipo, m.documento, m.origen, m.destino, m.detalle, m.usuario]);
      return {
        titulo: 'Kardex del activo fijo', subtitulo: `${a.codigo} — ${a.auxiliar}: ${a.descripcion} · Valor Bs ${num(a.valor).toFixed(2)} · ${a.situacion}`, unidad: 'UnidadAF', landscape: true,
        cols: [{ header: 'Fecha', w: 1 }, { header: 'Movimiento', w: 1.8 }, { header: 'Documento', w: 1.3 }, { header: 'Origen', w: 2.2 }, { header: 'Destino', w: 2.2 }, { header: 'Detalle', w: 3 }, { header: 'Usuario', w: 1 }],
        filas,
      };
    },
  },
  {
    id: 'af-incompletos',
    nombre: 'Activos con registro incompleto (sin ficha técnica o sin fotografía)',
    modulo: 'af',
    params: [],
    async ejecutar(db): Promise<Tabla> {
      const rows = (await db('af_activos').whereNot({ situacion: 'BAJA' }).orderBy('codigo')) as any[];
      const filas = rows
        .map((a) => {
          const falta: string[] = [];
          if (!txt(a.marca)) falta.push('marca');
          if (!txt(a.modelo)) falta.push('modelo');
          if (!txt(a.serie)) falta.push('serie');
          if (!txt(a.c01)) falta.push('ficha técnica');
          if (!txt(a.foto1)) falta.push('fotografía');
          return [a.codigo, a.descripcion, a.auxiliar, a.funcionario, falta.join(', ')];
        })
        .filter((f) => f[4]);
      return {
        titulo: 'Activos fijos con registro incompleto', subtitulo: `Al ${fmtDate(today())} · ${filas.length} de ${rows.length} activos`, unidad: 'UnidadAF', landscape: true,
        cols: [{ header: 'Código', w: 1.5 }, { header: 'Descripción', w: 4 }, { header: 'Auxiliar', w: 2 }, { header: 'Funcionario', w: 2.5 }, { header: 'Datos faltantes', w: 3 }],
        filas,
      };
    },
  },
  {
    id: 'af-inventario-general',
    nombre: 'Inventario general de activos fijos (exportación completa)',
    modulo: 'af',
    params: [{ name: 'situacion', label: 'Situación', type: 'select', options: ['TODAS', 'EN ALMACEN', 'ASIGNADO', 'BAJA'] }],
    async ejecutar(db, p): Promise<Tabla> {
      const q = db('af_activos as a').leftJoin('af_cuentas as c', 'c.id_cta', 'a.id_cta').leftJoin('af_edificios as e', 'e.cod_edif', 'a.edif_actual').leftJoin('af_ambientes as m', (j) => j.on('m.cod_edif', 'a.edif_actual').andOn('m.cod_amb', 'a.amb_actual')).select('a.*', 'c.cuenta', 'c.partida', 'e.edificio', 'm.ambiente').orderBy('a.codigo');
      if (txt(p.situacion) && p.situacion !== 'TODAS') q.where('a.situacion', p.situacion);
      const filas = ((await q) as any[]).map((a) => [a.codigo, a.cuenta, a.partida, a.auxiliar, a.descripcion, a.marca, a.modelo, a.serie, a.color, a.estado, num(a.valor), fmtDate(a.fecha_ingreso), a.situacion, a.funcionario, a.edificio, a.ambiente, a.nro_ingreso, a.nro_acta]);
      return {
        titulo: 'Inventario general de activos fijos', subtitulo: `Al ${fmtDate(today())}`, unidad: 'UnidadAF', landscape: true,
        cols: [{ header: 'Código', w: 1.4 }, { header: 'Cuenta', w: 2 }, { header: 'Partida', w: 0.8 }, { header: 'Auxiliar', w: 1.6 }, { header: 'Descripción', w: 3 }, { header: 'Marca', w: 1 }, { header: 'Modelo', w: 1 }, { header: 'Serie', w: 1 }, { header: 'Color', w: 0.8 }, { header: 'Estado', w: 0.8 }, { header: 'Valor Bs', w: 1, num: 'money' }, { header: 'F. ingreso', w: 1 }, { header: 'Situación', w: 1 }, { header: 'Funcionario', w: 1.8 }, { header: 'Edificio', w: 1.8 }, { header: 'Ambiente', w: 1.4 }, { header: 'Ingreso', w: 1.2 }, { header: 'Acta', w: 1.2 }],
        filas, totales: ['TOTAL', '', '', '', '', '', '', '', '', '', sumCol(filas, 10), '', '', '', '', '', '', ''],
      };
    },
  },
);
