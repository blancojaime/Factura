import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { abrirPdfPost, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { Card, DataTable, DateField, PageHead, SelectField, useAction, useLoad, useUi } from '../../ui';
import { nroUrl, optsAmb, optsAux, optsCta, optsEdif, useAfMeta } from './common';

export default function AfCodificar() {
  const { puede } = useAuth();
  const ui = useUi();
  const [sp] = useSearchParams();
  const { data: meta } = useAfMeta();
  const { data: ings } = useLoad<any[]>(() => get('/af/ingresos'));
  const [ing, setIng] = useState(sp.get('ing') ?? '');
  const [fecha, setFecha] = useState(hoy());
  const [estado, setEstado] = useState('Nuevo');
  const [filas, setFilas] = useState<any[]>([]);
  const [res, setRes] = useState<any[]>([]);
  const [run, busy] = useAction();
  useEffect(() => {
    if (!ing) { setFilas([{ item: 0, id_cta: '', id_aux: '', descripcion: '', pendiente: 99, cod_edif: '', cod_amb: '', cantidad: '', valor: '' }]); return; }
    get(`/af/ingresos/${nroUrl(ing)}/pendientes`).then((p: any[]) => setFilas(p.filter((x) => x.pendiente > 0).map((x) => ({ item: x.item, id_cta: x.id_cta, id_aux: x.id_aux, descripcion: x.descripcion, auxiliar: x.auxiliar, cuenta: x.cuenta, pendiente: x.pendiente, cod_edif: '', cod_amb: '', cantidad: x.pendiente, valor: x.precio_unit })))).catch((e) => ui.error(e.message));
  }, [ing]); // eslint-disable-line
  const set = (i: number, k: string, v: any) => setFilas(filas.map((f, j) => (j === i ? { ...f, [k]: v } : f)));
  const generar = () => run(async () => {
    const r = await post('/af/codificar', { nro_ingreso: ing || undefined, fecha, estado, filas: filas.filter((f) => Number(f.cantidad) > 0).map((f) => ({ item: ing ? f.item : undefined, id_cta: Number(f.id_cta), id_aux: Number(f.id_aux), descripcion: f.descripcion, cod_edif: Number(f.cod_edif), cod_amb: f.cod_amb === '' ? 0 : Number(f.cod_amb), cantidad: Number(f.cantidad), valor: f.valor === '' ? undefined : Number(f.valor) })) });
    setRes(r.generados);
    ui.ok(`Se generaron ${r.cantidad} código(s) único(s).`);
    if (ing) setIng(ing + ''); // recarga pendientes
    get(`/af/ingresos/${nroUrl(ing)}/pendientes`).then((p: any[]) => setFilas(p.filter((x) => x.pendiente > 0).map((x) => ({ item: x.item, id_cta: x.id_cta, id_aux: x.id_aux, descripcion: x.descripcion, auxiliar: x.auxiliar, cuenta: x.cuenta, pendiente: x.pendiente, cod_edif: '', cod_amb: '', cantidad: x.pendiente, valor: x.precio_unit })))).catch(() => {});
  });
  return (
    <>
      <PageHead title="Registro y codificación de activos fijos" sub="Código = EEE-AA-CCXXX-NN · Edificio (3) - Ambiente (2) - Cuenta (2) + Auxiliar (3) - Correlativo (2)" />
      <Card>
        <div className="row">
          <SelectField label="Ingreso a codificar (vacío = codificación directa / inventario inicial)" value={ing} onChange={setIng} options={(ings ?? []).filter((i) => i.estado !== 'CODIFICADO').map((i) => ({ value: i.nro, label: `${i.nro} · ${i.proveedor ?? ''} · ${i.estado}` }))} />
          <DateField label="Fecha de codificación" value={fecha} onChange={setFecha} />
          <SelectField label="Estado físico inicial" blank={false} value={estado} onChange={setEstado} options={(meta?.estados ?? []).map((e) => e.estado)} />
        </div>
      </Card>
      <Card title="Activos a codificar — indique cantidad, edificio y ambiente de destino">
        <div className="table-wrap"><table className="t"><thead><tr><th>Ítem</th><th>Cuenta / auxiliar</th><th>Descripción</th><th className="num">Pend.</th><th>Edificio</th><th>Ambiente</th><th className="num" style={{ width: 90 }}>Cant. a codificar</th><th className="num" style={{ width: 100 }}>Valor Bs</th></tr></thead>
          <tbody>{filas.length === 0 && <tr><td colSpan={8} className="empty">{ing ? 'El ingreso no tiene activos pendientes de codificar.' : 'Agregue filas para codificación directa.'}</td></tr>}
            {filas.map((f, i) => (
              <tr key={i}><td className="ctr">{ing ? f.item : i + 1}</td>
                <td>{ing ? <span>{f.cuenta} / {f.auxiliar}</span> : <div className="row" style={{ gap: 4, flexWrap: 'nowrap' }}><select value={f.id_cta} onChange={(e) => setFilas(filas.map((x, j) => (j === i ? { ...x, id_cta: e.target.value, id_aux: '' } : x)))}><option />{optsCta(meta).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select><select value={f.id_aux} onChange={(e) => set(i, 'id_aux', e.target.value)}><option />{optsAux(meta, f.id_cta).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></div>}</td>
                <td><input value={f.descripcion ?? ''} onChange={(e) => set(i, 'descripcion', e.target.value)} /></td><td className="num">{ing ? f.pendiente : ''}</td>
                <td><select value={f.cod_edif} onChange={(e) => setFilas(filas.map((x, j) => (j === i ? { ...x, cod_edif: e.target.value, cod_amb: '' } : x)))}><option />{optsEdif(meta).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></td>
                <td><select disabled={!f.cod_edif} value={f.cod_amb} onChange={(e) => set(i, 'cod_amb', e.target.value)}><option />{optsAmb(meta, f.cod_edif).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></td>
                <td><input type="number" value={f.cantidad} onChange={(e) => set(i, 'cantidad', e.target.value)} /></td>
                <td><input type="number" value={f.valor} onChange={(e) => set(i, 'valor', e.target.value)} /></td></tr>))}</tbody></table></div>
        {!ing && puede('af') && <div style={{ marginTop: 6 }}><button className="sm" onClick={() => setFilas([...filas, { item: 0, id_cta: '', id_aux: '', descripcion: '', pendiente: 99, cod_edif: '', cod_amb: '', cantidad: '', valor: '' }])}>+ Agregar fila</button></div>}
        {puede('af') && <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={generar}>Generar códigos</button></div>}
      </Card>
      {res.length > 0 && (
        <Card title={`Códigos generados (${res.length})`} right={<button className="primary" onClick={() => abrirPdfPost('/af/stickers', { codigos: res.map((r) => r.codigo) }).catch((e) => ui.error(e.message))}>Imprimir stickers</button>}>
          <DataTable maxHeight="40vh" rows={res} cols={[{ key: 'codigo', header: 'Código' }, { key: 'auxiliar', header: 'Auxiliar' }, { key: 'descripcion', header: 'Descripción' }, { key: 'ubicacion', header: 'Ubicación' }]} />
        </Card>
      )}
    </>
  );
}
