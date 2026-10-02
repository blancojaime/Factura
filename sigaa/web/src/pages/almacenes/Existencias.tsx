import { useState } from 'react';
import { abrirDocumento, fmtDate, get, hoy, fmt2, fmtN } from '../../api';
import { Card, DataTable, DateField, PageHead, SelectField, TextField, useLoad, Badge } from '../../ui';
import { codeOf, useAlmMeta, useItems } from './common';

export default function AlmExistencias() {
  const { data: meta } = useAlmMeta();
  const [bod, setBod] = useState('');
  const [item, setItem] = useState('');
  const [desde, setDesde] = useState(`${hoy().slice(0, 4)}-01-01`);
  const [hasta, setHasta] = useState(hoy());
  const { Lista, listId } = useItems(bod);
  const { data: ex } = useLoad<any[]>(() => get('/alm/existencias', { bod }), [bod]);
  const cod = codeOf(item);
  const { data: kx } = useLoad<any[]>(() => (cod ? get('/alm/kardex', { bod, cod, desde, hasta }) : Promise.resolve([])), [bod, cod, desde, hasta]);
  const { data: lotes } = useLoad<any[]>(() => (cod && bod ? get('/alm/lotes', { bod, cod }) : Promise.resolve([])), [bod, cod]);
  return (
    <>
      <PageHead title="Existencias y kardex" sub="Kardex valorado por ítem (PEPS por lotes con prioridad al vencimiento)" />
      <Card>
        <div className="row">
          <SelectField label="Bodega" value={bod} onChange={setBod} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
          <TextField label="Ítem (código - descripción)" list={listId} value={item} onChange={setItem} className="span2" />
          <DateField label="Desde" value={desde} onChange={setDesde} />
          <DateField label="Hasta" value={hasta} onChange={setHasta} />
          <button disabled={!cod} onClick={() => abrirDocumento('alm-kardex', cod, { bodega: bod || 'TODAS', desde, hasta })}>PDF del kardex</button>
        </div>
        <Lista />
      </Card>
      {cod && (
        <Card title={`Kardex de ${item}`}>
          <DataTable maxHeight="45vh" rows={kx ?? []} cols={[
            { key: 'fecha', header: 'Fecha', date: true }, { key: 'documento', header: 'Documento' }, { key: 'detalle', header: 'Detalle' },
            { key: 'entCant', header: 'Entrada', num: true }, { key: 'entBs', header: 'Entrada Bs', money: true }, { key: 'salCant', header: 'Salida', num: true }, { key: 'salBs', header: 'Salida Bs', money: true },
            { key: 'saldoCant', header: 'Saldo', num: true }, { key: 'saldoBs', header: 'Saldo Bs', money: true }, { key: 'puProm', header: 'P.U. prom.', money: true },
          ]} />
          {lotes && lotes.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <h3>Lotes con saldo (orden de salida FEFO/PEPS)</h3>
              <DataTable rows={lotes} cols={[{ key: 'id_lote', header: 'Lote' }, { key: 'doc_origen', header: 'Ingreso' }, { key: 'fecha_ing', header: 'F. ingreso', date: true }, { key: 'vencimiento', header: 'Vence', date: true }, { key: 'saldo', header: 'Saldo', num: true }, { key: 'precio_unit', header: 'P. unit.', money: true }]} />
            </div>
          )}
        </Card>
      )}
      <Card title="Existencias actuales">
        <DataTable maxHeight="50vh" rows={ex ?? []} cols={[
          { key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' }, { key: 'bodega', header: 'Bodega' }, { key: 'unidad', header: 'Unidad' },
          { key: 'existencia', header: 'Existencia', num: true }, { key: 'stock_min', header: 'Mín.', num: true }, { key: 'valor', header: 'Valor Bs', money: true },
          { key: 'a', header: '', render: (r) => (Number(r.stock_min) > 0 && Number(r.existencia) <= Number(r.stock_min) ? <Badge v="PENDIENTE" /> : null) },
        ]} />
        <small className="muted">Valor total: Bs {fmt2((ex ?? []).reduce((t, r) => t + Number(r.valor), 0))} · {fmtN((ex ?? []).length)} ítems · {fmtDate(hoy())}</small>
      </Card>
    </>
  );
}
