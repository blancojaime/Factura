import type { Db } from '../../core/context.js';
import { addDays, num, round, today } from '../../core/util.js';
import { cfgNum } from '../../core/services.js';
import { saldosActuales } from './stock.js';
import { alertasSeguridad } from './otros.js';

export interface Alerta {
  modulo: 'alm' | 'com' | 'af';
  nivel: 'info' | 'aviso' | 'critico';
  texto: string;
  ruta?: string;
}

/** Indicadores y alertas de Almacenes (equivalente a la pantalla INICIO del sistema original). */
export async function dashboardAlm(db: Db) {
  const hoy = today();
  const dias = await cfgNum(db, 'DiasVenc', 90);
  const cat = await db('alm_catalogo').where({ estado: 'ACTIVO' });
  const sal = await saldosActuales(db, '');
  let bajo = 0;
  let valor = 0;
  for (const c of cat) {
    const s = sal.get(`${c.cod_bod}|${c.codigo}`)?.cant ?? 0;
    if (num(c.stock_min) > 0 && s <= num(c.stock_min)) bajo++;
  }
  for (const v of sal.values()) valor += v.bs;
  const lotes = await db('alm_lotes').where({ estado: 'ACTIVO' }).where('saldo', '>', 1e-6).whereNotNull('vencimiento');
  const porVencer = lotes.filter((l: any) => l.vencimiento >= hoy && l.vencimiento <= addDays(hoy, dias)).length;
  const vencidos = lotes.filter((l: any) => l.vencimiento < hoy).length;
  const cnt = async (t: string, w: Record<string, string>) => Number((await db(t).where(w).count({ n: '*' }).first())?.n);
  const pedidos = Number((await db('alm_salidas').whereIn('estado', ['PEDIDO', 'APROBADO']).count({ n: '*' }).first())?.n);
  const ingresos = await cnt('alm_ingresos', { estado: 'REGISTRADO' });
  const bajas = Number((await db('alm_bajas').whereIn('estado', ['EN TRÁMITE', 'BAJA EJECUTADA']).count({ n: '*' }).first())?.n); // no concluidos (pasos de disposición pendientes)
  const seg = await alertasSeguridad(db);
  const alertas: Alerta[] = [];
  if (bajo) alertas.push({ modulo: 'alm', nivel: 'aviso', texto: `${bajo} ítem(s) en o bajo el stock mínimo: genere el requerimiento de compra.`, ruta: '/almacenes/reposicion' });
  if (vencidos) alertas.push({ modulo: 'alm', nivel: 'critico', texto: `${vencidos} lote(s) VENCIDOS con existencia: inicie la baja por vencimiento.`, ruta: '/almacenes/bajas' });
  if (porVencer) alertas.push({ modulo: 'alm', nivel: 'aviso', texto: `${porVencer} lote(s) vencen en los próximos ${dias} días: priorice su salida.`, ruta: '/reportes/alm-vencimientos' });
  if (pedidos) alertas.push({ modulo: 'alm', nivel: 'info', texto: `${pedidos} pedido(s) de salida pendiente(s) de aprobación o entrega.`, ruta: '/almacenes/salidas' });
  if (ingresos) alertas.push({ modulo: 'alm', nivel: 'info', texto: `${ingresos} ingreso(s) registrado(s) sin confirmar: complete los documentos de respaldo.`, ruta: '/almacenes/ingresos' });
  if (bajas) alertas.push({ modulo: 'alm', nivel: 'info', texto: `${bajas} expediente(s) de baja en trámite.`, ruta: '/almacenes/bajas' });
  if (seg.extintoresVencidos.length) alertas.push({ modulo: 'alm', nivel: 'critico', texto: `${seg.extintoresVencidos.length} extintor(es) con recarga VENCIDA: solicite recarga o baja.`, ruta: '/almacenes/seguridad' });
  if (seg.extintoresPorVencer.length) alertas.push({ modulo: 'alm', nivel: 'aviso', texto: `${seg.extintoresPorVencer.length} extintor(es) con recarga próxima a vencer.`, ruta: '/almacenes/seguridad' });
  if (seg.segurosVencidos.length) alertas.push({ modulo: 'alm', nivel: 'critico', texto: `${seg.segurosVencidos.length} póliza(s) de seguro VENCIDA(S).`, ruta: '/almacenes/seguridad' });
  if (seg.segurosPorVencer.length) alertas.push({ modulo: 'alm', nivel: 'aviso', texto: `${seg.segurosPorVencer.length} póliza(s) de seguro próxima(s) a vencer.`, ruta: '/almacenes/seguridad' });
  if (hoy.slice(5, 7) >= '11') alertas.push({ modulo: 'alm', nivel: 'info', texto: 'Programe el INVENTARIO ANUAL (100%) de cierre de gestión.', ruta: '/almacenes/cierre' });
  return {
    indicadores: { items: cat.length, bajo_minimo: bajo, por_vencer: porVencer, vencidos, pedidos_pendientes: pedidos, ingresos_sin_confirmar: ingresos, bajas_en_tramite: bajas, valor_existencias: round(valor, 2) },
    alertas,
  };
}
