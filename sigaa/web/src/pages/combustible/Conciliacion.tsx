import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { Badge, Card, DataTable, DateField, PageHead, SelectField, useAction, useLoad } from '../../ui';
import { useComMeta } from './common';

interface Cobro { nro_vale: number; fecha?: string; placa?: string; litros?: number; monto: number; factura?: string }

/** Interpreta el detalle pegado desde Excel/CSV: nro vale, fecha, placa, litros, monto, factura (con o sin encabezado). */
export function parseCobros(texto: string): Cobro[] {
  const out: Cobro[] = [];
  const sin = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  let idx: Record<string, number> | null = null;
  for (const linea of texto.split(/\r?\n/)) {
    if (!linea.trim()) continue;
    const c = linea.split(/\t|;|,(?=(?:[^"]*"[^"]*")*[^"]*$)/).map((x) => x.replace(/^"|"$/g, '').trim());
    const cab = c.map(sin);
    if (cab.some((x) => x.includes('vale')) && cab.some((x) => x.includes('monto') || x.includes('importe'))) {
      idx = {};
      cab.forEach((x, i) => {
        if (x.includes('vale')) idx!.vale = i; else if (x.includes('fecha')) idx!.fecha = i; else if (x.includes('placa')) idx!.placa = i; else if (x.includes('litro')) idx!.litros = i; else if (x.includes('monto') || x.includes('importe')) idx!.monto = i; else if (x.includes('factura')) idx!.factura = i;
      });
      continue;
    }
    const g = (k: string, d: number) => c[idx ? idx[k] ?? -1 : d];
    const num = (s?: string) => Number(String(s ?? '').replace(/\./g, (m, off, str) => (str.includes(',') ? '' : m)).replace(',', '.'));
    const nv = Number(String(g('vale', 0) ?? '').replace(/\D/g, ''));
    const monto = num(g('monto', 4));
    if (!nv || isNaN(monto)) continue;
    let f = g('fecha', 1) ?? '';
    const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(f);
    if (m) f = `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
    out.push({ nro_vale: nv, fecha: /^\d{4}-\d{2}-\d{2}/.test(f) ? f.slice(0, 10) : undefined, placa: g('placa', 2), litros: num(g('litros', 3)) || undefined, monto, factura: g('factura', 5) });
  }
  return out;
}

export default function ComConciliacion() {
  const { puede } = useAuth();
  const { data: meta } = useComMeta();
  const { data: hist, reload } = useLoad<any[]>(() => get('/com/conciliaciones'));
  const [f, setF] = useState<any>({ proveedor: '', contrato: '', desde: `${hoy().slice(0, 7)}-01`, hasta: hoy() });
  const [texto, setTexto] = useState('');
  const [res, setRes] = useState<any>(null);
  const [run, busy] = useAction();
  const cobros = parseCobros(texto);
  const cargarArchivo = (file?: File) => file && file.text().then(setTexto);
  return (
    <>
      <PageHead title="Conciliación con el proveedor" sub="Compare los vales que cobra la estación de servicio con los entregados y descargados en el sistema" />
      <Card title="1. Proveedor y periodo">
        <div className="grid">
          <SelectField label="Proveedor" req value={f.proveedor} onChange={(v) => setF({ ...f, proveedor: v })} options={[...new Set((meta?.contratos ?? []).map((c) => c.proveedor))]} />
          <SelectField label="Contrato (opcional)" value={f.contrato} onChange={(v) => setF({ ...f, contrato: v })} options={(meta?.contratos ?? []).filter((c) => !f.proveedor || c.proveedor === f.proveedor).map((c) => c.nro)} />
          <DateField label="Periodo desde" req value={f.desde} onChange={(v) => setF({ ...f, desde: v })} />
          <DateField label="Hasta" req value={f.hasta} onChange={(v) => setF({ ...f, hasta: v })} />
        </div>
      </Card>
      <Card title="2. Vales cobrados por el proveedor" right={<input type="file" accept=".csv,.txt,.tsv" onChange={(e) => cargarArchivo(e.target.files?.[0])} />}>
        <p className="muted" style={{ marginTop: 0 }}>Pegue aquí el detalle del proveedor (una fila por vale) copiado desde Excel o cargue un archivo CSV. Columnas: Nº vale, Fecha, Placa, Litros, Monto Bs, Factura (con o sin encabezado).</p>
        <textarea rows={7} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={'Nro Vale\tFecha\tPlaca\tLitros\tMonto Bs\tFactura\n1001\t29/09/2026\t2345ABC\t4.31\t30\tF-123'} style={{ fontFamily: 'monospace' }} />
        <small className="muted">Se reconocen {cobros.length} vale(s) por Bs {fmt2(cobros.reduce((t, c) => t + c.monto, 0))}.</small>
      </Card>
      {puede('com') && <button className="primary" disabled={busy || !cobros.length || !f.proveedor} onClick={() => run(async () => { const r = await post('/com/conciliaciones', { ...f, cobros }); setRes(r); reload(); abrirDocumento('com-conciliacion', r.nro); }, 'Conciliación registrada.')}>Conciliar</button>}
      {res && (
        <Card title={`Resultado ${res.nro}`}>
          <div className="kpis"><div className="kpi com"><b>{res.conformes}</b><span>Conformes</span></div><div className="kpi com"><b>Bs {fmt2(res.total_pagar)}</b><span>Monto a pagar</span></div><div className={'kpi ' + (res.observados ? 'warn' : 'com')}><b>{res.observados}</b><span>Observados</span></div></div>
          <div className="row">{Object.entries(res.resumen).map(([k, n]) => <span key={k}><Badge v={k === 'CONFORME' ? 'CONFORME' : 'Observado'} /> {k}: <b>{String(n)}</b></span>)}</div>
        </Card>
      )}
      <Card title="Conciliaciones realizadas"><DataTable rows={hist ?? []} cols={[{ key: 'nro', header: 'Nº' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'proveedor', header: 'Proveedor' }, { key: 'desde', header: 'Desde', date: true }, { key: 'hasta', header: 'Hasta', date: true }, { key: 'lineas', header: 'Vales', num: true }, { key: 'p', header: '', render: (r) => <button className="sm" onClick={() => abrirDocumento('com-conciliacion', r.nro)}>PDF</button> }]} /></Card>
    </>
  );
}
