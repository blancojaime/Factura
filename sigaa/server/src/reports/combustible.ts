/** Reportes de Combustible: existencias, kardex, emisiones, consumo, contratos, rendimiento, pendientes, cronograma, viajes e informe mensual. */
import type { Db } from '../core/context.js';
import { addDays, fmtDate, fmt2, isDate, literal, MESES, num, round, today, txt, month, year } from '../core/util.js';
import { cfgAll, cfgNum } from '../core/services.js';
import { saldoTurril, costoPromTurril } from '../modules/combustible/base.js';
import { registrar, sumCol, type Params, type Tabla, type Firma } from './types.js';

const per = (p: Params) => ({ desde: isDate(p.desde) ? p.desde! : `${today().slice(0, 7)}-01`, hasta: isDate(p.hasta) ? p.hasta! : today() });
const PARAMS = [
  { name: 'desde', label: 'Fecha desde', type: 'date' as const },
  { name: 'hasta', label: 'Fecha hasta', type: 'date' as const },
  { name: 'combustible', label: 'Combustible (opcional)', type: 'select' as const, options: ['', 'Gasolina', 'Diésel', 'GNV'] },
  { name: 'placa', label: 'Placa (opcional)', type: 'text' as const },
  { name: 'puesto', label: 'Puesto de turriles (opcional)', type: 'text' as const },
];
const firmas = async (db: Db): Promise<Firma[]> => {
  const c = await cfgAll(db);
  return [{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE COMBUSTIBLE' }, { nombre: c.NombreSEC, cargo: c.CargoSEC, rol: 'AUTORIZA' }];
};
const sub = (p: Params, d: string, h: string) => `Del ${fmtDate(d)} al ${fmtDate(h)}${txt(p.combustible) ? ' · ' + p.combustible : ''}${txt(p.placa) ? ' · ' + p.placa : ''}${txt(p.puesto) ? ' · ' + p.puesto : ''}`;

async function emisiones(db: Db, p: Params) {
  const { desde, hasta } = per(p);
  const q = db('com_emisiones').whereNot({ estado: 'Anulado' }).whereBetween('fecha', [desde, hasta]).orderBy('nro');
  if (txt(p.combustible)) q.whereRaw('lower(combustible) = ?', [p.combustible!.toLowerCase()]);
  if (txt(p.placa)) q.where({ placa: p.placa });
  return { rows: await q, desde, hasta };
}

registrar(
  {
    id: 'com-existencias',
    nombre: 'Existencias de vales y combustible en turriles',
    modulo: 'com',
    params: [],
    async ejecutar(db): Promise<Tabla> {
      const rows = await db('com_vales').groupBy('combustible', 'corte', 'estado').select('combustible', 'corte', 'estado').count({ n: '*' });
      const m = new Map<string, Record<string, number>>();
      for (const r of rows as any[]) {
        const k = `${r.combustible}|${r.corte}`;
        const o = m.get(k) ?? {};
        o[r.estado] = Number(r.n);
        m.set(k, o);
      }
      const filas = [...m.entries()].sort().map(([k, o]) => {
        const [comb, corte] = k.split('|');
        const c = Number(corte);
        const g = (e: string) => o[e] ?? 0;
        return [comb, c, g('Disponible'), g('Disponible') * c, g('Entregado'), g('Entregado') * c, g('Utilizado'), g('Utilizado') * c, g('Anulado') + g('Vencido') + g('Extraviado')];
      });
      const puestos = await db('com_puestos');
      const tur: unknown[][] = [];
      for (const pt of puestos) {
        const s = await saldoTurril(db, pt.codigo);
        const cu = await costoPromTurril(db, pt.codigo);
        tur.push([pt.codigo, pt.nombre, pt.combustible, num(pt.capacidad_l), s, cu, round(s * cu, 2)]);
      }
      return {
        titulo: 'Existencias de vales de combustible', subtitulo: `Al ${fmtDate(today())}`, unidad: 'combustible', landscape: true,
        cols: [{ header: 'Combustible', w: 1.5 }, { header: 'Corte Bs', w: 0.8, num: 'int' }, { header: 'Disponibles', w: 1, num: 'int' }, { header: 'Importe disp. Bs', w: 1.3, num: 'money' }, { header: 'Entregados', w: 1, num: 'int' }, { header: 'Importe entreg. Bs', w: 1.3, num: 'money' }, { header: 'Utilizados', w: 1, num: 'int' }, { header: 'Importe util. Bs', w: 1.3, num: 'money' }, { header: 'Bajas', w: 0.8, num: 'int' }],
        filas, totales: ['TOTAL', '', sumCol(filas, 2), sumCol(filas, 3), sumCol(filas, 4), sumCol(filas, 5), sumCol(filas, 6), sumCol(filas, 7), sumCol(filas, 8)],
        extra: [{ titulo: 'Combustible en turriles (puestos)', cols: [{ header: 'Puesto', w: 1 }, { header: 'Nombre', w: 3 }, { header: 'Combustible', w: 1.2 }, { header: 'Capacidad L', w: 1.2, num: 'qty' }, { header: 'Saldo L', w: 1.2, num: 'qty' }, { header: 'Costo prom. Bs/L', w: 1.3, num: 'money' }, { header: 'Saldo Bs', w: 1.3, num: 'money' }], filas: tur, totales: ['TOTAL', '', '', '', sumCol(tur, 4), '', sumCol(tur, 6)] }],
        firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-kardex',
    nombre: 'Kardex general de vales',
    modulo: 'com',
    params: PARAMS,
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = per(p);
      const q = db('com_kardex').where('almacen', 'VALES').whereBetween('fecha', [desde, hasta]).orderBy(['item', 'fecha', 'id']);
      if (txt(p.combustible)) q.whereRaw('upper(item) like ?', [`%${p.combustible!.toUpperCase()}%`]);
      const rows = await q;
      const saldo = new Map<string, number>();
      const filas = rows.map((r: any) => {
        const s = (saldo.get(r.item) ?? 0) + num(r.entrada) - num(r.salida);
        saldo.set(r.item, s);
        return [r.item, fmtDate(r.fecha), r.tipo, r.documento, r.placa, r.detalle, num(r.entrada), num(r.salida), s, num(r.importe_entrada) - num(r.importe_salida)];
      });
      return {
        titulo: 'Kardex general de vales de combustible', subtitulo: sub(p, desde, hasta), unidad: 'combustible', landscape: true,
        cols: [{ header: 'Ítem', w: 2 }, { header: 'Fecha', w: 1 }, { header: 'Tipo', w: 1.1 }, { header: 'Documento', w: 1.3 }, { header: 'Placa', w: 1 }, { header: 'Detalle', w: 3.5 }, { header: 'Entrada', w: 0.9, num: 'int' }, { header: 'Salida', w: 0.9, num: 'int' }, { header: 'Saldo', w: 0.9, num: 'int' }, { header: 'Importe Bs', w: 1.1, num: 'money' }],
        filas, totales: ['TOTALES', '', '', '', '', '', sumCol(filas, 6), sumCol(filas, 7), '', sumCol(filas, 9)], firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-emisiones',
    nombre: 'Detalle de emisiones de vales',
    modulo: 'com',
    params: PARAMS,
    async ejecutar(db, p): Promise<Tabla> {
      const { rows, desde, hasta } = await emisiones(db, p);
      const filas = rows.map((e: any) => [e.nro, fmtDate(e.fecha), e.placa, e.conductor, e.unidad, e.apertura, `${fmtDate(e.desde)} - ${fmtDate(e.hasta)}`, num(e.cant_vales), num(e.monto), num(e.litros), e.estado]);
      const porPlaca = new Map<string, { n: number; v: number; m: number; l: number; d: string }>();
      const porUnidad = new Map<string, { n: number; v: number; m: number; l: number }>();
      for (const e of rows as any[]) {
        const a = porPlaca.get(e.placa) ?? { n: 0, v: 0, m: 0, l: 0, d: e.descripcion_destino };
        a.n++; a.v += num(e.cant_vales); a.m += num(e.monto); a.l += num(e.litros);
        porPlaca.set(e.placa, a);
        const u = porUnidad.get(e.unidad) ?? { n: 0, v: 0, m: 0, l: 0 };
        u.n++; u.v += num(e.cant_vales); u.m += num(e.monto); u.l += num(e.litros);
        porUnidad.set(e.unidad, u);
      }
      const totM = sumCol(filas, 8);
      const fv = [...porPlaca.entries()].map(([k, a]) => [k, a.n, a.v, round(a.m, 2), round(a.l, 2), a.d]);
      const fu = [...porUnidad.entries()].map(([k, a]) => [k, a.n, a.v, round(a.m, 2), round(a.l, 2), totM ? round((a.m / totM) * 100, 1) : 0]);
      return {
        titulo: 'Detalle de emisiones de vales de combustible', subtitulo: sub(p, desde, hasta), unidad: 'combustible', landscape: true,
        cols: [{ header: 'Nº Emisión', w: 1.3 }, { header: 'Fecha', w: 1 }, { header: 'Placa / Puesto', w: 1.1 }, { header: 'Conductor', w: 2.2 }, { header: 'Unidad', w: 2.4 }, { header: 'Apertura', w: 1 }, { header: 'Periodo', w: 1.8 }, { header: 'Vales', w: 0.6, num: 'int' }, { header: 'Monto Bs', w: 1, num: 'money' }, { header: 'Litros', w: 0.9, num: 'money' }, { header: 'Estado', w: 1 }],
        filas, totales: ['TOTAL', '', '', '', '', '', '', sumCol(filas, 7), totM, sumCol(filas, 9), ''],
        extra: [
          { titulo: 'Resumen por vehículo / puesto', cols: [{ header: 'Placa / Puesto', w: 1.4 }, { header: 'Emisiones', w: 0.9, num: 'int' }, { header: 'Vales', w: 0.8, num: 'int' }, { header: 'Monto Bs', w: 1.2, num: 'money' }, { header: 'Litros', w: 1, num: 'money' }, { header: 'Descripción', w: 3 }], filas: fv, totales: ['TOTAL', sumCol(fv, 1), sumCol(fv, 2), sumCol(fv, 3), sumCol(fv, 4), ''] },
          { titulo: 'Por unidad / área solicitante', cols: [{ header: 'Unidad', w: 3 }, { header: 'Emisiones', w: 0.9, num: 'int' }, { header: 'Vales', w: 0.8, num: 'int' }, { header: 'Monto Bs', w: 1.2, num: 'money' }, { header: 'Litros', w: 1, num: 'money' }, { header: '% del total', w: 0.9, num: 'money' }], filas: fu, totales: ['TOTAL', sumCol(fu, 1), sumCol(fu, 2), sumCol(fu, 3), sumCol(fu, 4), 100] },
        ],
        firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-consumo',
    nombre: 'Consumo y ejecución por apertura programática',
    modulo: 'com',
    params: PARAMS,
    async ejecutar(db, p): Promise<Tabla> {
      const { rows, desde, hasta } = await emisiones(db, p);
      const aperturas = await db('core_aperturas');
      const ej = new Map<string, { m: number; l: number; n: number }>();
      for (const e of rows as any[]) {
        const a = ej.get(e.apertura) ?? { m: 0, l: 0, n: 0 };
        a.m += num(e.monto); a.l += num(e.litros); a.n++;
        ej.set(e.apertura, a);
      }
      const filas = aperturas.map((a: any) => {
        const x = ej.get(a.apertura) ?? { m: 0, l: 0, n: 0 };
        return [`${a.apertura} - ${a.descripcion ?? ''}`, num(a.presupuesto), round(x.m, 2), num(a.presupuesto) ? round((x.m / num(a.presupuesto)) * 100, 1) : 0, round(x.l, 2), x.n];
      });
      return {
        titulo: 'Consumo de combustible por apertura programática', subtitulo: sub(p, desde, hasta), unidad: 'combustible',
        cols: [{ header: 'Apertura - Descripción', w: 4 }, { header: 'Presupuesto Bs', w: 1.3, num: 'money' }, { header: 'Ejecutado Bs', w: 1.3, num: 'money' }, { header: '% Ejecución', w: 1, num: 'money' }, { header: 'Litros', w: 1, num: 'money' }, { header: 'Emisiones', w: 0.9, num: 'int' }],
        filas, totales: ['TOTAL', sumCol(filas, 1), sumCol(filas, 2), '', sumCol(filas, 4), sumCol(filas, 5)], firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-turriles',
    nombre: 'Kardex de combustible en turriles',
    modulo: 'com',
    params: PARAMS,
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = per(p);
      const q = db('com_kardex').whereNot('almacen', 'VALES').whereBetween('fecha', [desde, hasta]).orderBy(['almacen', 'fecha', 'id']);
      if (txt(p.puesto)) q.where({ almacen: p.puesto });
      const saldo = new Map<string, number>();
      const filas = (await q).map((r: any) => {
        const s = (saldo.get(r.almacen) ?? 0) + num(r.entrada) - num(r.salida);
        saldo.set(r.almacen, s);
        return [r.almacen, fmtDate(r.fecha), r.tipo, r.documento, r.placa, r.detalle, num(r.entrada), num(r.salida), round(s, 2), num(r.costo_unit)];
      });
      return {
        titulo: 'Kardex de combustible en turriles', subtitulo: sub(p, desde, hasta), unidad: 'combustible', landscape: true,
        cols: [{ header: 'Puesto', w: 0.9 }, { header: 'Fecha', w: 1 }, { header: 'Tipo', w: 1 }, { header: 'Documento', w: 1.3 }, { header: 'Placa', w: 1 }, { header: 'Detalle', w: 3.5 }, { header: 'Ingreso L', w: 1, num: 'money' }, { header: 'Despacho L', w: 1, num: 'money' }, { header: 'Saldo L', w: 1, num: 'money' }, { header: 'Costo Bs/L', w: 1, num: 'money' }],
        filas, totales: ['TOTALES', '', '', '', '', '', sumCol(filas, 6), sumCol(filas, 7), '', ''], firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-contratos',
    nombre: 'Contratos de provisión de combustible',
    modulo: 'com',
    params: [],
    async ejecutar(db): Promise<Tabla> {
      const filas = (await db('com_contratos').orderBy('nro')).map((c: any) => [c.nro, c.proveedor, c.modalidad, c.combustible, fmtDate(c.vigencia_desde), fmtDate(c.vigencia_hasta), num(c.monto), num(c.recibido), num(c.saldo), num(c.monto) ? round((num(c.recibido) / num(c.monto)) * 100, 1) : 0, c.estado]);
      return {
        titulo: 'Contratos de provisión de combustible', subtitulo: `Al ${fmtDate(today())}`, unidad: 'combustible', landscape: true,
        cols: [{ header: 'Nº Contrato', w: 1.8 }, { header: 'Proveedor', w: 3 }, { header: 'Modalidad', w: 1 }, { header: 'Combustible', w: 1.1 }, { header: 'Desde', w: 1 }, { header: 'Hasta', w: 1 }, { header: 'Monto Bs', w: 1.2, num: 'money' }, { header: 'Recibido Bs', w: 1.2, num: 'money' }, { header: 'Saldo Bs', w: 1.2, num: 'money' }, { header: '% ejec.', w: 0.8, num: 'money' }, { header: 'Estado', w: 0.9 }],
        filas, totales: ['TOTAL', '', '', '', '', '', sumCol(filas, 6), sumCol(filas, 7), sumCol(filas, 8), '', ''], firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-rendimiento',
    nombre: 'Rendimiento de vehículos y maquinaria (según descargos)',
    modulo: 'com',
    params: PARAMS,
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = per(p);
      const q = db('com_descargos').whereBetween('fecha', [desde, hasta]).orderBy('placa');
      if (txt(p.placa)) q.where({ placa: p.placa });
      const rows = await q;
      const vm = new Map((await db('com_vehiculos')).map((v: any) => [v.placa, v]));
      const g = new Map<string, { n: number; rec: number; lit: number; obs: number; ref: number; med: string }>();
      for (const d of rows as any[]) {
        const a = g.get(d.placa) ?? { n: 0, rec: 0, lit: 0, obs: 0, ref: num(d.rendimiento_ref), med: d.medidor };
        a.n++; a.rec += num(d.recorrido); a.lit += num(d.litros); if (d.estado === 'Observado') a.obs++;
        g.set(d.placa, a);
      }
      const filas = [...g.entries()].map(([pl, a]) => {
        const real = a.rec > 0 ? a.lit / a.rec : 0;
        const dev = a.ref && real ? real / a.ref - 1 : 0;
        const v: any = vm.get(pl);
        return [pl, `${txt(v?.tipo)} ${txt(v?.marca)}`.trim(), a.n, round(a.rec, 1), a.med, round(a.lit, 2), round(real, 3), a.ref, round(dev * 100, 1), a.obs, a.obs ? 'REVISAR' : 'CONFORME'];
      });
      const det = (rows as any[]).map((d) => [d.nro, d.conductor, fmtDate(d.fecha), num(d.recorrido), d.placa, num(d.litros), num(d.rendimiento_real), num(d.rendimiento_ref), num(d.desviacion) * 100, d.estado, d.alertas]);
      return {
        titulo: 'Rendimiento de vehículos y maquinaria', subtitulo: sub(p, desde, hasta), unidad: 'combustible', landscape: true,
        cols: [{ header: 'Placa', w: 1 }, { header: 'Vehículo', w: 2 }, { header: 'Descargos', w: 0.9, num: 'int' }, { header: 'Recorrido', w: 1, num: 'money' }, { header: 'Medidor', w: 0.8 }, { header: 'Litros', w: 1, num: 'money' }, { header: 'Rend. real', w: 1, num: 'money' }, { header: 'Rend. ref.', w: 1, num: 'money' }, { header: 'Desv. %', w: 0.9, num: 'money' }, { header: 'Observados', w: 1, num: 'int' }, { header: 'Situación', w: 1 }],
        filas, totales: ['TOTAL', '', sumCol(filas, 2), '', '', sumCol(filas, 5), '', '', '', sumCol(filas, 9), ''],
        extra: [{ titulo: 'Detalle de descargos', cols: [{ header: 'Nº', w: 1.2 }, { header: 'Conductor', w: 2.2 }, { header: 'Fecha', w: 1 }, { header: 'Recorrido', w: 1, num: 'money' }, { header: 'Placa', w: 1 }, { header: 'Litros', w: 1, num: 'money' }, { header: 'Rend. real', w: 1, num: 'money' }, { header: 'Rend. ref.', w: 1, num: 'money' }, { header: 'Desv. %', w: 0.9, num: 'money' }, { header: 'Estado', w: 1 }, { header: 'Alertas', w: 3 }], filas: det }],
        firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-pendientes',
    nombre: 'Emisiones sin descargo y descargos vencidos',
    modulo: 'com',
    params: [],
    async ejecutar(db): Promise<Tabla> {
      const plazo = await cfgNum(db, 'DIAS_PLAZO_DESCARGO', 3);
      const hoy = today();
      const rows = await db('com_emisiones').where({ estado: 'Emitido' }).orderBy('hasta');
      const filas = (rows as any[]).map((e) => {
        const lim = addDays(e.hasta, plazo);
        const atraso = lim < hoy ? Math.round((Date.parse(hoy) - Date.parse(lim)) / 86400000) : 0;
        return [e.nro, fmtDate(e.fecha), e.placa, e.conductor, `${fmtDate(e.desde)} - ${fmtDate(e.hasta)}`, fmtDate(lim), atraso, atraso ? 'VENCIDO' : 'EN PLAZO', num(e.monto)];
      });
      const porCond = new Map<string, { p: number; v: number; m: number }>();
      for (const f of filas) {
        const c = String(f[3]);
        const a = porCond.get(c) ?? { p: 0, v: 0, m: 0 };
        a.p++; if (Number(f[6]) > 0) a.v++; a.m += Number(f[8]);
        porCond.set(c, a);
      }
      const fc = [...porCond.entries()].map(([k, a]) => [k, a.p, a.v, a.m, a.v ? 'BLOQUEO SI EXCEDE EL LÍMITE' : 'EN PLAZO']);
      return {
        titulo: 'Emisiones pendientes de descargo', subtitulo: `Plazo: ${plazo} día(s) tras el fin del periodo · Al ${fmtDate(hoy)}`, unidad: 'combustible', landscape: true,
        cols: [{ header: 'Nº Emisión', w: 1.3 }, { header: 'Fecha', w: 1 }, { header: 'Placa', w: 1 }, { header: 'Conductor', w: 2.4 }, { header: 'Periodo', w: 2 }, { header: 'Límite descargo', w: 1.2 }, { header: 'Días atraso', w: 0.9, num: 'int' }, { header: 'Situación', w: 1 }, { header: 'Monto Bs', w: 1.1, num: 'money' }],
        filas, totales: ['TOTAL', '', '', '', '', '', '', '', sumCol(filas, 8)],
        extra: [{ titulo: 'Por conductor', cols: [{ header: 'Conductor', w: 3 }, { header: 'Pendientes', w: 1, num: 'int' }, { header: 'Vencidos', w: 1, num: 'int' }, { header: 'Monto Bs', w: 1.2, num: 'money' }, { header: 'Situación', w: 2 }], filas: fc }],
        firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-cronograma',
    nombre: 'Cronograma mensual de uso de maquinaria y vehículos',
    modulo: 'com',
    params: [{ name: 'mes', label: 'Mes (cualquier fecha del mes)', type: 'date' }],
    async ejecutar(db, p): Promise<Tabla> {
      const mes = (isDate(p.mes) ? p.mes! : today()).slice(0, 7) + '-01';
      const filas = (await db('com_cronograma as c').leftJoin('com_vehiculos as v', 'v.placa', 'c.placa').where('c.mes', mes).select('c.*', 'v.tipo', 'v.marca', 'v.medidor').orderBy('c.placa')).map((c: any) => [c.placa, `${txt(c.tipo)} ${txt(c.marca)}`.trim(), c.medidor, c.obra, c.apertura, c.dias, num(c.km_horas), num(c.litros_estimados), c.responsable]);
      const c = await cfgAll(db);
      return {
        titulo: 'Cronograma mensual de uso de maquinaria y vehículos operativos', subtitulo: `${MESES[month(mes) - 1]} ${year(mes)}`, unidad: 'combustible', landscape: true,
        cols: [{ header: 'Placa', w: 1 }, { header: 'Vehículo', w: 2 }, { header: 'Medidor', w: 0.8 }, { header: 'Obra / actividad', w: 3 }, { header: 'Apertura', w: 1 }, { header: 'Días', w: 0.6, num: 'int' }, { header: 'Km u horas', w: 1, num: 'money' }, { header: 'Litros est.', w: 1, num: 'money' }, { header: 'Responsable', w: 2 }],
        filas, totales: ['TOTAL', '', '', '', '', '', sumCol(filas, 6), sumCol(filas, 7), ''],
        firmas: [{ nombre: c.NombreSMG, cargo: c.CargoSMG, rol: 'PROGRAMACIÓN DE MAQUINARIA' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE COMBUSTIBLE' }],
      };
    },
  },
  {
    id: 'com-viajes',
    nombre: 'Viajes oficiales con fondos en avance',
    modulo: 'com',
    params: PARAMS,
    async ejecutar(db, p): Promise<Tabla> {
      const { desde, hasta } = per(p);
      const q = db('com_viajes').whereBetween('fecha', [desde, hasta]).orderBy('nro');
      if (txt(p.placa)) q.where({ placa: p.placa });
      const filas = (await q).map((v: any) => [v.nro, fmtDate(v.fecha), v.placa, v.conductor, `${v.origen} → ${v.destino}`, num(v.fondo), num(v.gastado), num(v.saldo), v.estado, v.resultado ?? '']);
      return {
        titulo: 'Viajes oficiales con fondos en avance', subtitulo: sub(p, desde, hasta), unidad: 'combustible', landscape: true,
        cols: [{ header: 'Nº Viaje', w: 1.2 }, { header: 'Fecha', w: 1 }, { header: 'Placa', w: 1 }, { header: 'Conductor', w: 2.2 }, { header: 'Ruta', w: 3 }, { header: 'Fondo Bs', w: 1.1, num: 'money' }, { header: 'Gastado Bs', w: 1.1, num: 'money' }, { header: 'Saldo Bs', w: 1.1, num: 'money' }, { header: 'Estado', w: 1 }, { header: 'Resultado', w: 1 }],
        filas, totales: ['TOTAL', '', '', '', '', sumCol(filas, 5), sumCol(filas, 6), sumCol(filas, 7), '', ''], firmas: await firmas(db),
      };
    },
  },
  {
    id: 'com-informe-mensual',
    nombre: 'Informe mensual de descargo de uso de vales (Anexo 5)',
    modulo: 'com',
    params: [
      { name: 'mes', label: 'Mes a informar (cualquier fecha del mes)', type: 'date' },
      { name: 'a_nombre', label: 'A (nombre)', type: 'text' },
      { name: 'a_cargo', label: 'Cargo', type: 'text' },
      { name: 'via_nombre', label: 'Vía (nombre, opcional)', type: 'text' },
      { name: 'via_cargo', label: 'Vía (cargo)', type: 'text' },
      { name: 'antecedentes', label: 'Antecedentes', type: 'text' },
      { name: 'actividades', label: 'Actividades sobresalientes', type: 'text' },
      { name: 'conclusiones', label: 'Conclusiones', type: 'text' },
      { name: 'recomendaciones', label: 'Recomendaciones', type: 'text' },
    ],
    async ejecutar(db, p): Promise<Tabla> {
      const mes = (isDate(p.mes) ? p.mes! : today()).slice(0, 7);
      const d0 = `${mes}-01`;
      const d1 = addDays(`${month(d0) === 12 ? year(d0) + 1 : year(d0)}-${String(month(d0) === 12 ? 1 : month(d0) + 1).padStart(2, '0')}-01`, -1);
      const c = await cfgAll(db);
      // 2. Movimiento de vales
      const kx = (await db('com_kardex').where('almacen', 'VALES').where('fecha', '<=', d1)) as any[];
      const items = [...new Set(kx.map((k) => k.item))].sort();
      const f2 = items.map((it) => {
        const r = { ini: 0, ing: 0, ent: 0, dev: 0, baj: 0 };
        for (const k of kx.filter((x) => x.item === it)) {
          if (k.fecha < d0) r.ini += num(k.entrada) - num(k.salida);
          else if (k.tipo === 'INGRESO') r.ing += num(k.entrada);
          else if (k.tipo === 'SALIDA') r.ent += num(k.salida);
          else if (k.tipo === 'DEVOLUCIÓN') r.dev += num(k.entrada);
          else if (k.tipo === 'BAJA') r.baj += num(k.salida);
        }
        const fin = r.ini + r.ing - r.ent + r.dev - r.baj;
        const corte = Number(/Bs (\d+)/.exec(it)?.[1] ?? 0);
        return [it, r.ini, r.ing, r.ent, r.dev, r.baj, fin, fin * corte];
      });
      // 3. Por apertura / 4. Por vehículo
      const em = (await db('com_emisiones').whereNot({ estado: 'Anulado' }).whereBetween('fecha', [d0, d1])) as any[];
      const agg = (key: (e: any) => string) => {
        const m = new Map<string, { n: number; v: number; l: number; m: number; d: string }>();
        for (const e of em) {
          const k = key(e);
          const a = m.get(k) ?? { n: 0, v: 0, l: 0, m: 0, d: '' };
          a.n++; a.v += num(e.cant_vales); a.l += num(e.litros); a.m += num(e.monto);
          a.d = key === undefined ? '' : a.d;
          m.set(k, a);
        }
        return m;
      };
      const apD = new Map((await db('core_aperturas')).map((a: any) => [a.apertura, a.descripcion]));
      const f3 = [...agg((e) => e.apertura).entries()].map(([k, a]) => [k, a.n, a.v, round(a.l, 2), round(a.m, 2), apD.get(k) ?? '']);
      const vd = new Map(em.map((e) => [e.placa, e.descripcion_destino]));
      const f4 = [...agg((e) => e.placa).entries()].map(([k, a]) => [k, a.n, a.v, round(a.l, 2), round(a.m, 2), vd.get(k) ?? '']);
      const total = sumCol(f3, 4);
      // 5. Descargos
      const ds = (await db('com_descargos').whereBetween('fecha', [d0, d1])) as any[];
      const f5 = ds.map((d) => [d.nro, fmtDate(d.fecha), d.placa, num(d.rendimiento_real), `${d.conductor}${d.alertas ? ' — ' + d.alertas : ''}`]);
      const plazo = await cfgNum(db, 'DIAS_PLAZO_DESCARGO', 3);
      const pend = ((await db('com_emisiones').where({ estado: 'Emitido' }).where('hasta', '<=', d1)) as any[]).filter((e) => addDays(e.hasta, plazo) < d1).map((e) => [e.nro, fmtDate(e.hasta), e.placa, Math.round((Date.parse(d1) - Date.parse(addDays(e.hasta, plazo))) / 86400000), e.conductor]);
      // 6. Conciliaciones / 7. Turriles / 8. Viajes
      const cc = (await db('com_conciliaciones').whereBetween('fecha', [d0, d1])) as any[];
      const ccm = new Map<string, { conf: number; bs: number; obs: number; prov: string; per: string }>();
      for (const r of cc) {
        const a = ccm.get(r.nro) ?? { conf: 0, bs: 0, obs: 0, prov: r.proveedor, per: `${fmtDate(r.desde)} - ${fmtDate(r.hasta)}` };
        if (r.pagable) { a.conf++; a.bs += num(r.monto_cobrado); } else a.obs++;
        ccm.set(r.nro, a);
      }
      const f6 = [...ccm.entries()].map(([k, a]) => [k, a.per, a.conf, a.bs, a.obs, a.prov]);
      const f7: unknown[][] = [];
      for (const pt of await db('com_puestos')) {
        const k = kx.length ? ((await db('com_kardex').where({ almacen: pt.codigo }).where('fecha', '<=', d1)) as any[]) : [];
        const ing = k.filter((x) => x.fecha >= d0 && x.tipo === 'INGRESO').reduce((t, x) => t + num(x.entrada), 0);
        const des = k.filter((x) => x.fecha >= d0 && x.tipo !== 'INGRESO').reduce((t, x) => t + num(x.salida) - num(x.entrada), 0);
        const saldo = k.reduce((t, x) => t + num(x.entrada) - num(x.salida), 0);
        const cu = await costoPromTurril(db, pt.codigo);
        f7.push([pt.codigo, ing, des, saldo, round(saldo * cu, 2), pt.nombre]);
      }
      const f8 = ((await db('com_viajes').whereBetween('fecha', [d0, d1])) as any[]).map((v) => [v.nro, v.placa, num(v.fondo), num(v.gastado), num(v.saldo), v.estado, `${v.destino} / ${v.conductor}`]);
      const money = { num: 'money' as const };
      const int = { num: 'int' as const };
      return {
        titulo: 'Informe mensual de descargo de uso de vales de combustible (Anexo 5)', subtitulo: `${MESES[month(d0) - 1]} ${year(d0)}`, unidad: 'combustible', landscape: true,
        nota: [
          `A: ${txt(p.a_nombre) || c.NombreSEC} — ${txt(p.a_cargo) || c.CargoSEC}`,
          txt(p.via_nombre) ? `VÍA: ${p.via_nombre} — ${txt(p.via_cargo)}` : '',
          `DE: ${c.NombreRAF} — ${c.CargoRAF}`,
          `REF.: Informe mensual de descargo de uso de vales de combustible - ${MESES[month(d0) - 1]} ${year(d0)}`,
          `1. ANTECEDENTES: ${txt(p.antecedentes) || 'Se presenta el informe mensual de descargo de uso de vales de combustible.'}`,
          `SON: ${literal(total)}`,
        ].filter(Boolean).join('\n'),
        cols: [{ header: '2. MOVIMIENTO DE VALES — Ítem', w: 3 }, { header: 'Saldo inicial', w: 1, ...int }, { header: 'Ingresos', w: 1, ...int }, { header: 'Entregas', w: 1, ...int }, { header: 'Devoluciones', w: 1, ...int }, { header: 'Bajas', w: 1, ...int }, { header: 'Saldo final', w: 1, ...int }, { header: 'Saldo final Bs', w: 1.2, ...money }],
        filas: f2, totales: ['TOTAL', '', '', '', '', '', '', sumCol(f2, 7)],
        extra: [
          { titulo: '3. Combustible entregado por apertura programática', cols: [{ header: 'Apertura', w: 1.4 }, { header: 'Emisiones', w: 1, ...int }, { header: 'Vales', w: 1, ...int }, { header: 'Litros', w: 1, ...money }, { header: 'Importe Bs', w: 1.2, ...money }, { header: 'Descripción', w: 3 }], filas: f3, totales: ['TOTAL', sumCol(f3, 1), sumCol(f3, 2), sumCol(f3, 3), total, ''] },
          { titulo: '4. Combustible entregado por vehículo / puesto', cols: [{ header: 'Placa / puesto', w: 1.4 }, { header: 'Emisiones', w: 1, ...int }, { header: 'Vales', w: 1, ...int }, { header: 'Litros', w: 1, ...money }, { header: 'Importe Bs', w: 1.2, ...money }, { header: 'Descripción', w: 3 }], filas: f4, totales: ['TOTAL', sumCol(f4, 1), sumCol(f4, 2), sumCol(f4, 3), sumCol(f4, 4), ''] },
          { titulo: '5. Descargos de los conductores (Anexo 3) — presentados', cols: [{ header: 'Nº descargo', w: 1.3 }, { header: 'Fecha', w: 1 }, { header: 'Placa', w: 1 }, { header: 'Rend. real', w: 1, ...money }, { header: 'Conductor / alerta', w: 4 }], filas: f5 },
          { titulo: '5. Descargos vencidos al cierre (emisión sin descargo)', cols: [{ header: 'Emisión', w: 1.3 }, { header: 'Fin periodo', w: 1 }, { header: 'Placa', w: 1 }, { header: 'Días atraso', w: 1, ...int }, { header: 'Conductor', w: 4 }], filas: pend },
          { titulo: '6. Conciliación con proveedores', cols: [{ header: 'Nº', w: 1.2 }, { header: 'Periodo', w: 2 }, { header: 'Conformes', w: 1, ...int }, { header: 'Bs conforme', w: 1.2, ...money }, { header: 'Observados', w: 1, ...int }, { header: 'Proveedor', w: 3 }], filas: f6, totales: ['TOTAL', '', sumCol(f6, 2), sumCol(f6, 3), sumCol(f6, 4), ''] },
          { titulo: '7. Combustible en turriles', cols: [{ header: 'Puesto', w: 1 }, { header: 'Ingresos L (mes)', w: 1.2, ...money }, { header: 'Despachos L (mes)', w: 1.2, ...money }, { header: 'Saldo L', w: 1, ...money }, { header: 'Saldo Bs', w: 1, ...money }, { header: 'Nombre', w: 3 }], filas: f7, totales: ['TOTAL', sumCol(f7, 1), sumCol(f7, 2), sumCol(f7, 3), sumCol(f7, 4), ''] },
          { titulo: '8. Viajes oficiales con fondos en avance', cols: [{ header: 'Nº viaje', w: 1.2 }, { header: 'Placa', w: 1 }, { header: 'Fondo Bs', w: 1, ...money }, { header: 'Gastado Bs', w: 1, ...money }, { header: 'Saldo Bs', w: 1, ...money }, { header: 'Estado', w: 1 }, { header: 'Destino / conductor', w: 3 }], filas: f8, totales: ['TOTAL', '', sumCol(f8, 2), sumCol(f8, 3), sumCol(f8, 4), '', ''] },
          { titulo: '9-11. Actividades, conclusiones y recomendaciones', cols: [{ header: 'Sección', w: 1.5 }, { header: 'Texto', w: 6 }], filas: [['9. Actividades sobresalientes', txt(p.actividades) || 'Ninguna.'], ['10. Conclusiones', txt(p.conclusiones) || '-'], ['11. Recomendaciones', txt(p.recomendaciones) || '-']] },
        ],
        firmas: [{ nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'ELABORA' }],
      };
    },
  },
);
void fmt2;
