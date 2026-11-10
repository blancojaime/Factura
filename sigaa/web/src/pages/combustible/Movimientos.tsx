import { useState } from 'react';
import { abrirDocumento, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { Card, DateField, NumField, PageHead, SelectField, Tabs, TextField, useAction, useLoad, useUi } from '../../ui';
import { useComMeta } from './common';

export default function ComMovimientos() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useComMeta();
  const { data: emis, reload } = useLoad<any[]>(() => get('/com/emisiones', { estado: 'Emitido' }));
  const [t, setT] = useState<'rango' | 'emision'>('rango');
  const [f, setF] = useState<any>({ fecha: hoy(), accion: 'Devolución', proveedor: '', combustible: '', corte: '', desde: '', hasta: '', motivo: '' });
  const [an, setAn] = useState({ nro: '', motivo: '' });
  const [run, busy] = useAction();
  return (
    <>
      <PageHead title="Devolución, anulación, vencimiento o extravío de vales" sub="Cada operación genera un acta y queda registrada en el kardex" />
      <Tabs value={t} onChange={setT} items={[{ id: 'rango', label: 'Por rango de numeración' }, { id: 'emision', label: 'Anular una emisión completa' }]} />
      {t === 'rango' && (
        <Card title="Movimiento por rango de numeración">
          <div className="grid">
            <DateField label="Fecha" req value={f.fecha} onChange={(v) => setF({ ...f, fecha: v })} />
            <SelectField label="Acción" blank={false} req value={f.accion} onChange={(v) => setF({ ...f, accion: v })} options={['Devolución', 'Anulación', 'Vencimiento', 'Extravío']} hint={{ Devolución: 'Requiere vales Entregados', Anulación: 'Requiere vales Disponibles', Vencimiento: 'Requiere vales Disponibles', Extravío: 'Vales Disponibles o Entregados' }[f.accion as string]} />
            <SelectField label="Proveedor de los vales" req value={f.proveedor} onChange={(v) => setF({ ...f, proveedor: v })} options={[...new Set((meta?.contratos ?? []).map((c) => c.proveedor))]} />
            <SelectField label="Combustible" req value={f.combustible} onChange={(v) => setF({ ...f, combustible: v })} options={['Gasolina', 'Diésel', 'GNV']} />
            <SelectField label="Corte (Bs)" req value={f.corte} onChange={(v) => setF({ ...f, corte: v })} options={(meta?.cortes ?? []).map(String)} />
            <NumField label="Nº desde" req value={f.desde} onChange={(v) => setF({ ...f, desde: v ?? '' })} />
            <NumField label="Nº hasta" req value={f.hasta} onChange={(v) => setF({ ...f, hasta: v ?? '' })} />
            <TextField className="span-all" label="Motivo" req value={f.motivo} onChange={(v) => setF({ ...f, motivo: v })} />
          </div>
          {puede('com') && <div style={{ marginTop: 12 }}><button className="primary" disabled={busy} onClick={() => run(async () => { const r = await post('/com/movimientos', { ...f, corte: Number(f.corte), desde: Number(f.desde), hasta: Number(f.hasta) }); ui.ok(`${f.accion}: ${r.cantidad} vale(s) procesado(s) (acta ${r.doc}).`); abrirDocumento('com-acta-movimiento', r.doc); })}>Procesar movimiento</button></div>}
        </Card>
      )}
      {t === 'emision' && (
        <Card title="Anular una emisión completa">
          <p className="muted">Devuelve los vales al almacén (y revierte la carga del turril si corresponde). Solo emisiones en estado Emitido, es decir, sin descargo.</p>
          <div className="grid">
            <SelectField label="Nº de emisión" req value={an.nro} onChange={(v) => setAn({ ...an, nro: v })} options={(emis ?? []).map((e) => ({ value: e.nro, label: `${e.nro} · ${e.placa} · Bs ${e.monto}` }))} />
            <TextField className="span2" label="Motivo de la anulación" req value={an.motivo} onChange={(v) => setAn({ ...an, motivo: v })} />
          </div>
          {puede('com') && <div style={{ marginTop: 12 }}><button className="danger" disabled={busy} onClick={async () => { if (await ui.confirm(`¿Anular la emisión ${an.nro}? Los vales volverán al almacén.`)) run(async () => { await post(`/com/emisiones/${encodeURIComponent(an.nro)}/anular`, { motivo: an.motivo }); setAn({ nro: '', motivo: '' }); reload(); }, 'Emisión anulada.'); }}>Anular emisión</button></div>}
        </Card>
      )}
    </>
  );
}
