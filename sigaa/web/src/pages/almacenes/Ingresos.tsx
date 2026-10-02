import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, ItemsGrid, PageHead, SelectField, TextField, useAction, useLoad, useUi } from '../../ui';
import { codeOf, nroUrl, useAlmMeta, useItems } from './common';

const vacio = () => ({ nro: '', fecha: hoy(), cod_bod: '', tipo: '', proveedor: '', nro_oc: '', plazo_entrega: '', factura: '', fecha_factura: '', unidad: '', preventivo: '', nro_pse: '', proyecto: '', fuente: '', partida: '', comision: '', obs_plazo: '', estado: '' });
const linea = () => ({ item: '', cantidad: '', precio_unit: '', vencimiento: '', lote: '', marca: '' });

export default function AlmIngresos() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useAlmMeta();
  const [est, setEst] = useState('');
  const { data: lista, reload } = useLoad<any[]>(() => get('/alm/ingresos', { estado: est }), [est]);
  const { data: provs } = useLoad<any[]>(() => get('/maestros/proveedores'));
  const { data: unids } = useLoad<any[]>(() => get('/maestros/unidades'));
  const { data: proys } = useLoad<any[]>(() => get('/maestros/proyectos'));
  const [h, setH] = useState<any>(vacio());
  const [items, setItems] = useState<any[]>([linea()]);
  const [docs, setDocs] = useState<any[]>([]);
  const [run, busy] = useAction();
  const { Lista, listId, porCodigo } = useItems(h.cod_bod);
  const editable = puede('alm') && (!h.nro || h.estado === 'REGISTRADO');
  const total = items.reduce((t, i) => t + (Number(i.cantidad) || 0) * (Number(i.precio_unit) || 0), 0);

  const cargar = (nro: string) => run(async () => {
    const d = await get(`/alm/ingresos/${nroUrl(nro)}`);
    setH({ ...vacio(), ...d });
    setItems(d.items.map((x: any) => ({ item: `${x.cod_item} - ${x.descripcion}`, cantidad: x.cantidad, precio_unit: x.precio_unit, vencimiento: x.vencimiento ?? '', lote: x.lote ?? '', marca: x.marca ?? '' })));
    setDocs(d.docs.map((x: any) => ({ documento: x.documento, estado: x.estado ?? '' })));
  });
  const nuevo = () => { setH(vacio()); setItems([linea()]); setDocs([]); };
  const cargarDocs = (tipo: string) => run(async () => { setDocs(await get(`/alm/ingresos/docs/${encodeURIComponent(tipo)}`)); });
  const payload = () => ({ ...h, items: items.filter((i) => i.item).map((i) => ({ cod_item: codeOf(i.item), cantidad: Number(i.cantidad), precio_unit: Number(i.precio_unit), vencimiento: i.vencimiento || null, lote: i.lote, marca: i.marca })), docs });
  const guardar = () => run(async () => {
    const r = await post('/alm/ingresos', payload());
    setH({ ...h, nro: r.nro, estado: 'REGISTRADO' });
    await reload();
    ui.ok(`Ingreso ${r.nro} guardado. Verifique los documentos de respaldo y confirme el ingreso.`);
  });
  const confirmar = async () => {
    if (!(await ui.confirm(`¿Confirmar el ingreso ${h.nro} por Bs ${fmt2(total)}?\nSe darán de alta las existencias en la bodega y no podrá modificarse.`))) return;
    run(async () => { await post('/alm/ingresos', payload()); await post(`/alm/ingresos/${nroUrl(h.nro)}/confirmar`); await cargar(h.nro); await reload(); }, 'Ingreso confirmado: existencias disponibles.');
  };
  const anular = async () => {
    const motivo = await ui.prompt('Motivo de la anulación del ingreso:');
    if (!motivo) return;
    run(async () => { await post(`/alm/ingresos/${nroUrl(h.nro)}/anular`, { motivo }); await cargar(h.nro); await reload(); }, 'Ingreso anulado.');
  };
  const compra = String(h.tipo).startsWith('COMPRA');
  return (
    <>
      <PageHead title="Ingreso de bienes de consumo a almacén (CGI)" sub="Control General de Ingresos · verificación de documentos · registro en kardex por lotes">
        {puede('alm') && <button className="primary" onClick={nuevo}>Nuevo CGI</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: 'minmax(260px,320px) minmax(0,1fr)' }}>
        <Card title="Ingresos registrados" right={<select style={{ width: 130 }} value={est} onChange={(e) => setEst(e.target.value)}><option value="">Todos</option><option>REGISTRADO</option><option>INGRESADO</option><option>ANULADO</option></select>}>
          <DataTable maxHeight="70vh" rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === h.nro} cols={[{ key: 'nro', header: 'CGI' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'total', header: 'Bs', money: true }, { key: 'estado', header: 'Estado', badge: true }]} />
        </Card>
        <div>
          <Card title={h.nro ? `${h.nro}` : 'Nuevo ingreso'} right={<Badge v={h.estado} />}>
            <div className="grid">
              <DateField label="Fecha de recepción" req value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} disabled={!editable} />
              <SelectField label="Bodega" req value={h.cod_bod} onChange={(v) => setH({ ...h, cod_bod: v })} disabled={!editable} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
              <SelectField label="Tipo de ingreso" req value={h.tipo} onChange={(v) => { setH({ ...h, tipo: v }); if (!h.nro) cargarDocs(v); }} disabled={!editable} options={meta?.tipos_ingreso ?? []} />
              <SelectField label="Proveedor" req={compra} value={h.proveedor} onChange={(v) => setH({ ...h, proveedor: v })} disabled={!editable} options={(provs ?? []).map((p) => p.razon_social)} />
              <TextField label="Nº Orden de compra / contrato" req={compra} value={h.nro_oc} onChange={(v) => setH({ ...h, nro_oc: v })} disabled={!editable} />
              <DateField label="Plazo de entrega (fecha límite)" value={h.plazo_entrega} onChange={(v) => setH({ ...h, plazo_entrega: v })} disabled={!editable} />
              <TextField label="Factura / nota de remisión Nº" req={h.tipo && !String(h.tipo).startsWith('TRANSF') && !String(h.tipo).startsWith('AJUSTE')} value={h.factura} onChange={(v) => setH({ ...h, factura: v })} disabled={!editable} />
              <DateField label="Fecha de la factura" value={h.fecha_factura} onChange={(v) => setH({ ...h, fecha_factura: v })} disabled={!editable} />
              <SelectField label="Unidad solicitante" value={h.unidad} onChange={(v) => setH({ ...h, unidad: v })} disabled={!editable} options={(unids ?? []).map((u) => u.nombre)} />
              <TextField label="Nº preventivo" value={h.preventivo} onChange={(v) => setH({ ...h, preventivo: v })} disabled={!editable} />
              <TextField label="Nº almacén sin existencia (PSE)" value={h.nro_pse} onChange={(v) => setH({ ...h, nro_pse: v })} disabled={!editable} />
              <SelectField label="Proyecto / destino" value={h.proyecto} onChange={(v) => setH({ ...h, proyecto: v })} disabled={!editable} options={(proys ?? []).map((p) => p.nombre)} />
              <TextField label="Fuente de financiamiento / organismo" value={h.fuente} onChange={(v) => setH({ ...h, fuente: v })} disabled={!editable} />
              <SelectField label="Partida presupuestaria" value={h.partida} onChange={(v) => setH({ ...h, partida: v })} disabled={!editable} options={(meta?.partidas ?? []).map((p) => ({ value: p.partida, label: `${p.partida} - ${p.descripcion}` }))} />
              <TextField className="span2" label="Comisión / responsable de recepción" value={h.comision} onChange={(v) => setH({ ...h, comision: v })} disabled={!editable} />
              <AreaField className="span-all" label="Observaciones / justificación de entrega fuera de plazo" value={h.obs_plazo} onChange={(v) => setH({ ...h, obs_plazo: v })} disabled={!editable} />
            </div>
          </Card>
          <Card title="Detalle de bienes recibidos" right={<b>Total: Bs {fmt2(total)}</b>}>
            <Lista />
            <ItemsGrid disabled={!editable} rows={items} onChange={setItems} vacio={linea} cols={[
              { key: 'item', header: 'Ítem del catálogo (código - descripción)', list: listId, width: '36%' },
              { key: 'marca', header: 'Marca / caract.' },
              { key: 'cantidad', header: 'Cantidad', type: 'number', num: true, width: 90 },
              { key: 'precio_unit', header: 'P. unit. (Bs)', type: 'number', num: true, width: 100 },
              { key: 'vencimiento', header: 'Vencimiento', type: 'date', width: 140 },
              { key: 'lote', header: 'Lote / serie', width: 100 },
            ]} />
            {items.some((i) => porCodigo.get(codeOf(i.item))?.perecible === 'SI' && !i.vencimiento) && <div className="alert aviso" style={{ marginTop: 8 }}>Hay ítems perecibles sin fecha de vencimiento.</div>}
          </Card>
          <Card title="Documentación de respaldo (art. 13-IV · Manual 11.2) — (*) obligatorio">
            {docs.length === 0 && <div className="muted">Seleccione el tipo de ingreso para cargar la lista de documentos.</div>}
            {docs.map((d, i) => (
              <label key={i} className="row" style={{ gap: 8, padding: '3px 0' }}>
                <input type="checkbox" disabled={!editable} checked={String(d.estado).toUpperCase() === 'SI'} onChange={(e) => setDocs(docs.map((x, j) => (j === i ? { ...x, estado: e.target.checked ? 'SI' : 'NO' } : x)))} />
                <span>{d.documento}</span>
              </label>
            ))}
          </Card>
          <div className="row">
            {editable && <button className="primary" disabled={busy} onClick={guardar}>Guardar</button>}
            {puede('alm') && h.nro && h.estado === 'REGISTRADO' && <button className="ok" disabled={busy} onClick={confirmar}>Confirmar ingreso</button>}
            {puede('alm') && h.nro && h.estado !== 'ANULADO' && <button className="danger" disabled={busy} onClick={anular}>Anular</button>}
            {h.nro && <button onClick={() => abrirDocumento('alm-cgi', h.nro)}>Imprimir CGI</button>}
            {h.nro && <button onClick={() => abrirDocumento('alm-verif-docs', h.nro)}>Verificación de documentos</button>}
          </div>
        </div>
      </div>
    </>
  );
}
