import { useState } from 'react';
import { get, hoy, post, fmt2 } from '../../api';
import { useAuth } from '../../auth';
import { Card, DataTable, DateField, NumField, PageHead, SelectField, Tabs, TextField, useAction, useLoad } from '../../ui';
import { useComMeta } from './common';

export default function ComTurriles() {
  const { puede } = useAuth();
  const { data: meta } = useComMeta();
  const { data: tu, reload } = useLoad<any[]>(() => get('/com/turriles'));
  const [puesto, setPuesto] = useState('');
  const { data: kx, reload: reK } = useLoad<any[]>(() => get('/com/kardex', { almacen: puesto || undefined }), [puesto]);
  const [t, setT] = useState<'ing' | 'des'>('ing');
  const [i, setI] = useState<any>({ fecha: hoy(), puesto: '', litros: '', precio: '', factura: '', proveedor: '' });
  const [d, setD] = useState<any>({ fecha: hoy(), puesto: '', placa: '', operador: '', litros: '', lectura: '', apertura: '', obra: '' });
  const [run, busy] = useAction();
  const after = () => { reload(); reK(); };
  const puestos = (meta?.puestos ?? []).map((p) => ({ value: p.codigo, label: `${p.codigo} - ${p.nombre} (${p.combustible})` }));
  const sel = tu?.find((x) => x.codigo === d.puesto);
  return (
    <>
      <PageHead title="Combustible en turriles (puestos y campamentos)" sub="Las cargas con vales se registran en Emitir vales con destino TURRIL" />
      <div className="kpis">{(tu ?? []).map((p) => <div key={p.codigo} className="kpi com"><b>{fmt2(p.saldo)} L</b><span>{p.codigo} · {p.nombre} · capacidad {p.capacidad_l} L · Bs/L {fmt2(p.costo_prom)}</span></div>)}</div>
      {puede('com') && (
        <Card>
          <Tabs value={t} onChange={setT} items={[{ id: 'ing', label: 'A. Ingreso por compra directa (con factura)' }, { id: 'des', label: 'B. Despacho a vehículo / maquinaria' }]} />
          {t === 'ing' && (
            <>
              <div className="grid">
                <DateField label="Fecha" req value={i.fecha} onChange={(v) => setI({ ...i, fecha: v })} />
                <SelectField label="Puesto" req value={i.puesto} onChange={(v) => setI({ ...i, puesto: v })} options={puestos} />
                <NumField label="Litros recibidos" req value={i.litros} onChange={(v) => setI({ ...i, litros: v ?? '' })} />
                <NumField label="Precio unitario Bs/L" req value={i.precio} onChange={(v) => setI({ ...i, precio: v ?? '' })} />
                <TextField label="Nº de factura (a nombre y NIT del GAM)" req value={i.factura} onChange={(v) => setI({ ...i, factura: v })} />
                <TextField label="Proveedor / estación" value={i.proveedor} onChange={(v) => setI({ ...i, proveedor: v })} />
              </div>
              <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={() => run(async () => { const r = await post('/com/turriles/ingreso', { ...i, litros: Number(i.litros), precio: Number(i.precio) }); after(); return r; }, 'Ingreso registrado.')}>Registrar ingreso</button></div>
            </>
          )}
          {t === 'des' && (
            <>
              <div className="grid">
                <DateField label="Fecha" req value={d.fecha} onChange={(v) => setD({ ...d, fecha: v })} />
                <SelectField label="Puesto" req value={d.puesto} onChange={(v) => setD({ ...d, puesto: v })} options={puestos} hint={sel ? `Saldo: ${fmt2(sel.saldo)} L` : ''} />
                <SelectField label="Vehículo / equipo" req value={d.placa} onChange={(v) => setD({ ...d, placa: v })} options={(meta?.vehiculos ?? []).map((v) => ({ value: v.placa, label: `${v.placa} - ${v.tipo} (${v.combustible})` }))} />
                <SelectField label="Operador / conductor" req value={d.operador} onChange={(v) => setD({ ...d, operador: v })} options={(meta?.conductores ?? []).map((c) => c.nombre)} />
                <NumField label="Litros despachados" req value={d.litros} onChange={(v) => setD({ ...d, litros: v ?? '' })} />
                <NumField label="Lectura km / horómetro" req value={d.lectura} onChange={(v) => setD({ ...d, lectura: v ?? '' })} />
                <SelectField label="Apertura programática" req value={d.apertura} onChange={(v) => setD({ ...d, apertura: v })} options={(meta?.aperturas ?? []).map((a) => ({ value: a.apertura, label: `${a.apertura} - ${a.descripcion}` }))} />
                <TextField label="Obra o actividad" req value={d.obra} onChange={(v) => setD({ ...d, obra: v })} />
              </div>
              <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={() => run(async () => { await post('/com/turriles/despacho', { ...d, litros: Number(d.litros), lectura: Number(d.lectura) }); after(); }, 'Despacho registrado.')}>Registrar despacho</button></div>
            </>
          )}
        </Card>
      )}
      <Card title="Kardex de turriles" right={<select style={{ width: 200 }} value={puesto} onChange={(e) => setPuesto(e.target.value)}><option value="">Todos los almacenes</option>{(tu ?? []).map((p) => <option key={p.codigo} value={p.codigo}>{p.codigo}</option>)}</select>}>
        <DataTable maxHeight="45vh" rows={kx ?? []} cols={[{ key: 'fecha', header: 'Fecha', date: true }, { key: 'tipo', header: 'Tipo' }, { key: 'documento', header: 'Documento' }, { key: 'almacen', header: 'Almacén' }, { key: 'item', header: 'Ítem' }, { key: 'entrada', header: 'Entrada', num: true }, { key: 'salida', header: 'Salida', num: true }, { key: 'costo_unit', header: 'Costo', money: true }, { key: 'placa', header: 'Placa' }, { key: 'detalle', header: 'Detalle' }]} />
      </Card>
    </>
  );
}
