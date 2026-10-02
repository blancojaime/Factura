/** Reportes de Almacenes (Anexos 3, 4 y 5 del Manual y reportes semestrales a Tesoro Municipal). */
import type { Db } from '../core/context.js';
import { fail } from '../core/errors.js';
import { addDays, diffDays, fmtDate, isDate, num, round, today, txt } from '../core/util.js';
import { cfgAll, cfgNum } from '../core/services.js';
import { resumenMov, saldosActuales, ultimoMovimiento } from '../modules/almacenes/stock.js';
import { registrar, sumCol, type Params, type Tabla, type Firma } from './types.js';

const bodsMap = async (db: Db) => new Map((await db('alm_bodegas')).map((b: any) => [b.cod, b.nombre]));
const periodo = (p: Params) => {
  const desde = isDate(p.desde) ? p.desde! : `${today().slice(0, 4)}-01-01`;
  const hasta = isDate(p.hasta) ? p.hasta! : today();
  return { desde, hasta };
};
const bodTxt = async (db: Db, p: Params) => {
  if (!txt(p.bodega) || p.bodega!.toUpperCase() === 'TODAS') return { cod: '', nombre: 'TODAS LAS BODEGAS' };
  const b = await db('alm_bodegas').where({ cod: p.bodega }).orWhere({ nombre: p.bodega }).first();
  if (!b) fail('La bodega no existe.');
  return { cod: b.cod as string, nombre: b.nombre as string };
};
const firmasAlm = async (db: Db): Promise<Firma[]> => {
  const c = await cfgAll(db);
  return [
    { nombre: c.NombreALM, cargo: c.CargoALM, rol: 'ENCARGADO DE ALMACENES' },
    { nombre: c.NombreJBS, cargo: c.CargoJBS, rol: 'Vo.Bo. JEFE DE BIENES Y SERVICIOS' },
  ];
};
const catMap = async (db: Db) => new Map((await db('alm_catalogo')).map((c: any) => [c.codigo, c]));

const PARAMS_PERIODO = [
  { name: 'bodega', label: 'Bodega (o TODAS)', type: 'bodega' as const },
  { name: 'desde', label: 'Desde (fecha)', type: 'date' as const },
  { name: 'hasta', label: 'Hasta (fecha)', type: 'date' as const },
];

registrar(
  {
    id: 'alm-inventario',
    nombre: 'Inventario físico, valorado y consolidado de existencias',
    modulo: 'alm',
    params: [{ name: 'bodega', label: 'Bodega (o TODAS)', type: 'bodega' }],
    async ejecutar(db, p): Promise<Tabla> {
      const b = await bodTxt(db, p);
      const bm = await bodsMap(db);
      const cm = await catMap(db);
      const sal = await saldosActuales(db, b.cod);
      const filas = [...sal.entries()]
        .map(([k, v]) => {
          const [bod, cod] = k.split('|');
          const it: any = cm.get(cod);
          return [bod, bm.get(bod) ?? bod, cod, it?.descripcion, it?.unidad, it?.partida, v.cant, v.cant ? v.bs / v.cant : 0, round(v.bs, 2)];
        })
        .sort((a, c) => String(a[0] + a[2]).localeCompare(String(c[0] + c[2])))
        .map((f, i) => [i + 1, ...f.slice(1)]);
      return {
        titulo: 'Inventario físico, valorado y consolidado de existencias',
        subtitulo: `${b.nombre} · Al ${fmtDate(today())}`,
        landscape: true,
        cols: [
          { header: 'N°', w: 0.5, align: 'center' }, { header: 'Bodega', w: 3 }, { header: 'Código', w: 1.4 }, { header: 'Descripción', w: 4 }, { header: 'Unidad', w: 1 }, { header: 'Partida', w: 0.9 },
          { header: 'Existencia', w: 1, num: 'qty' }, { header: 'P.U. prom. (Bs)', w: 1.1, num: 'money' }, { header: 'Valor (Bs)', w: 1.2, num: 'money' },
        ],
        filas,
        totales: ['', '', '', 'TOTAL', '', '', '', '', sumCol(filas, 8)],
        firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-ingresos',
    nombre: 'Resumen de ingresos de materiales y suministros (Anexo 5)',
    modulo: 'alm',
    params: PARAMS_PERIODO,
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = periodo(p);
      const b = await bodTxt(db, p);
      const bm = await bodsMap(db);
      const q = db('alm_ingresos').where({ estado: 'INGRESADO' }).whereBetween('fecha', [desde, hasta]).orderBy('fecha');
      if (b.cod) q.where({ cod_bod: b.cod });
      const filas = (await q).map((i: any) => [fmtDate(i.fecha), i.nro, bm.get(i.cod_bod), i.tipo, i.proveedor, i.factura, i.nro_oc, i.unidad, num(i.total)]);
      return {
        titulo: 'Resumen de ingresos de materiales y suministros', subtitulo: `${b.nombre} · Del ${fmtDate(desde)} al ${fmtDate(hasta)} · Solo ingresos confirmados`, landscape: true,
        cols: [{ header: 'Fecha', w: 1 }, { header: 'CGI', w: 1.2 }, { header: 'Bodega', w: 2.2 }, { header: 'Tipo', w: 2 }, { header: 'Proveedor', w: 2.4 }, { header: 'Factura', w: 0.9 }, { header: 'O.C.', w: 1 }, { header: 'Unidad solic.', w: 2 }, { header: 'Total (Bs)', w: 1.1, num: 'money' }],
        filas, totales: ['', '', '', '', '', '', '', 'TOTAL', sumCol(filas, 8)], firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-salidas',
    nombre: 'Resumen de salidas de materiales y suministros (Anexo 4)',
    modulo: 'alm',
    params: [...PARAMS_PERIODO, { name: 'unidad', label: 'Unidad solicitante (opcional)', type: 'text' }, { name: 'proyecto', label: 'Proyecto / destino (opcional)', type: 'text' }],
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = periodo(p);
      const b = await bodTxt(db, p);
      const bm = await bodsMap(db);
      const q = db('alm_salidas').where({ estado: 'ENTREGADO' }).whereBetween('fecha_pedido', [desde, hasta]).orderBy('fecha_pedido');
      if (b.cod) q.where({ cod_bod: b.cod });
      if (txt(p.unidad)) q.where({ unidad: p.unidad });
      if (txt(p.proyecto)) q.where({ proyecto: p.proyecto });
      const filas = (await q).map((s: any) => [fmtDate(s.fecha_pedido), s.nro, bm.get(s.cod_bod), s.unidad, s.solicitante, s.proyecto, num(s.total)]);
      return {
        titulo: 'Resumen de salidas de materiales y suministros', subtitulo: `${b.nombre} · Del ${fmtDate(desde)} al ${fmtDate(hasta)} · Solo vales entregados`, landscape: true,
        cols: [{ header: 'Fecha', w: 1 }, { header: 'Vale', w: 1.2 }, { header: 'Bodega', w: 2.2 }, { header: 'Unidad solicitante', w: 2.6 }, { header: 'Solicitante', w: 2.2 }, { header: 'Proyecto / destino', w: 3 }, { header: 'Total (Bs)', w: 1.1, num: 'money' }],
        filas, totales: ['', '', '', '', '', 'TOTAL', sumCol(filas, 6)], firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-por-unidad',
    nombre: 'Salidas por unidad solicitante y/o proyecto (control por destino)',
    modulo: 'alm',
    params: [...PARAMS_PERIODO, { name: 'unidad', label: 'Unidad solicitante (opcional)', type: 'text' }, { name: 'proyecto', label: 'Proyecto / destino (opcional)', type: 'text' }],
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = periodo(p);
      const b = await bodTxt(db, p);
      const q = db('alm_salidas as s').join('alm_salidas_det as d', 'd.nro', 's.nro').where('s.estado', 'ENTREGADO').whereBetween('s.fecha_pedido', [desde, hasta]).where('d.cant_entregada', '>', 0);
      if (b.cod) q.where('s.cod_bod', b.cod);
      if (txt(p.unidad)) q.where('s.unidad', p.unidad);
      if (txt(p.proyecto)) q.where('s.proyecto', p.proyecto);
      const rows = await q.groupBy('s.unidad', 's.proyecto', 'd.cod_item', 'd.descripcion', 'd.unidad').select('s.unidad as uni', 's.proyecto', 'd.cod_item', 'd.descripcion', 'd.unidad as um').sum({ c: 'd.cant_entregada', t: 'd.total' }).orderBy(['s.unidad', 's.proyecto', 'd.cod_item']);
      const filas = rows.map((r: any) => [r.uni, r.proyecto, r.cod_item, r.descripcion, r.um, num(r.c), num(r.t)]);
      return {
        titulo: 'Salidas por unidad solicitante y/o proyecto', subtitulo: `${b.nombre} · Del ${fmtDate(desde)} al ${fmtDate(hasta)}`, landscape: true,
        cols: [{ header: 'Unidad solicitante', w: 2.5 }, { header: 'Proyecto / destino', w: 3 }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 3.5 }, { header: 'Unid.', w: 0.9 }, { header: 'Cantidad', w: 1, num: 'qty' }, { header: 'Importe (Bs)', w: 1.2, num: 'money' }],
        filas, totales: ['', '', '', '', 'TOTAL', '', sumCol(filas, 6)], firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-stock-minimo',
    nombre: 'Existencias bajo stock mínimo (necesidad de reposición)',
    modulo: 'alm',
    params: [{ name: 'bodega', label: 'Bodega (o TODAS)', type: 'bodega' }],
    async ejecutar(db, p): Promise<Tabla> {
      const { calcularReposicion } = await import('../modules/almacenes/otros.js');
      const b = await bodTxt(db, p);
      const rep = await calcularReposicion(db, b.cod || undefined);
      const filas = rep.map((r: any, i: number) => [i + 1, r.cod_item, r.descripcion, r.unidad, r.stock, r.minimo, r.maximo, r.sugerido, r.precio_ref, r.importe]);
      return {
        titulo: 'Existencias bajo stock mínimo', subtitulo: `${b.nombre} · Al ${fmtDate(today())}`, landscape: true,
        cols: [{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.4 }, { header: 'Descripción', w: 4 }, { header: 'Unidad', w: 1 }, { header: 'Stock', w: 0.9, num: 'qty' }, { header: 'Mínimo', w: 0.9, num: 'qty' }, { header: 'Máximo', w: 0.9, num: 'qty' }, { header: 'Sugerido', w: 1, num: 'qty' }, { header: 'P.U. ref.', w: 1, num: 'money' }, { header: 'Importe (Bs)', w: 1.2, num: 'money' }],
        filas, totales: ['', '', '', '', '', '', '', '', 'TOTAL', sumCol(filas, 9)], firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-vencimientos',
    nombre: 'Existencias por vencer y vencidas',
    modulo: 'alm',
    params: [{ name: 'bodega', label: 'Bodega (o TODAS)', type: 'bodega' }],
    async ejecutar(db, p): Promise<Tabla> {
      const b = await bodTxt(db, p);
      const bm = await bodsMap(db);
      const cm = await catMap(db);
      const dias = await cfgNum(db, 'DiasVenc', 90);
      const q = db('alm_lotes').where({ estado: 'ACTIVO' }).where('saldo', '>', 1e-6).whereNotNull('vencimiento').where('vencimiento', '<=', addDays(today(), dias)).orderBy('vencimiento');
      if (b.cod) q.where({ cod_bod: b.cod });
      const filas = (await q).map((l: any) => {
        const d = diffDays(l.vencimiento, today());
        return [bm.get(l.cod_bod), l.cod_item, (cm.get(l.cod_item) as any)?.descripcion, l.id_lote, fmtDate(l.vencimiento), d, d < 0 ? 'VENCIDO' : 'POR VENCER', num(l.saldo), round(num(l.saldo) * num(l.precio_unit), 2)];
      });
      return {
        titulo: 'Existencias por vencer y vencidas', subtitulo: `${b.nombre} · Alerta a ${dias} días · Al ${fmtDate(today())}`, landscape: true,
        cols: [{ header: 'Bodega', w: 2.5 }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 3.5 }, { header: 'Lote', w: 1 }, { header: 'Vencimiento', w: 1.1 }, { header: 'Días', w: 0.7, num: 'int' }, { header: 'Situación', w: 1.1, align: 'center' }, { header: 'Saldo', w: 0.9, num: 'qty' }, { header: 'Valor (Bs)', w: 1.1, num: 'money' }],
        filas, totales: ['', '', '', '', '', '', '', 'TOTAL', sumCol(filas, 8)], firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-sin-movimiento',
    nombre: 'Ítems sin movimiento (candidatos a baja por obsolescencia)',
    modulo: 'alm',
    params: [{ name: 'bodega', label: 'Bodega (o TODAS)', type: 'bodega' }],
    async ejecutar(db, p): Promise<Tabla> {
      const b = await bodTxt(db, p);
      const bm = await bodsMap(db);
      const cm = await catMap(db);
      const dias = await cfgNum(db, 'DiasSinMov', 730);
      const ult = await ultimoMovimiento(db);
      const sal = await saldosActuales(db, b.cod);
      const filas: unknown[][] = [];
      for (const [k, v] of sal) {
        const [bod, cod] = k.split('|');
        const f = ult.get(k);
        const d = f ? diffDays(today(), f) : 99999;
        if (d >= dias) filas.push([bm.get(bod), cod, (cm.get(cod) as any)?.descripcion, f ? fmtDate(f) : '(sin movimiento)', d === 99999 ? '' : d, v.cant, round(v.bs, 2)]);
      }
      return {
        titulo: 'Ítems sin movimiento (obsolescencia)', subtitulo: `${b.nombre} · Sin movimiento por ${dias} días o más`, landscape: true,
        cols: [{ header: 'Bodega', w: 2.5 }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Último mov.', w: 1.2 }, { header: 'Días', w: 0.8, num: 'int' }, { header: 'Existencia', w: 1, num: 'qty' }, { header: 'Valor (Bs)', w: 1.1, num: 'money' }],
        filas, totales: ['', '', '', '', '', 'TOTAL', sumCol(filas, 6)], firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-semestral',
    nombre: 'Informe semestral de movimientos (Tesoro Municipal y Auditoría)',
    modulo: 'alm',
    params: PARAMS_PERIODO,
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = periodo(p);
      const b = await bodTxt(db, p);
      const bm = await bodsMap(db);
      const cm = await catMap(db);
      const res = await resumenMov(db, b.cod, desde, hasta);
      const filas = [...res.values()]
        .map((v) => [bm.get(v.bod), v.cod, (cm.get(v.cod) as any)?.descripcion, v.saldoIniCant, round(v.saldoIniBs, 2), v.entCant, round(v.entBs, 2), v.salCant, round(v.salBs, 2), v.saldoIniCant + v.entCant - v.salCant, round(v.saldoIniBs + v.entBs - v.salBs, 2)])
        .sort((a, c) => String(a[0] + a[1]).localeCompare(String(c[0] + c[1])));
      return {
        titulo: 'Informe semestral de movimientos de almacén', subtitulo: `${b.nombre} · Del ${fmtDate(desde)} al ${fmtDate(hasta)} · Valores en Bs`, landscape: true,
        cols: [{ header: 'Bodega', w: 2.2 }, { header: 'Código', w: 1.2 }, { header: 'Descripción', w: 3 }, { header: 'Saldo ini. cant.', w: 1, num: 'qty' }, { header: 'Saldo ini. Bs', w: 1.1, num: 'money' }, { header: 'Ingresos cant.', w: 1, num: 'qty' }, { header: 'Ingresos Bs', w: 1.1, num: 'money' }, { header: 'Salidas cant.', w: 1, num: 'qty' }, { header: 'Salidas Bs', w: 1.1, num: 'money' }, { header: 'Saldo final cant.', w: 1, num: 'qty' }, { header: 'Saldo final Bs', w: 1.1, num: 'money' }],
        filas, totales: ['', '', 'TOTAL', '', sumCol(filas, 4), '', sumCol(filas, 6), '', sumCol(filas, 8), '', sumCol(filas, 10)], firmas: await firmasAlm(db),
      };
    },
  },
  {
    id: 'alm-por-partida',
    nombre: 'Resumen de existencias por partida presupuestaria (Contabilidad)',
    modulo: 'alm',
    params: [{ name: 'bodega', label: 'Bodega (o TODAS)', type: 'bodega' }],
    async ejecutar(db, p): Promise<Tabla> {
      const b = await bodTxt(db, p);
      const cm = await catMap(db);
      const pm = new Map((await db('core_partidas')).map((x: any) => [x.partida, x.descripcion]));
      const sal = await saldosActuales(db, b.cod);
      const agg = new Map<string, { n: number; bs: number }>();
      for (const [k, v] of sal) {
        const part = txt((cm.get(k.split('|')[1]) as any)?.partida) || '(sin partida)';
        const a = agg.get(part) ?? { n: 0, bs: 0 };
        a.n++;
        a.bs += v.bs;
        agg.set(part, a);
      }
      const filas = [...agg.entries()].sort().map(([part, a]) => [part, pm.get(part) ?? '', a.n, round(a.bs, 2)]);
      return {
        titulo: 'Resumen de existencias por partida presupuestaria', subtitulo: `${b.nombre} · Al ${fmtDate(today())}`,
        cols: [{ header: 'Partida', w: 1 }, { header: 'Descripción', w: 4 }, { header: 'Ítems', w: 0.8, num: 'int' }, { header: 'Valor (Bs)', w: 1.4, num: 'money' }],
        filas, totales: ['', 'TOTAL', sumCol(filas, 2), sumCol(filas, 3)],
        firmas: [{ nombre: (await cfgAll(db)).NombreALM, cargo: (await cfgAll(db)).CargoALM, rol: 'ENCARGADO DE ALMACENES' }, { nombre: (await cfgAll(db)).NombreCON, cargo: (await cfgAll(db)).CargoCON, rol: 'CONTABILIDAD' }],
      };
    },
  },
  {
    id: 'alm-catalogo',
    nombre: 'Catálogo general de materiales y suministros',
    modulo: 'alm',
    params: [{ name: 'bodega', label: 'Bodega (o TODAS)', type: 'bodega' }],
    async ejecutar(db, p): Promise<Tabla> {
      const b = await bodTxt(db, p);
      const bm = await bodsMap(db);
      const q = db('alm_catalogo').orderBy('codigo');
      if (b.cod) q.where({ cod_bod: b.cod });
      const filas = (await q).map((c: any, i: number) => [i + 1, c.codigo, c.descripcion, c.unidad, c.partida, bm.get(c.cod_bod), c.stock_min, c.stock_max, c.perecible, c.ubicacion, c.estado]);
      return {
        titulo: 'Catálogo general de materiales y suministros', subtitulo: `${b.nombre} · Al ${fmtDate(today())}`, landscape: true,
        cols: [{ header: 'N°', w: 0.5, align: 'center' }, { header: 'Código', w: 1.3 }, { header: 'Descripción', w: 4 }, { header: 'Unidad', w: 1 }, { header: 'Partida', w: 0.9 }, { header: 'Bodega', w: 2.4 }, { header: 'Mín.', w: 0.6, num: 'qty' }, { header: 'Máx.', w: 0.6, num: 'qty' }, { header: 'Perec.', w: 0.7, align: 'center' }, { header: 'Ubicación', w: 1.2 }, { header: 'Estado', w: 0.9 }],
        filas,
      };
    },
  },
  {
    id: 'alm-bitacora',
    nombre: 'Bitácora de operaciones del sistema (auditoría)',
    modulo: 'alm',
    params: [{ name: 'desde', label: 'Desde (fecha)', type: 'date' }, { name: 'hasta', label: 'Hasta (fecha)', type: 'date' }, { name: 'modulo', label: 'Módulo', type: 'select', options: ['', 'ALMACENES', 'COMBUSTIBLE', 'ACTIVOS FIJOS', 'SEGURIDAD'] }],
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = periodo(p);
      const q = db('core_bitacora').where('fecha', '>=', desde).where('fecha', '<=', hasta + ' 23:59:59').orderBy('id', 'desc').limit(5000);
      if (txt(p.modulo)) q.where({ modulo: p.modulo });
      const filas = (await q).map((x: any) => [x.fecha, x.usuario, x.modulo, x.accion, x.documento, x.detalle]);
      return {
        titulo: 'Bitácora de operaciones del sistema', subtitulo: `Del ${fmtDate(desde)} al ${fmtDate(hasta)}${txt(p.modulo) ? ' · ' + p.modulo : ''}`, landscape: true,
        cols: [{ header: 'Fecha y hora', w: 1.5 }, { header: 'Usuario', w: 1.5 }, { header: 'Módulo', w: 1.3 }, { header: 'Acción', w: 2.2 }, { header: 'Documento', w: 1.5 }, { header: 'Detalle', w: 4 }],
        filas,
      };
    },
  },
);
void sumCol;
