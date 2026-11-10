import { useState } from 'react';
import { get } from '../../api';
import { Card, DataTable, PageHead, SelectField, TextField, useLoad } from '../../ui';

export default function ComVales() {
  const [f, setF] = useState<Record<string, string>>({});
  const { data: vales } = useLoad<any[]>(() => get('/com/vales', { ...f, limite: 1000 }), [JSON.stringify(f)]);
  const { data: res } = useLoad<any>(() => get('/com/resumen-vales'));
  return (
    <>
      <PageHead title="Registro de vales" sub="Un registro por vale: Disponible → Entregado → Utilizado (o Devuelto, Anulado, Vencido, Extraviado)" />
      <Card title="Resumen">
        <DataTable rows={res?.lista ?? []} cols={[{ key: 'combustible', header: 'Combustible' }, { key: 'corte', header: 'Corte Bs', num: true }, { key: 'Disponible', header: 'Disponibles', num: true }, { key: 'Entregado', header: 'Entregados', num: true }, { key: 'Utilizado', header: 'Utilizados', num: true }, { key: 'Anulado', header: 'Anulados', num: true }, { key: 'Vencido', header: 'Vencidos', num: true }, { key: 'Extraviado', header: 'Extraviados', num: true }]} />
      </Card>
      <Card>
        <div className="row">
          <SelectField label="Estado" value={f.estado} onChange={(v) => setF({ ...f, estado: v })} options={['Disponible', 'Entregado', 'Utilizado', 'Anulado', 'Vencido', 'Extraviado']} />
          <SelectField label="Combustible" value={f.combustible} onChange={(v) => setF({ ...f, combustible: v })} options={['Gasolina', 'Diésel', 'GNV']} />
          <SelectField label="Corte" value={f.corte} onChange={(v) => setF({ ...f, corte: v })} options={['30', '50', '100']} />
          <TextField label="Nº de vale" value={f.nro} onChange={(v) => setF({ ...f, nro: v })} />
          <TextField label="Placa" value={f.placa} onChange={(v) => setF({ ...f, placa: v })} />
          <TextField label="Nº de emisión" value={f.nro_emision} onChange={(v) => setF({ ...f, nro_emision: v })} />
        </div>
      </Card>
      <DataTable maxHeight="60vh" rows={vales ?? []} cols={[{ key: 'nro_vale', header: 'Nº vale', num: true }, { key: 'proveedor', header: 'Proveedor' }, { key: 'combustible', header: 'Comb.' }, { key: 'corte', header: 'Corte', num: true }, { key: 'estado', header: 'Estado', badge: true }, { key: 'nro_emision', header: 'Emisión' }, { key: 'placa', header: 'Placa' }, { key: 'conductor', header: 'Conductor' }, { key: 'fecha_entrega', header: 'F. entrega', date: true }, { key: 'fecha_estado', header: 'F. estado', date: true }, { key: 'conciliacion', header: 'Conciliación' }, { key: 'observaciones', header: 'Observaciones' }]} />
      <small className="muted">{vales?.length ?? 0} vale(s) (máx. 1.000 por consulta)</small>
    </>
  );
}
