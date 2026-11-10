import { useState } from 'react';
import { abrirPdfPost, get } from '../../api';
import { useAuth } from '../../auth';
import { Card, DataTable, PageHead, SelectField, useAction, useLoad, useUi, Badge } from '../../ui';
import { optsEdif, useAfMeta } from './common';

export default function AfEtiquetas() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useAfMeta();
  const [soloPend, setSoloPend] = useState(true);
  const [edif, setEdif] = useState('');
  const { data: lista, reload } = useLoad<any[]>(() => get('/af/activos', { cod_edif: edif, limite: 2000 }), [edif]);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [run, busy] = useAction();
  const rows = (lista ?? []).filter((a) => a.situacion !== 'BAJA' && (!soloPend || a.etq_impresa !== 'SI'));
  const toggle = (c: string) => { const n = new Set(sel); n.has(c) ? n.delete(c) : n.add(c); setSel(n); };
  return (
    <>
      <PageHead title="Etiquetas (stickers) de activos fijos" sub="Hoja carta de 30 stickers (3 × 10): entidad, edificio, auxiliar y código del activo" />
      <Card>
        <div className="row">
          <SelectField label="Edificio" value={edif} onChange={setEdif} options={optsEdif(meta)} />
          <label className="row" style={{ gap: 6 }}><input type="checkbox" checked={soloPend} onChange={(e) => setSoloPend(e.target.checked)} /> Solo pendientes de impresión</label>
          <button onClick={() => setSel(new Set(rows.map((r) => r.codigo)))}>Marcar todo</button><button onClick={() => setSel(new Set())}>Desmarcar</button>
          {puede('af') && <button className="primary" disabled={busy || !sel.size} onClick={() => run(async () => { await abrirPdfPost('/af/stickers', { codigos: [...sel] }); setSel(new Set()); reload(); ui.ok('Stickers generados y marcados como impresos.'); })}>Generar stickers ({sel.size})</button>}
        </div>
      </Card>
      <DataTable maxHeight="62vh" rows={rows} onRow={(r) => toggle(r.codigo)} cols={[{ key: 's', header: '', render: (r) => <input type="checkbox" readOnly checked={sel.has(r.codigo)} /> }, { key: 'codigo', header: 'Código' }, { key: 'auxiliar', header: 'Auxiliar' }, { key: 'descripcion', header: 'Descripción' }, { key: 'edificio', header: 'Edificio' }, { key: 'etq_impresa', header: 'Sticker', render: (r) => <Badge v={r.etq_impresa === 'SI' ? 'HECHO' : 'PENDIENTE'} /> }]} />
      <small className="muted">{rows.length} activo(s)</small>
    </>
  );
}
