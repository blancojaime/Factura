import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, ItemsGrid, PageHead, SelectField, TextField, useAction, useLoad, useUi } from '../../ui';
import { nroUrl, optsAux, optsCta, useAfMeta } from './common';

const vacio = () => ({ nro: '', fecha: hoy(), tipo_doc: '', nro_doc: '', preventivo: '', proveedor: '', factura: '', nro_memo: '', comision1: '', comision2: '', unidad: '', fuente_fin: '', observaciones: '', estado: '', total: 0 });
const lin = () => ({ id_cta: '', id_aux: '', descripcion: '', unidad: 'PIEZA', cantidad: '', precio_unit: '', cant_codif: 0 });

export default function AfIngresos() {
  const { puede } = useAuth();
  const ui = useUi();
  const nav = useNavigate();
  const { data: meta } = useAfMeta();
  const { data: lista, reload } = useLoad<any[]>(() => get('/af/ingresos'));
  const [h, setH] = useState<any>(vacio());
  const [items, setItems] = useState<any[]>([lin()]);
  const [run, busy] = useAction();
  const total = items.reduce((t, i) => t + (Number(i.cantidad) || 0) * (Number(i.precio_unit) || 0), 0);
  const cargar = (nro: string) => run(async () => {
    const d = await get(`/af/ingresos/${nroUrl(nro)}`);
    setH({ ...vacio(), ...d });
    setItems(d.items.map((x: any) => ({ ...x })));
  });
  const guardar = () => run(async () => {
    const r = await post('/af/ingresos', { ...h, items: items.filter((i) => i.id_cta).map((i) => ({ id_cta: Number(i.id_cta), id_aux: Number(i.id_aux), descripcion: i.descripcion, unidad: i.unidad, cantidad: Number(i.cantidad), precio_unit: Number(i.precio_unit) })) });
    await cargar(r.nro); await reload();
    ui.ok(`Ingreso ${r.nro} guardado (Bs ${fmt2(r.total)}). Siguiente paso: Codificación.`);
    if (r.advertencias?.length) ui.error('Advertencias:\n' + r.advertencias.join('\n'));
  });
  const editable = puede('af');
  const compra = ['ORDEN DE COMPRA', 'CONTRATO'].includes(h.tipo_doc);
  return (
    <>
      <PageHead title="Recepción e ingreso de activos fijos a almacén" sub="Orden de compra / contrato → memorándum de comisión → acta de conformidad → formulario de ingreso">
        {editable && <button className="primary" onClick={() => { setH(vacio()); setItems([lin()]); }}>Nuevo ingreso</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: 'minmax(250px,320px) minmax(0,1fr)' }}>
        <Card title="Ingresos"><DataTable maxHeight="70vh" rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === h.nro} cols={[{ key: 'nro', header: 'Nº' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'total', header: 'Bs', money: true }, { key: 'estado', header: 'Estado', badge: true }]} /></Card>
        <div>
          <Card title={h.nro || 'Nuevo ingreso'} right={<Badge v={h.estado} />}>
            <div className="grid">
              <DateField label="Fecha de recepción" req value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} disabled={!editable} />
              <SelectField label="Tipo de ingreso" req value={h.tipo_doc} onChange={(v) => setH({ ...h, tipo_doc: v })} disabled={!editable} options={meta?.tipos_ingreso ?? []} />
              <TextField label="Nº orden de compra / contrato" req={compra} value={h.nro_doc} onChange={(v) => setH({ ...h, nro_doc: v })} disabled={!editable} />
              <TextField label="Nº preventivo" value={h.preventivo} onChange={(v) => setH({ ...h, preventivo: v })} disabled={!editable} />
              <SelectField label="Proveedor" req={compra} value={h.proveedor} onChange={(v) => setH({ ...h, proveedor: v })} disabled={!editable} options={(meta?.proveedores ?? []).map((p) => p.razon_social)} />
              <TextField label="Factura / nota de remisión" value={h.factura} onChange={(v) => setH({ ...h, factura: v })} disabled={!editable} />
              <TextField label="Nº memorándum de comisión" value={h.nro_memo} onChange={(v) => setH({ ...h, nro_memo: v })} disabled={!editable} />
              <SelectField label="Comisión de recepción 1" value={h.comision1} onChange={(v) => setH({ ...h, comision1: v })} disabled={!editable} options={(meta?.funcionarios ?? []).map((f) => f.nombre)} />
              <SelectField label="Comisión de recepción 2" value={h.comision2} onChange={(v) => setH({ ...h, comision2: v })} disabled={!editable} options={(meta?.funcionarios ?? []).map((f) => f.nombre)} />
              <SelectField label="Unidad" value={h.unidad} onChange={(v) => setH({ ...h, unidad: v })} disabled={!editable} options={(meta?.unidades ?? []).map((u) => u.nombre)} />
              <TextField label="Fuente de financiamiento" value={h.fuente_fin} onChange={(v) => setH({ ...h, fuente_fin: v })} disabled={!editable} />
              <AreaField className="span-all" label="Observaciones" value={h.observaciones} onChange={(v) => setH({ ...h, observaciones: v })} disabled={!editable} />
            </div>
          </Card>
          <Card title="Activos recibidos" right={<b>Total: Bs {fmt2(total)} · valor mínimo de activo: Bs {meta?.config.ValorMinimo}</b>}>
            <div className="table-wrap"><table className="t"><thead><tr><th>#</th><th>Cuenta contable</th><th>Auxiliar (tipo de activo)</th><th>Descripción</th><th>Unid.</th><th className="num">Cantidad</th><th className="num">P. unit. Bs</th><th className="num">Total</th><th className="num">Codif.</th><th /></tr></thead>
              <tbody>{items.map((it, i) => {
                const set = (k: string, v: any) => setItems(items.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
                return (
                  <tr key={i}><td className="ctr">{i + 1}</td>
                    <td><select disabled={!editable} value={it.id_cta} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, id_cta: e.target.value, id_aux: '' } : x)))}><option value="" />{optsCta(meta).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></td>
                    <td><select disabled={!editable || !it.id_cta} value={it.id_aux} onChange={(e) => set('id_aux', e.target.value)}><option value="" />{optsAux(meta, it.id_cta).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></td>
                    <td><input disabled={!editable} value={it.descripcion ?? ''} onChange={(e) => set('descripcion', e.target.value)} /></td>
                    <td style={{ width: 80 }}><input disabled={!editable} value={it.unidad ?? ''} onChange={(e) => set('unidad', e.target.value)} /></td>
                    <td style={{ width: 90 }}><input type="number" disabled={!editable} value={it.cantidad} onChange={(e) => set('cantidad', e.target.value)} /></td>
                    <td style={{ width: 110 }}><input type="number" disabled={!editable} value={it.precio_unit} onChange={(e) => set('precio_unit', e.target.value)} /></td>
                    <td className="num">{fmt2((Number(it.cantidad) || 0) * (Number(it.precio_unit) || 0))}</td><td className="num">{it.cant_codif}</td>
                    <td>{editable && !it.cant_codif && <button className="sm danger" onClick={() => setItems(items.filter((_, j) => j !== i))}>×</button>}</td></tr>);
              })}</tbody></table></div>
            {editable && <div style={{ marginTop: 6 }}><button className="sm" onClick={() => setItems([...items, lin()])}>+ Agregar línea</button></div>}
          </Card>
          <div className="row">
            {editable && <button className="primary" disabled={busy} onClick={guardar}>Guardar ingreso</button>}
            {h.nro && editable && <button className="ok" onClick={() => nav(`/activos/codificar?ing=${nroUrl(h.nro)}`)}>Ir a codificación</button>}
            {h.nro && <button onClick={() => abrirDocumento('af-memo-comision', h.nro)}>Memorándum de comisión</button>}
            {h.nro && <button onClick={() => abrirDocumento('af-acta-conformidad', h.nro)}>Acta de conformidad</button>}
            {h.nro && <button onClick={() => abrirDocumento('af-form-ingreso', h.nro)}>Formulario de ingreso</button>}
          </div>
        </div>
      </div>
    </>
  );
}
