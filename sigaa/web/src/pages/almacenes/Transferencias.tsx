import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, ItemsGrid, PageHead, SelectField, useAction, useLoad, useUi } from '../../ui';
import { codeOf, nroUrl, useAlmMeta, useItems } from './common';

const vacio = () => ({ nro: '', fecha: hoy(), bod_origen: '', bod_destino: '', entrega: '', recibe: '', motivo: '', estado: '', total: 0 });
const linea = () => ({ item: '', cantidad: '' });

export default function AlmTransferencias() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useAlmMeta();
  const { data: lista, reload } = useLoad<any[]>(() => get('/alm/transferencias'));
  const { data: funcs } = useLoad<any[]>(() => get('/maestros/funcionarios'));
  const [h, setH] = useState<any>(vacio());
  const [items, setItems] = useState<any[]>([linea()]);
  const [run, busy] = useAction();
  const { Lista, listId } = useItems('');
  const editable = puede('alm') && (!h.nro || h.estado === 'REGISTRADA');
  const cargar = (nro: string) => run(async () => {
    const d = await get(`/alm/transferencias/${nroUrl(nro)}`);
    setH({ ...vacio(), ...d });
    setItems(d.items.map((x: any) => ({ item: `${x.cod_item} - ${x.descripcion}`, cantidad: x.cantidad })));
  });
  const payload = () => ({ ...h, items: items.filter((i) => i.item).map((i) => ({ cod_item: codeOf(i.item), cantidad: Number(i.cantidad) })) });
  const bods = (meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }));
  const nombres = (funcs ?? []).map((f) => f.nombre);
  return (
    <>
      <PageHead title="Transferencia de bienes entre bodegas" sub="Salida de la bodega de origen e ingreso a la de destino, conservando lote, vencimiento y costo">
        {puede('alm') && <button className="primary" onClick={() => { setH(vacio()); setItems([linea()]); }}>Nueva transferencia</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: 'minmax(250px,320px) minmax(0,1fr)' }}>
        <Card title="Transferencias"><DataTable rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === h.nro} cols={[{ key: 'nro', header: 'Nº' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'total', header: 'Bs', money: true }, { key: 'estado', header: 'Estado', badge: true }]} /></Card>
        <div>
          <Card title={h.nro || 'Nueva transferencia'} right={<Badge v={h.estado} />}>
            <div className="grid">
              <DateField label="Fecha" req value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} disabled={!editable} />
              <SelectField label="Bodega de origen" req value={h.bod_origen} onChange={(v) => setH({ ...h, bod_origen: v })} disabled={!editable} options={bods} />
              <SelectField label="Bodega de destino" req value={h.bod_destino} onChange={(v) => setH({ ...h, bod_destino: v })} disabled={!editable} options={bods} />
              <SelectField label="Entrega (funcionario)" req value={h.entrega} onChange={(v) => setH({ ...h, entrega: v })} disabled={!editable} options={nombres} />
              <SelectField label="Recibe (funcionario)" req value={h.recibe} onChange={(v) => setH({ ...h, recibe: v })} disabled={!editable} options={nombres} />
              <AreaField className="span-all" label="Motivo de la transferencia" req value={h.motivo} onChange={(v) => setH({ ...h, motivo: v })} disabled={!editable} />
            </div>
          </Card>
          <Card title="Ítems a transferir" right={<b>Total: Bs {fmt2(h.total)}</b>}>
            <Lista />
            <ItemsGrid disabled={!editable} rows={items} onChange={setItems} vacio={linea} cols={[{ key: 'item', header: 'Ítem (código - descripción)', list: listId, width: '65%' }, { key: 'cantidad', header: 'Cantidad', type: 'number', num: true }]} />
          </Card>
          <div className="row">
            {editable && <button className="primary" disabled={busy} onClick={() => run(async () => { const r = await post('/alm/transferencias', payload()); await cargar(r.nro); await reload(); }, 'Transferencia guardada.')}>Guardar</button>}
            {puede('alm') && h.estado === 'REGISTRADA' && <button className="ok" disabled={busy} onClick={async () => { if (await ui.confirm(`¿Ejecutar la transferencia ${h.nro} por Bs ${fmt2(h.total)}?`)) run(async () => { await post('/alm/transferencias', payload()); await post(`/alm/transferencias/${nroUrl(h.nro)}/ejecutar`); await cargar(h.nro); await reload(); }, 'Transferencia ejecutada.'); }}>Ejecutar</button>}
            {h.nro && <button onClick={() => abrirDocumento('alm-acta-transferencia', h.nro)}>Acta de transferencia</button>}
          </div>
        </div>
      </div>
    </>
  );
}
