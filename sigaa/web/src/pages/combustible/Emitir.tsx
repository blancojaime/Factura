import { useEffect, useState } from 'react';
import { abrirDocumento, fmt2, get, hoy } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Card, DateField, NumField, PageHead, SelectField, TextField, useConfirmable, useLoad, useUi } from '../../ui';
import { post } from '../../api';
import { useComMeta } from './common';

const vacio = () => ({ fecha: hoy(), destino: 'VEHICULO', placa: '', lectura: '', conductor: '', solicitante: '', cargo_solicitante: '', unidad: '', apertura: '', trabajo: '', desde: hoy(), hasta: hoy(), programado: '', justificacion: '', observaciones: '' });

export default function ComEmitir() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useComMeta();
  const { data: resumen, reload: reVales } = useLoad<any>(() => get('/com/resumen-vales'));
  const [f, setF] = useState<any>(vacio());
  const [cant, setCant] = useState<Record<string, string>>({});
  const [info, setInfo] = useState<{ precio?: number; litros_max?: number | null; ultima?: number; pend?: number }>({});
  const [exec, busy] = useConfirmable();
  const veh = meta?.vehiculos.find((v) => v.placa === f.placa);
  const pto = meta?.puestos.find((p) => p.codigo === f.placa);
  const comb = f.destino === 'TURRIL' ? pto?.combustible : veh?.combustible;
  const monto = Object.entries(cant).reduce((t, [k, v]) => t + Number(k) * (Number(v) || 0), 0);
  const litros = info.precio ? monto / info.precio : 0;
  const disp = (corte: number) => (resumen?.lista ?? []).find((x: any) => x.combustible?.toLowerCase() === String(comb ?? '').toLowerCase() && x.corte === corte)?.disponible ?? 0;

  useEffect(() => {
    if (veh && f.destino === 'VEHICULO') setF((x: any) => ({ ...x, conductor: x.conductor || veh.conductor || '', unidad: x.unidad || veh.unidad || '' }));
  }, [veh?.placa]); // eslint-disable-line
  useEffect(() => {
    if (!comb || !f.fecha) return setInfo({});
    Promise.all([
      get('/com/precio', { combustible: comb, fecha: f.fecha }),
      get('/com/litros-maximos', { placa: f.placa, destino: f.destino, desde: f.desde, hasta: f.hasta, programado: f.programado }),
      f.destino === 'VEHICULO' ? get('/com/ultima-lectura', { placa: f.placa, fecha: f.fecha }) : Promise.resolve({ lectura: 0 }),
      f.conductor ? get('/com/descargos-pendientes', { conductor: f.conductor, fecha: f.fecha }) : Promise.resolve({ pendientes: 0 }),
    ]).then(([p, l, u, d]) => setInfo({ precio: p.precio, litros_max: l.litros, ultima: u.lectura, pend: d.pendientes })).catch(() => {});
  }, [comb, f.fecha, f.placa, f.destino, f.desde, f.hasta, f.programado, f.conductor]);

  const emitir = () => exec(async (confirmar) => post('/com/emisiones', { ...f, lectura: f.lectura === '' ? null : Number(f.lectura), programado: f.programado === '' ? undefined : Number(f.programado), cantidades: cant, confirmar }), (r) => `Emisión registrada: ${r.data.nro} — ${r.data.detalle}`).then((r) => {
    if (r?.ok) {
      abrirDocumento('com-vale', r.data.nro);
      if (r.data.planilla) setTimeout(() => abrirDocumento('com-planilla-descargo', r.data.nro), 400);
      setF(vacio()); setCant({}); reVales();
    }
  });
  const excede = info.litros_max != null && litros > info.litros_max + 0.001;
  return (
    <>
      <PageHead title="Emisión de vales de combustible" sub="Solicitud (Anexo 1) y vale (Anexo 2) · control de límites, rendimiento y plazos de descargo" />
      <Card title="1. Destino del combustible">
        <div className="grid">
          <DateField label="Fecha de emisión" req value={f.fecha} onChange={(v) => setF({ ...f, fecha: v })} />
          <SelectField label="Tipo de destino" blank={false} req value={f.destino} onChange={(v) => setF({ ...f, destino: v, placa: '' })} options={['VEHICULO', 'TURRIL']} />
          <SelectField label={f.destino === 'TURRIL' ? 'Código de puesto' : 'Placa / código del vehículo'} req value={f.placa} onChange={(v) => setF({ ...f, placa: v })} options={f.destino === 'TURRIL' ? (meta?.puestos ?? []).map((p) => ({ value: p.codigo, label: `${p.codigo} - ${p.nombre}` })) : (meta?.vehiculos ?? []).map((v) => ({ value: v.placa, label: `${v.placa} - ${v.tipo} ${v.marca ?? ''} (${v.uso})` }))} />
          {f.destino === 'VEHICULO' && <NumField label={`Km u horómetro actual${veh?.medidor === 'Horas' ? ' (horas)' : ''}`} value={f.lectura} onChange={(v) => setF({ ...f, lectura: v ?? '' })} hint={info.ultima ? `Última lectura registrada: ${info.ultima}` : ''} />}
        </div>
        {(veh || pto) && <div className="alert info" style={{ marginTop: 10 }}>{veh ? `${veh.tipo} ${veh.marca ?? ''} ${veh.modelo ?? ''} · ${veh.combustible} · uso ${veh.uso} · tanque ${veh.capacidad_tanque} L` : `Puesto ${pto.nombre} · ${pto.combustible} · capacidad ${pto.capacidad_l} L`}</div>}
      </Card>
      <Card title="2. Conductor, solicitante y trabajo">
        <div className="grid">
          <SelectField label="Conductor / operador" req value={f.conductor} onChange={(v) => setF({ ...f, conductor: v })} options={(meta?.conductores ?? []).map((c) => c.nombre)} />
          <TextField label="Solicitante" req value={f.solicitante} onChange={(v) => setF({ ...f, solicitante: v })} />
          <TextField label="Cargo del solicitante" value={f.cargo_solicitante} onChange={(v) => setF({ ...f, cargo_solicitante: v })} />
          <SelectField label="Unidad / área solicitante" req value={f.unidad} onChange={(v) => setF({ ...f, unidad: v })} options={(meta?.unidades ?? []).map((u) => u.nombre)} />
          <SelectField label="Apertura programática" req value={f.apertura} onChange={(v) => setF({ ...f, apertura: v })} options={(meta?.aperturas ?? []).map((a) => ({ value: a.apertura, label: `${a.apertura} - ${a.descripcion}` }))} />
          <DateField label="Utilización desde" req value={f.desde} onChange={(v) => setF({ ...f, desde: v })} />
          <DateField label="Utilización hasta" req value={f.hasta} onChange={(v) => setF({ ...f, hasta: v })} />
          {veh?.uso === 'Operativo' && <NumField label={`Programado (${veh.medidor === 'Horas' ? 'horas' : 'km'})`} req value={f.programado} onChange={(v) => setF({ ...f, programado: v ?? '' })} />}
          <AreaField className="span-all" label="Descripción del trabajo a realizar" req value={f.trabajo} onChange={(v) => setF({ ...f, trabajo: v })} />
        </div>
        {(info.pend ?? 0) > 0 && <div className="alert aviso" style={{ marginTop: 8 }}>El conductor tiene {info.pend} descargo(s) vencido(s). Máximo permitido: {meta?.config.MAX_DESCARGOS_PENDIENTES}.</div>}
      </Card>
      <Card title="3. Vales a entregar" right={<span>{comb ? `${comb} · ` : ''}Bs/L {info.precio ? fmt2(info.precio) : '—'}</span>}>
        <div className="grid">
          {(meta?.cortes ?? []).map((c) => (
            <NumField key={c} label={`Vales de Bs ${c}`} hint={comb ? `Disponibles: ${disp(c)}` : ''} value={cant[String(c)] ?? ''} onChange={(v) => setCant({ ...cant, [String(c)]: v === null ? '' : String(v) })} />
          ))}
        </div>
        <div className="kpis" style={{ marginTop: 10 }}>
          <div className="kpi com"><b>Bs {fmt2(monto)}</b><span>Monto</span></div>
          <div className="kpi com"><b>{fmt2(litros)} L</b><span>Litros equivalentes</span></div>
          <div className={'kpi ' + (excede ? 'bad' : 'com')}><b>{info.litros_max != null ? fmt2(info.litros_max) + ' L' : '—'}</b><span>Máximo permitido</span></div>
        </div>
        {excede && <><div className="alert critico">Los litros superan el máximo permitido: registre la justificación del excedente.</div><AreaField label="Justificación de excedente (viaje, emergencia, etc.)" req value={f.justificacion} onChange={(v) => setF({ ...f, justificacion: v })} /></>}
        <AreaField label="Observaciones" value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} />
      </Card>
      {puede('com') && <div className="row"><button className="primary" disabled={busy} onClick={emitir}>Emitir vales e imprimir</button><button onClick={() => { setF(vacio()); setCant({}); ui.ok('Formulario limpio.'); }}>Limpiar</button></div>}
    </>
  );
}
