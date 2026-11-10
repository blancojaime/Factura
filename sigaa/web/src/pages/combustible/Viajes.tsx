import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, ItemsGrid, NumField, PageHead, SelectField, Tabs, TextField, useConfirmable, useLoad } from '../../ui';
import { nroUrl, useComMeta } from './common';

const tr = () => ({ fecha: hoy(), origen: '', destino: '', hora_salida: '', hora_llegada: '', km_inicial: '', km_final: '' });
const co = () => ({ fecha: hoy(), estacion: '', factura: '', litros: '', total: '' });

export default function ComViajes() {
  const { puede } = useAuth();
  const { data: meta } = useComMeta();
  const { data: lista, reload } = useLoad<any[]>(() => get('/com/viajes'));
  const [t, setT] = useState<'nuevo' | 'descargo'>('nuevo');
  const [v, setV] = useState<any>({ fecha: hoy(), placa: '', conductor: '', origen: '', destino: '', salida: hoy(), retorno: hoy(), km_estimado: '', litros_estimados: '', apertura: '', fondo: '', motivo: '', nota: '', comprobante: '', funcionarios: '' });
  const [sel, setSel] = useState<any>(null);
  const [tramos, setTramos] = useState<any[]>([tr()]);
  const [compras, setCompras] = useState<any[]>([co()]);
  const [dd, setDd] = useState({ fecha_descargo: hoy(), actividades: '', conclusiones: '' });
  const [exec, busy] = useConfirmable();
  const pendientes = (lista ?? []).filter((x) => x.estado === 'En curso');
  const kmTotal = tramos.reduce((s, x) => s + Math.max(0, Number(x.km_final) - Number(x.km_inicial) || 0), 0);
  const gastado = compras.reduce((s, x) => s + (Number(x.total) || 0), 0);
  return (
    <>
      <PageHead title="Viajes oficiales con fondos en avance (Anexos 4 y 6)" sub="Registre el viaje y el fondo antes de la salida; al regreso presente el descargo con tramos y facturas" />
      <Tabs value={t} onChange={setT} items={[{ id: 'nuevo', label: '1. Solicitud de viaje' }, { id: 'descargo', label: '2. Descargo del viaje' }]} />
      {t === 'nuevo' && puede('com') && (
        <Card title="Registro del viaje y del fondo">
          <div className="grid">
            <DateField label="Fecha de solicitud" req value={v.fecha} onChange={(x) => setV({ ...v, fecha: x })} />
            <SelectField label="Vehículo (placa)" req value={v.placa} onChange={(x) => setV({ ...v, placa: x })} options={(meta?.vehiculos ?? []).map((a) => ({ value: a.placa, label: `${a.placa} - ${a.tipo}` }))} />
            <SelectField label="Conductor" req value={v.conductor} onChange={(x) => setV({ ...v, conductor: x })} options={(meta?.conductores ?? []).map((c) => c.nombre)} />
            <TextField label="Origen" req value={v.origen} onChange={(x) => setV({ ...v, origen: x })} />
            <TextField label="Destino" req value={v.destino} onChange={(x) => setV({ ...v, destino: x })} />
            <DateField label="Fecha de salida" req value={v.salida} onChange={(x) => setV({ ...v, salida: x })} />
            <DateField label="Fecha de retorno" req value={v.retorno} onChange={(x) => setV({ ...v, retorno: x })} />
            <NumField label="Km estimados" value={v.km_estimado} onChange={(x) => setV({ ...v, km_estimado: x ?? '' })} />
            <NumField label="Litros estimados" value={v.litros_estimados} onChange={(x) => setV({ ...v, litros_estimados: x ?? '' })} />
            <SelectField label="Apertura programática" req value={v.apertura} onChange={(x) => setV({ ...v, apertura: x })} options={(meta?.aperturas ?? []).map((a) => ({ value: a.apertura, label: `${a.apertura} - ${a.descripcion}` }))} />
            <NumField label="Fondo en avance (Bs)" req value={v.fondo} onChange={(x) => setV({ ...v, fondo: x ?? '' })} />
            <TextField label="Nota / comprobante" value={v.nota} onChange={(x) => setV({ ...v, nota: x })} />
            <AreaField className="span-all" label="Motivo o comisión del viaje" req value={v.motivo} onChange={(x) => setV({ ...v, motivo: x })} />
            <AreaField className="span-all" label="Funcionarios que viajan" value={v.funcionarios} onChange={(x) => setV({ ...v, funcionarios: x })} />
          </div>
          <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={() => exec((confirmar) => post('/com/viajes', { ...v, km_estimado: Number(v.km_estimado) || undefined, litros_estimados: Number(v.litros_estimados) || undefined, fondo: Number(v.fondo), confirmar }), (r) => `Viaje ${r.data.nro} registrado`).then((r) => { if (r?.ok) { reload(); abrirDocumento('com-viaje', r.data.nro); } })}>Registrar viaje</button></div>
        </Card>
      )}
      {t === 'descargo' && (
        <>
          <Card title="Seleccione el viaje en curso">
            <SelectField label="Viaje" value={sel?.nro ?? ''} onChange={(n) => setSel(pendientes.find((x) => x.nro === n) ?? null)} options={pendientes.map((x) => ({ value: x.nro, label: `${x.nro} · ${x.placa} · ${x.origen}→${x.destino} · fondo Bs ${fmt2(x.fondo)}` }))} />
          </Card>
          {sel && (
            <>
              <Card title="Tramos recorridos" right={<b>{kmTotal} km</b>}><ItemsGrid rows={tramos} onChange={setTramos} vacio={tr} cols={[{ key: 'fecha', header: 'Fecha', type: 'date', width: 140 }, { key: 'origen', header: 'Origen' }, { key: 'destino', header: 'Destino' }, { key: 'hora_salida', header: 'Salida', width: 80 }, { key: 'hora_llegada', header: 'Llegada', width: 80 }, { key: 'km_inicial', header: 'Km inicial', type: 'number', num: true }, { key: 'km_final', header: 'Km final', type: 'number', num: true }]} /></Card>
              <Card title="Compras de combustible (facturas)" right={<b>Gastado Bs {fmt2(gastado)} · Saldo Bs {fmt2(Number(sel.fondo) - gastado)}</b>}><ItemsGrid rows={compras} onChange={setCompras} vacio={co} cols={[{ key: 'fecha', header: 'Fecha', type: 'date', width: 140 }, { key: 'estacion', header: 'Estación de servicio' }, { key: 'factura', header: 'Nº factura' }, { key: 'litros', header: 'Litros', type: 'number', num: true }, { key: 'total', header: 'Total Bs', type: 'number', num: true }]} /></Card>
              <Card>
                <div className="grid"><DateField label="Fecha de descargo" req value={dd.fecha_descargo} onChange={(x) => setDd({ ...dd, fecha_descargo: x })} /><AreaField className="span2" label="Actividades realizadas" value={dd.actividades} onChange={(x) => setDd({ ...dd, actividades: x })} /><AreaField className="span-all" label="Conclusiones" value={dd.conclusiones} onChange={(x) => setDd({ ...dd, conclusiones: x })} /></div>
                {puede('com') && <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={() => exec((confirmar) => post(`/com/viajes/${nroUrl(sel.nro)}/descargo`, { ...dd, confirmar, tramos: tramos.map((x) => ({ ...x, km_inicial: Number(x.km_inicial), km_final: Number(x.km_final) })), compras: compras.filter((x) => x.litros || x.total).map((x) => ({ ...x, litros: Number(x.litros), total: Number(x.total) })) }), (r) => `Descargo registrado (${r.data.resultado}). Saldo Bs ${fmt2(r.data.saldo)}`).then((r) => { if (r?.ok) { setSel(null); reload(); abrirDocumento('com-viaje', sel.nro); } })}>Registrar descargo</button></div>}
              </Card>
            </>
          )}
        </>
      )}
      <Card title="Viajes"><DataTable maxHeight="40vh" rows={lista ?? []} cols={[{ key: 'nro', header: 'Viaje' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'placa', header: 'Placa' }, { key: 'conductor', header: 'Conductor' }, { key: 'destino', header: 'Destino' }, { key: 'fondo', header: 'Fondo', money: true }, { key: 'gastado', header: 'Gastado', money: true }, { key: 'saldo', header: 'Saldo', money: true }, { key: 'estado', header: 'Estado', badge: true }, { key: 'resultado', header: 'Resultado', render: (r) => <Badge v={r.resultado} /> }, { key: 'p', header: '', render: (r) => <button className="sm" onClick={() => abrirDocumento('com-viaje', r.nro)}>PDF</button> }]} /></Card>
    </>
  );
}
