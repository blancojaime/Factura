import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post, fmtDate } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Card, DataTable, DateField, ItemsGrid, PageHead, SelectField, useConfirmable, useLoad } from '../../ui';
import { nroUrl } from './common';

const lin = () => ({ fecha: hoy(), ruta: '', lectura_salida: '', lectura_llegada: '', nro_vale: '', litros: '', factura: '', estacion: '' });
export default function ComDescargo() {
  const { puede } = useAuth();
  const { data: pend, reload: reP } = useLoad<any[]>(() => get('/com/emisiones', { estado: 'Emitido' }));
  const { data: desc, reload: reD } = useLoad<any[]>(() => get('/com/descargos'));
  const [em, setEm] = useState<any>(null);
  const [fecha, setFecha] = useState(hoy());
  const [lineas, setLineas] = useState<any[]>([lin()]);
  const [devolver, setDevolver] = useState(true);
  const [obs, setObs] = useState('');
  const [exec, busy] = useConfirmable();
  const elegir = async (nro: string) => {
    if (!nro) return setEm(null);
    const d = await get(`/com/emisiones/${nroUrl(nro)}`);
    setEm(d); setLineas([lin()]);
  };
  const vales = (em?.vales ?? []).filter((v: any) => v.estado === 'Entregado');
  const registrar = () => exec(async (confirmar) => post('/com/descargos', {
    nro_emision: em.nro, fecha, devolver_automaticamente: devolver, observaciones: obs, confirmar,
    lineas: lineas.filter((l) => l.fecha || l.litros || l.nro_vale).map((l) => ({ ...l, lectura_salida: l.lectura_salida === '' ? undefined : Number(l.lectura_salida), lectura_llegada: l.lectura_llegada === '' ? undefined : Number(l.lectura_llegada), nro_vale: l.nro_vale === '' ? null : Number(l.nro_vale), litros: l.litros === '' ? undefined : Number(l.litros) })),
  }), (r) => `Descargo ${r.data.nro} registrado (${r.data.estado})`).then((r) => { if (r?.ok) { setEm(null); reP(); reD(); abrirDocumento('com-descargo', r.data.nro); } });
  return (
    <>
      <PageHead title="Descargo de vales — bitácora de control (Anexo 3)" sub="El conductor presenta la bitácora con las lecturas de km/horómetro, los vales usados y las facturas" />
      <Card title="1. Emisión a descargar">
        <div className="row">
          <SelectField label="Nº de emisión (Emitido)" value={em?.nro ?? ''} onChange={elegir} options={(pend ?? []).map((e) => ({ value: e.nro, label: `${e.nro} · ${e.placa} · ${e.conductor}` }))} />
          <DateField label="Fecha de descargo" value={fecha} onChange={setFecha} />
          {em && <button onClick={() => abrirDocumento('com-planilla-descargo', em.nro)}>Imprimir planilla en blanco</button>}
        </div>
        {em && (
          <div className="alert info" style={{ marginTop: 10 }}>
            <div><b>{em.placa}</b> — {em.descripcion_destino} · Conductor: <b>{em.conductor}</b> · Periodo {fmtDate(em.desde)} al {fmtDate(em.hasta)}<br />Vales entregados ({vales.length}): {em.detalle_vales} · Lectura al emitir: {em.lectura_actual ?? '—'}</div>
          </div>
        )}
      </Card>
      {em && (
        <>
          <Card title="2. Bitácora de recorrido y cargas">
            <ItemsGrid rows={lineas} onChange={setLineas} vacio={lin} cols={[
              { key: 'fecha', header: 'Fecha', type: 'date', width: 140 }, { key: 'ruta', header: 'Ruta / actividad' },
              ...(em.destino === 'VEHICULO' ? [{ key: 'lectura_salida' as const, header: 'Lectura salida', type: 'number' as const, num: true }, { key: 'lectura_llegada' as const, header: 'Lectura llegada', type: 'number' as const, num: true }] : []),
              { key: 'nro_vale', header: 'Nº vale', type: 'select', options: vales.map((v: any) => String(v.nro_vale)), width: 120 }, { key: 'litros', header: 'Litros', type: 'number', num: true, width: 90 }, { key: 'factura', header: 'Nº factura', width: 110 }, { key: 'estacion', header: 'Estación de servicio' },
            ]} />
            <label className="row" style={{ marginTop: 8, gap: 6 }}><input type="checkbox" checked={devolver} onChange={(e) => setDevolver(e.target.checked)} /> Devolver automáticamente al almacén los vales no utilizados</label>
            <AreaField label="Observaciones" value={obs} onChange={setObs} />
          </Card>
          {puede('com') && <button className="primary" disabled={busy} onClick={registrar}>Registrar descargo</button>}
        </>
      )}
      <Card title="Descargos registrados">
        <DataTable maxHeight="40vh" rows={desc ?? []} cols={[{ key: 'nro', header: 'Descargo' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'nro_emision', header: 'Emisión' }, { key: 'placa', header: 'Placa' }, { key: 'conductor', header: 'Conductor' }, { key: 'litros', header: 'Litros', num: true }, { key: 'monto_usado', header: 'Bs usado', money: true }, { key: 'rendimiento_real', header: 'Rend.', num: true }, { key: 'estado', header: 'Estado', badge: true }, { key: 'alertas', header: 'Alertas' }, { key: 'p', header: '', render: (r) => <button className="sm" onClick={() => abrirDocumento('com-descargo', r.nro)}>PDF</button> }]} />
        <small className="muted">Rendimiento fuera de la tolerancia configurada deja el descargo OBSERVADO. Monto en Bs: {fmt2((desc ?? []).reduce((t, d) => t + Number(d.monto_usado), 0))}</small>
      </Card>
    </>
  );
}
