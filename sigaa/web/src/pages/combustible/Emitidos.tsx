import { useState } from 'react';
import { abrirDocumento, fmt2, get } from '../../api';
import { Badge, Card, DataTable, DateField, Kpi, Modal, PageHead, SelectField, TextField, useLoad } from '../../ui';

/** Visor de vales emitidos: una fila por emisión (solicitud) con los datos principales. */
export default function ComEmitidos() {
  const [f, setF] = useState<Record<string, string>>({});
  const [ver, setVer] = useState<any>();
  const { data: ems } = useLoad<any[]>(() => get('/com/emisiones', f), [JSON.stringify(f)]);
  const lista = (ems ?? []).filter((e) => !f.texto || [e.nro, e.conductor, e.unidad, e.solicitante, e.placa].some((x) => String(x ?? '').toLowerCase().includes(f.texto.toLowerCase())));
  const vigentes = lista.filter((e) => e.estado !== 'Anulado');
  const monto = vigentes.reduce((t, e) => t + Number(e.monto || 0), 0);
  const litros = vigentes.reduce((t, e) => t + Number(e.litros || 0), 0);
  const nVales = vigentes.reduce((t, e) => t + Number(e.cant_vales || 0), 0);
  const detalle = async (e: any) => setVer(await get(`/com/emisiones/${encodeURIComponent(e.nro)}`));
  return (
    <>
      <PageHead title="Vales emitidos" sub="Visor de emisiones (solicitud y vale): quién recibió los vales, para qué vehículo, por cuánto y en qué estado está el descargo" />
      <div className="kpis">
        <Kpi mod="com" label="Emisiones" value={vigentes.length} />
        <Kpi mod="com" label="Vales entregados" value={nVales} />
        <Kpi mod="com" label="Monto emitido (Bs)" value={fmt2(monto)} />
        <Kpi mod="com" label="Litros equivalentes" value={fmt2(litros)} />
      </div>
      <Card>
        <div className="row">
          <DateField label="Desde" value={f.desde ?? ''} onChange={(v) => setF({ ...f, desde: v })} />
          <DateField label="Hasta" value={f.hasta ?? ''} onChange={(v) => setF({ ...f, hasta: v })} />
          <SelectField label="Estado" value={f.estado} onChange={(v) => setF({ ...f, estado: v })} options={['Emitido', 'Descargado', 'Anulado']} />
          <TextField label="Placa / código" value={f.placa} onChange={(v) => setF({ ...f, placa: v })} />
          <TextField label="Buscar (Nº, conductor, unidad…)" value={f.texto} onChange={(v) => setF({ ...f, texto: v })} />
        </div>
      </Card>
      <DataTable maxHeight="62vh" rows={lista} onRow={detalle} empty="No hay emisiones con ese criterio."
        cols={[{ key: 'nro', header: 'Nº solicitud' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'placa', header: 'Placa / puesto' }, { key: 'conductor', header: 'Conductor' }, { key: 'unidad', header: 'Unidad' }, { key: 'combustible', header: 'Comb.' },
          { key: 'cant_vales', header: 'Vales', num: true }, { key: 'monto', header: 'Monto Bs', money: true }, { key: 'litros', header: 'Litros', num: true }, { key: 'hasta', header: 'Periodo hasta', date: true }, { key: 'estado', header: 'Estado', render: (r) => <Badge v={r.estado} /> },
          { key: 'pdf', header: '', render: (r) => <button className="sm" onClick={(ev) => { ev.stopPropagation(); abrirDocumento('com-vale', r.nro); }}>Vale PDF</button> }]} />
      <small className="muted">{lista.length} emisión(es). Pulse una fila para ver los vales entregados.</small>
      {ver && (
        <Modal wide title={`Emisión ${ver.nro}`} onClose={() => setVer(undefined)} footer={<><button onClick={() => abrirDocumento('com-vale', ver.nro)}>Vale con QR (PDF)</button><button onClick={() => setVer(undefined)}>Cerrar</button></>}>
          <p><b>{ver.conductor}</b> · {ver.placa} — {ver.descripcion_destino} · {ver.unidad}</p>
          <p className="muted">Apertura: {ver.apertura} {ver.desc_apertura} · Periodo: {ver.desde} al {ver.hasta} · Estado: {ver.estado}{ver.nro_descargo ? ` · Descargo ${ver.nro_descargo}` : ''}</p>
          <DataTable rows={ver.vales ?? []} cols={[{ key: 'nro_vale', header: 'Nº vale', num: true }, { key: 'combustible', header: 'Comb.' }, { key: 'corte', header: 'Corte Bs', num: true }, { key: 'estado', header: 'Estado', render: (r) => <Badge v={r.estado} /> }]} />
        </Modal>
      )}
    </>
  );
}
