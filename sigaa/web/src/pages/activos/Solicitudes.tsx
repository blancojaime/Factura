import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { abrirDocumento, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, PageHead, SelectField, useAction, useLoad, useUi } from '../../ui';
import { nroUrl, optsAux, optsCta, useAfMeta } from './common';

const vacio = () => ({ nro: '', fecha: hoy(), unidad: '', funcionario: '', cargo: '', justificacion: '', aprobado_daf: 'NO', estado: '', nro_acta: '' });
const lin = () => ({ id_cta: '', id_aux: '', cantidad: '', saldo: '' });
export default function AfSolicitudes() {
  const { puede } = useAuth();
  const ui = useUi();
  const nav = useNavigate();
  const { data: meta } = useAfMeta();
  const { data: lista, reload } = useLoad<any[]>(() => get('/af/solicitudes'));
  const [h, setH] = useState<any>(vacio());
  const [items, setItems] = useState<any[]>([lin()]);
  const [run, busy] = useAction();
  const cargar = (nro: string) => run(async () => { const d = await get(`/af/solicitudes/${nroUrl(nro)}`); setH({ ...vacio(), ...d }); setItems(d.items.map((x: any) => ({ id_cta: x.id_cta, id_aux: x.id_aux, cantidad: x.cantidad, saldo: x.saldo }))); });
  const guardar = () => run(async () => {
    const r = await post('/af/solicitudes', { ...h, items: items.filter((i) => i.id_cta).map((i) => ({ id_cta: Number(i.id_cta), id_aux: Number(i.id_aux), cantidad: Number(i.cantidad) })) });
    await cargar(r.nro); await reload(); ui.ok(`Solicitud ${r.nro} guardada. Verifique el saldo en almacén.`);
  });
  const editable = puede('af') && !['ATENDIDA'].includes(h.estado);
  const elegirFunc = (n: string) => { const f = meta?.funcionarios.find((x) => x.nombre === n); setH({ ...h, funcionario: n, cargo: f?.cargo ?? h.cargo, unidad: h.unidad || f?.unidad || '' }); };
  return (
    <>
      <PageHead title="Solicitud de activos fijos" sub="La unidad solicitante pide los activos; el sistema muestra el saldo disponible en almacén">
        {puede('af') && <button className="primary" onClick={() => { setH(vacio()); setItems([lin()]); }}>Nueva solicitud</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: 'minmax(250px,320px) minmax(0,1fr)' }}>
        <Card title="Solicitudes"><DataTable maxHeight="70vh" rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === h.nro} cols={[{ key: 'nro', header: 'Nº' }, { key: 'funcionario', header: 'Funcionario' }, { key: 'estado', header: 'Estado', badge: true }]} /></Card>
        <div>
          <Card title={h.nro || 'Nueva solicitud'} right={<Badge v={h.estado} />}>
            <div className="grid">
              <DateField label="Fecha" req value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} disabled={!editable} />
              <SelectField label="Funcionario solicitante" req value={h.funcionario} onChange={elegirFunc} disabled={!editable} options={(meta?.funcionarios ?? []).map((f) => f.nombre)} />
              <SelectField label="Unidad solicitante" req value={h.unidad} onChange={(v) => setH({ ...h, unidad: v })} disabled={!editable} options={(meta?.unidades ?? []).map((u) => u.nombre)} />
              <SelectField label="Aprobado por DAF" blank={false} value={h.aprobado_daf} onChange={(v) => setH({ ...h, aprobado_daf: v })} disabled={!editable} options={['SI', 'NO']} />
              <AreaField className="span-all" label="Justificación" value={h.justificacion} onChange={(v) => setH({ ...h, justificacion: v })} disabled={!editable} />
            </div>
          </Card>
          <Card title="Activos solicitados">
            <div className="table-wrap"><table className="t"><thead><tr><th>#</th><th>Cuenta contable</th><th>Auxiliar</th><th className="num" style={{ width: 100 }}>Cantidad</th><th className="num">Saldo en almacén</th><th /></tr></thead>
              <tbody>{items.map((it, i) => (
                <tr key={i}><td className="ctr">{i + 1}</td>
                  <td><select disabled={!editable} value={it.id_cta} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, id_cta: e.target.value, id_aux: '' } : x)))}><option />{optsCta(meta).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></td>
                  <td><select disabled={!editable || !it.id_cta} value={it.id_aux} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, id_aux: e.target.value } : x)))}><option />{optsAux(meta, it.id_cta).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></td>
                  <td><input type="number" disabled={!editable} value={it.cantidad} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, cantidad: e.target.value } : x)))} /></td>
                  <td className="num" style={{ color: it.saldo !== '' && Number(it.saldo) < Number(it.cantidad) ? 'var(--danger)' : undefined }}>{it.saldo}</td>
                  <td>{editable && <button className="sm danger" onClick={() => setItems(items.filter((_, j) => j !== i))}>×</button>}</td></tr>))}</tbody></table></div>
            {editable && <div style={{ marginTop: 6 }}><button className="sm" onClick={() => setItems([...items, lin()])}>+ Agregar línea</button></div>}
          </Card>
          <div className="row">
            {editable && <button className="primary" disabled={busy} onClick={guardar}>Guardar solicitud</button>}
            {h.nro && puede('af') && h.estado !== 'ATENDIDA' && h.estado !== 'SIN EXISTENCIA' && <button className="ok" onClick={() => nav(`/activos/asignar?sol=${nroUrl(h.nro)}`)}>Atender (asignar activos)</button>}
            {h.nro && puede('af') && ['PENDIENTE', 'ATENDIDA PARCIAL'].includes(h.estado) && <button className="danger" disabled={busy} onClick={async () => { if (await ui.confirm('¿Registrar la solicitud como SIN EXISTENCIA?')) run(async () => { await post(`/af/solicitudes/${nroUrl(h.nro)}/sin-existencia`); await cargar(h.nro); await reload(); abrirDocumento('af-salida-sin-existencia', h.nro); }); }}>Sin existencia</button>}
            {h.nro && <button onClick={() => abrirDocumento('af-solicitud', h.nro)}>Imprimir solicitud</button>}
          </div>
        </div>
      </div>
    </>
  );
}
