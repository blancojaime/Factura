import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Card, DataTable, DateField, ItemsGrid, PageHead, SelectField, TextField, useAction, useLoad, useUi } from '../../ui';
import { useComMeta } from './common';

const lin = () => ({ corte: '', desde: '', hasta: '' });
export default function ComRecepcion() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta, reload: reMeta } = useComMeta();
  const { data: lotes, reload } = useLoad<any[]>(() => get('/com/lotes'));
  const [h, setH] = useState<any>({ fecha: hoy(), nro_contrato: '', factura: '', fecha_factura: '', nota_ref: '', comprobante: '', observaciones: '' });
  const [filas, setFilas] = useState<any[]>([lin()]);
  const [run, busy] = useAction();
  const ct = meta?.contratos.find((c) => c.nro === h.nro_contrato);
  const cant = filas.reduce((t, f) => t + (Number(f.hasta) >= Number(f.desde) && f.desde ? Number(f.hasta) - Number(f.desde) + 1 : 0), 0);
  const monto = filas.reduce((t, f) => t + (Number(f.hasta) >= Number(f.desde) && f.desde ? (Number(f.hasta) - Number(f.desde) + 1) * Number(f.corte || 0) : 0), 0);
  const registrar = () => run(async () => {
    const r = await post('/com/recepciones', { ...h, filas: filas.filter((f) => f.corte || f.desde || f.hasta).map((f) => ({ corte: Number(f.corte), desde: Number(f.desde), hasta: Number(f.hasta) })) });
    ui.ok(`Ingreso ${r.nro_ingreso} registrado: ${r.cantidad} vales por Bs ${fmt2(r.monto)}`);
    abrirDocumento('com-nota-ingreso', r.nro_ingreso);
    setFilas([lin()]); setH({ ...h, factura: '', fecha_factura: '', nota_ref: '', comprobante: '', observaciones: '' });
    reload(); reMeta();
  });
  return (
    <>
      <PageHead title="Recepción de vales — ingreso a almacén" sub="Registre cada lote de vales recibido del proveedor (prepago o postpago) con su numeración" />
      <Card title="1. Datos del contrato y documentos">
        <div className="grid">
          <DateField label="Fecha de recepción" req value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} />
          <SelectField label="Nº de contrato" req value={h.nro_contrato} onChange={(v) => setH({ ...h, nro_contrato: v })} options={(meta?.contratos ?? []).filter((c) => c.estado === 'Vigente').map((c) => ({ value: c.nro, label: `${c.nro} · ${c.combustible}` }))} />
          <TextField label="Factura Nº" req={ct?.modalidad === 'Prepago'} value={h.factura} onChange={(v) => setH({ ...h, factura: v })} hint={ct?.modalidad === 'Prepago' ? 'Obligatoria en contratos PREPAGO' : ''} />
          <DateField label="Fecha de la factura" value={h.fecha_factura} onChange={(v) => setH({ ...h, fecha_factura: v })} />
          <TextField label="Nota / documento de referencia" value={h.nota_ref} onChange={(v) => setH({ ...h, nota_ref: v })} />
          <TextField label="Comprobante" value={h.comprobante} onChange={(v) => setH({ ...h, comprobante: v })} />
        </div>
        {ct && <div className="alert info" style={{ marginTop: 10 }}>Proveedor: <b>{ct.proveedor}</b> · Modalidad: <b>{ct.modalidad}</b> · Combustible: <b>{ct.combustible}</b> · Saldo del contrato: <b>Bs {fmt2(ct.saldo)}</b> · Vigencia {ct.vigencia_desde} a {ct.vigencia_hasta}</div>}
        <AreaField label="Observaciones" value={h.observaciones} onChange={(v) => setH({ ...h, observaciones: v })} />
      </Card>
      <Card title="2. Vales recibidos (una fila por corte y rango de numeración)" right={<b>{cant} vales · Bs {fmt2(monto)}</b>}>
        <ItemsGrid rows={filas} onChange={setFilas} vacio={lin} cols={[{ key: 'corte', header: 'Corte (Bs)', type: 'select', options: (meta?.cortes ?? []).map(String), width: 140 }, { key: 'desde', header: 'Nº desde', type: 'number', num: true }, { key: 'hasta', header: 'Nº hasta', type: 'number', num: true }]} />
      </Card>
      {puede('com') && <button className="primary" disabled={busy} onClick={registrar}>Registrar ingreso a almacén</button>}
      <Card title="Lotes recibidos">
        <DataTable maxHeight="45vh" rows={lotes ?? []} cols={[{ key: 'nro_ingreso', header: 'Ingreso' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'nro_contrato', header: 'Contrato' }, { key: 'combustible', header: 'Comb.' }, { key: 'corte', header: 'Corte', num: true }, { key: 'desde', header: 'Desde', num: true }, { key: 'hasta', header: 'Hasta', num: true }, { key: 'cantidad', header: 'Cant.', num: true }, { key: 'monto', header: 'Monto Bs', money: true }, { key: 'factura', header: 'Factura' }, { key: 'p', header: '', render: (r) => <button className="sm" onClick={() => abrirDocumento('com-nota-ingreso', r.nro_ingreso)}>Nota</button> }]} />
      </Card>
    </>
  );
}
