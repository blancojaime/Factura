import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, ItemsGrid, PageHead, SelectField, TextField, useAction, useLoad, useUi } from '../../ui';
import { codeOf, nroUrl, useAlmMeta, useItems } from './common';

const vacio = () => ({ nro: '', fecha: hoy(), cod_bod: '', causal: '', responsable: '', justificacion: '', nro_ra: '', fecha_ra: '', estado: '', total: 0 });
const linea = () => ({ item: '', cantidad: '', id_lote: '' });
const DOCS: Record<string, string> = { ACTAVER: 'Acta de verificación', INFSOL: 'Informe de solicitud', INFTEC: 'Informe técnico', MEMOCOM: 'Memorándum de comisión', ACTADEST: 'Acta de destrucción', ACTAENT: 'Acta de entrega', REGBAJA: 'Registro de baja', CONVOC: 'Convocatoria SICOES' };

export default function AlmBajas() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useAlmMeta();
  const { data: lista, reload } = useLoad<any[]>(() => get('/alm/bajas'));
  const { data: funcs } = useLoad<any[]>(() => get('/maestros/funcionarios'));
  const [h, setH] = useState<any>(vacio());
  const [items, setItems] = useState<any[]>([linea()]);
  const [pasos, setPasos] = useState<any[]>([]);
  const [run, busy] = useAction();
  const { Lista, listId } = useItems(h.cod_bod);
  const nuevoExp = !h.nro;
  const enTramite = nuevoExp || h.estado === 'EN TRÁMITE';

  const cargar = (nro: string) => run(async () => {
    const d = await get(`/alm/bajas/${nroUrl(nro)}`);
    setH({ ...vacio(), ...d });
    setItems(d.items.map((x: any) => ({ item: `${x.cod_item} - ${x.descripcion}`, cantidad: x.cantidad, id_lote: x.id_lote ?? '' })));
    setPasos(d.pasos);
  });
  const cargarTramite = (causal: string) => run(async () => setPasos(await get('/alm/bajas/tramite', { causal })));
  const payload = () => ({ ...h, items: items.filter((i) => i.item).map((i) => ({ cod_item: codeOf(i.item), cantidad: Number(i.cantidad), id_lote: i.id_lote })), pasos: h.nro ? pasos.map((p) => ({ orden: p.orden, referencia: p.referencia, fecha: p.fecha, estado: p.estado, respaldo: p.respaldo })) : undefined });
  const guardar = () => run(async () => { const r = await post('/alm/bajas', payload()); await cargar(r.nro); await reload(); ui.ok(`Expediente ${r.nro} guardado.`); });
  const ejecutar = async () => {
    if (!(await ui.confirm(`¿Ejecutar la baja física y contable del expediente ${h.nro} por Bs ${fmt2(h.total)}?\nResolución Administrativa Nº ${h.nro_ra}\nLas existencias se descargarán del almacén y no podrá revertirse.`))) return;
    run(async () => { await post('/alm/bajas', payload()); const r = await post(`/alm/bajas/${nroUrl(h.nro)}/ejecutar`); await cargar(h.nro); await reload(); ui.ok(`Baja ejecutada por Bs ${fmt2(r.total)}. Imprima el Registro de baja para Contabilidad.`); });
  };
  const setP = (i: number, k: string, v: string) => setPasos(pasos.map((p, j) => (j === i ? { ...p, [k]: v } : p)));
  return (
    <>
      <PageHead title="Expediente de baja de bienes de consumo y disposición" sub="Causales del art. 30 · Trámite paso a paso: informe técnico, informe legal, resolución administrativa, baja y disposición">
        {puede('alm') && <button className="primary" onClick={() => { setH(vacio()); setItems([linea()]); setPasos([]); }}>Nuevo expediente</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: 'minmax(250px,320px) minmax(0,1fr)' }}>
        <Card title="Expedientes"><DataTable maxHeight="70vh" rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === h.nro} cols={[{ key: 'nro', header: 'Nº' }, { key: 'causal', header: 'Causal' }, { key: 'total', header: 'Bs', money: true }, { key: 'estado', header: 'Estado', badge: true }]} /></Card>
        <div>
          <Card title={h.nro || 'Nuevo expediente'} right={<Badge v={h.estado} />}>
            <div className="grid">
              <DateField label="Fecha de solicitud" req value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} disabled={!enTramite} />
              <SelectField label="Bodega" req value={h.cod_bod} onChange={(v) => setH({ ...h, cod_bod: v })} disabled={!enTramite} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
              <SelectField label="Causal de baja" req value={h.causal} onChange={(v) => { setH({ ...h, causal: v }); if (!h.nro) cargarTramite(v); }} disabled={!enTramite || !!h.nro} options={(meta?.causales ?? []).map((c) => ({ value: c.causal, label: `${c.causal} (grupo ${c.grupo})` }))} />
              <SelectField label="Responsable de la solicitud" req value={h.responsable} onChange={(v) => setH({ ...h, responsable: v })} disabled={!enTramite} options={(funcs ?? []).map((f) => f.nombre)} />
              <TextField label="Nº Resolución Administrativa" value={h.nro_ra} onChange={(v) => setH({ ...h, nro_ra: v })} disabled={h.estado === 'CONCLUIDO' || h.estado === 'ANULADO'} />
              <DateField label="Fecha de la Resolución" value={h.fecha_ra} onChange={(v) => setH({ ...h, fecha_ra: v })} disabled={h.estado === 'CONCLUIDO' || h.estado === 'ANULADO'} />
              <AreaField className="span-all" label="Justificación / descripción del hecho" req value={h.justificacion} onChange={(v) => setH({ ...h, justificacion: v })} disabled={!enTramite} />
            </div>
          </Card>
          <Card title="Bienes a dar de baja" right={<b>Total: Bs {fmt2(h.total)}</b>}>
            <Lista />
            <ItemsGrid disabled={!enTramite} rows={items} onChange={setItems} vacio={linea} cols={[{ key: 'item', header: 'Ítem (código - descripción)', list: listId, width: '55%' }, { key: 'id_lote', header: 'Lote (opcional)', width: 120 }, { key: 'cantidad', header: 'Cantidad a dar de baja', type: 'number', num: true, width: 140 }]} />
          </Card>
          <Card title="Trámite del expediente (marcar HECHO cada paso con su referencia y fecha) — (*) obligatorio">
            {pasos.length === 0 ? <div className="muted">Seleccione la causal para cargar el trámite.</div> : (
              <div className="table-wrap"><table className="t"><thead><tr><th>N°</th><th>Paso / documento</th><th style={{ width: 150 }}>Referencia</th><th style={{ width: 140 }}>Fecha</th><th style={{ width: 120 }}>Estado</th><th>Documento</th></tr></thead>
                <tbody>{pasos.map((p, i) => (
                  <tr key={p.orden}>
                    <td className="ctr">{p.orden}</td><td>{p.paso}</td>
                    <td><input disabled={!h.nro || h.estado === 'ANULADO'} value={p.referencia ?? ''} onChange={(e) => setP(i, 'referencia', e.target.value)} /></td>
                    <td><input type="date" disabled={!h.nro || h.estado === 'ANULADO'} value={p.fecha ?? ''} onChange={(e) => setP(i, 'fecha', e.target.value)} /></td>
                    <td><select disabled={!h.nro || h.estado === 'ANULADO' || p.clase === 'BAJA'} value={p.estado} onChange={(e) => setP(i, 'estado', e.target.value)}>{['PENDIENTE', 'HECHO', 'NO APLICA'].map((s) => <option key={s}>{s}</option>)}</select></td>
                    <td>{p.doc && h.nro && <button className="sm" onClick={() => abrirDocumento('alm-baja', h.nro, { doc: p.doc })}>{DOCS[p.doc] ?? p.doc}</button>}</td>
                  </tr>))}</tbody></table></div>
            )}
          </Card>
          <div className="row">
            {puede('alm') && h.estado !== 'ANULADO' && h.estado !== 'CONCLUIDO' && <button className="primary" disabled={busy} onClick={guardar}>Guardar expediente</button>}
            {puede('alm') && h.estado === 'EN TRÁMITE' && <button className="ok" disabled={busy} onClick={ejecutar}>Ejecutar baja</button>}
            {puede('alm') && h.estado === 'BAJA EJECUTADA' && <button className="ok" disabled={busy} onClick={() => run(async () => { await post('/alm/bajas', payload()); await post(`/alm/bajas/${nroUrl(h.nro)}/concluir`); await cargar(h.nro); await reload(); }, 'Expediente concluido.')}>Concluir expediente</button>}
            {puede('alm') && h.estado === 'EN TRÁMITE' && <button className="danger" disabled={busy} onClick={async () => { const m = await ui.prompt('Motivo de la anulación del expediente:'); if (m) run(async () => { await post(`/alm/bajas/${nroUrl(h.nro)}/anular`, { motivo: m }); await cargar(h.nro); await reload(); }, 'Expediente anulado.'); }}>Anular</button>}
          </div>
        </div>
      </div>
    </>
  );
}
