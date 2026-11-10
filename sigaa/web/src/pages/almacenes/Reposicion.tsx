import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Card, DataTable, DateField, PageHead, SelectField, useAction, useLoad } from '../../ui';
import { useAlmMeta } from './common';

export default function AlmReposicion() {
  const { puede } = useAuth();
  const { data: meta } = useAlmMeta();
  const { data: reqs, reload } = useLoad<any[]>(() => get('/alm/requerimientos'));
  const [bod, setBod] = useState('');
  const [rows, setRows] = useState<any[]>([]);
  const [h, setH] = useState({ fecha: hoy(), tipo: 'PREVISTO - REPOSICIÓN DE STOCK', justificacion: 'Reposición de existencias en o bajo el stock mínimo para garantizar la continuidad de las operaciones.' });
  const [run, busy] = useAction();
  const total = rows.reduce((t, r) => t + (Number(r.cant_solic) || 0) * Number(r.precio_ref), 0);
  return (
    <>
      <PageHead title="Gestión de existencias y requerimiento de compra" sub="Control de stock mínimo · informe técnico de reposición · cantidad sugerida = máximo − stock" />
      <Card title="1. Calcular ítems en o bajo el stock mínimo">
        <div className="row">
          <SelectField label="Bodega (o todas)" value={bod} onChange={setBod} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
          <button className="primary" disabled={busy} onClick={() => run(async () => { const r = await get('/alm/reposicion', { bod }); setRows(r); if (!r.length) throw new Error('Ningún ítem está en o bajo el stock mínimo. No se requiere reposición.'); })}>Calcular reposición</button>
        </div>
      </Card>
      {rows.length > 0 && (
        <Card title="2. Revise las cantidades y registre el requerimiento" right={<b>Total estimado: Bs {fmt2(total)}</b>}>
          <div className="table-wrap" style={{ maxHeight: '45vh' }}>
            <table className="t"><thead><tr><th>Código</th><th>Descripción</th><th>Unid.</th><th className="num">Stock</th><th className="num">Mín.</th><th className="num">Máx.</th><th className="num">Sugerido</th><th className="num" style={{ width: 120 }}>A solicitar</th><th className="num">P.U. ref.</th><th className="num">Importe</th></tr></thead>
              <tbody>{rows.map((r, i) => (
                <tr key={r.cod_item}><td>{r.cod_item}</td><td>{r.descripcion}</td><td>{r.unidad}</td><td className="num">{r.stock}</td><td className="num">{r.minimo}</td><td className="num">{r.maximo}</td><td className="num">{r.sugerido}</td>
                  <td><input type="number" value={r.cant_solic} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, cant_solic: e.target.value } : x)))} /></td>
                  <td className="num">{fmt2(r.precio_ref)}</td><td className="num">{fmt2((Number(r.cant_solic) || 0) * Number(r.precio_ref))}</td></tr>))}</tbody></table>
          </div>
          <div className="grid" style={{ marginTop: 10 }}>
            <DateField label="Fecha" value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} />
            <SelectField label="Tipo de requerimiento" blank={false} value={h.tipo} onChange={(v) => setH({ ...h, tipo: v })} options={meta?.tipos_requerimiento ?? []} />
            <AreaField className="span-all" label="Justificación" value={h.justificacion} onChange={(v) => setH({ ...h, justificacion: v })} />
          </div>
          {puede('alm') && <div style={{ marginTop: 10 }}><button className="ok" disabled={busy} onClick={() => run(async () => { const r = await post('/alm/requerimientos', { ...h, bod, items: rows.map((x) => ({ cod_item: x.cod_item, cant_solic: Number(x.cant_solic) })) }); setRows([]); await reload(); abrirDocumento('alm-requerimiento', r.nro); }, 'Requerimiento registrado.')}>Guardar requerimiento</button></div>}
        </Card>
      )}
      <Card title="Requerimientos registrados">
        <DataTable rows={reqs ?? []} cols={[{ key: 'nro', header: 'Nº' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'tipo', header: 'Tipo' }, { key: 'total', header: 'Total Bs', money: true }, { key: 'estado', header: 'Estado', badge: true }, { key: 'p', header: '', render: (r) => <button className="sm" onClick={() => abrirDocumento('alm-requerimiento', r.nro)}>Imprimir</button> }]} />
      </Card>
    </>
  );
}
