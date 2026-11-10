import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { abrirDocumento, get, hoy, post, fmt2 } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Card, DataTable, DateField, PageHead, SelectField, useAction, useLoad, useUi } from '../../ui';
import { optsAmb, optsAux, optsCta, optsEdif, useAfMeta } from './common';

export default function AfAsignar() {
  const { puede } = useAuth();
  const ui = useUi();
  const [sp] = useSearchParams();
  const { data: meta } = useAfMeta();
  const { data: sols } = useLoad<any[]>(() => get('/af/solicitudes'));
  const { data: actas, reload } = useLoad<any[]>(() => get('/af/asignaciones'));
  const [f, setF] = useState<any>({ fecha: hoy(), nro_sol: sp.get('sol') ?? '', funcionario: '', cod_edif: '', cod_amb: '', observaciones: '', id_cta: '', id_aux: '' });
  const [disp, setDisp] = useState<any[]>([]);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [run, busy] = useAction();
  useEffect(() => {
    if (f.nro_sol) get(`/af/solicitudes/${encodeURIComponent(f.nro_sol)}`).then((s) => setF((x: any) => ({ ...x, funcionario: x.funcionario || s.funcionario })));
  }, [f.nro_sol]); // eslint-disable-line
  const mostrar = () => run(async () => {
    const r = await get('/af/asignaciones/disponibles', { nro_sol: f.nro_sol, id_cta: f.id_cta, id_aux: f.id_aux });
    setDisp(r); setSel(new Set(r.filter((x: any) => x.preseleccionado).map((x: any) => x.codigo)));
    if (!r.length) ui.error('No existen activos EN ALMACÉN que coincidan.' + (f.nro_sol ? ' Puede emitir el Formulario de Salida con leyenda SIN EXISTENCIA desde Solicitudes.' : ''));
    else ui.ok('Se preseleccionaron los activos disponibles según las cantidades solicitadas. Revise y genere la asignación.');
  });
  const valor = disp.filter((d) => sel.has(d.codigo)).reduce((t, d) => t + Number(d.valor), 0);
  const toggle = (c: string) => { const n = new Set(sel); n.has(c) ? n.delete(c) : n.add(c); setSel(n); };
  return (
    <>
      <PageHead title="Asignación y entrega de activos fijos" sub="Formulario de salida / acta de asignación: el servidor público recibe y se responsabiliza por los activos" />
      <Card title="1. Datos de la asignación">
        <div className="grid">
          <DateField label="Fecha" req value={f.fecha} onChange={(v) => setF({ ...f, fecha: v })} />
          <SelectField label="Nº de solicitud (opcional)" value={f.nro_sol} onChange={(v) => setF({ ...f, nro_sol: v })} options={(sols ?? []).filter((s) => !['ATENDIDA', 'SIN EXISTENCIA'].includes(s.estado)).map((s) => ({ value: s.nro, label: `${s.nro} · ${s.funcionario}` }))} />
          <SelectField label="Servidor público que recibe" req value={f.funcionario} onChange={(v) => setF({ ...f, funcionario: v })} options={(meta?.funcionarios ?? []).map((x) => x.nombre)} />
          <SelectField label="Edificio destino" value={f.cod_edif} onChange={(v) => setF({ ...f, cod_edif: v, cod_amb: '' })} options={optsEdif(meta)} />
          <SelectField label="Ambiente destino" value={f.cod_amb} onChange={(v) => setF({ ...f, cod_amb: v })} options={optsAmb(meta, f.cod_edif)} disabled={!f.cod_edif} />
          <SelectField label="Filtrar por cuenta" value={f.id_cta} onChange={(v) => setF({ ...f, id_cta: v, id_aux: '' })} options={optsCta(meta)} />
          <SelectField label="Filtrar por auxiliar" value={f.id_aux} onChange={(v) => setF({ ...f, id_aux: v })} options={optsAux(meta, f.id_cta)} disabled={!f.id_cta} />
          <AreaField className="span-all" label="Observaciones" value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} />
        </div>
        <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={mostrar}>Mostrar activos disponibles</button></div>
      </Card>
      {disp.length > 0 && (
        <Card title={`2. Activos en almacén (${sel.size} marcado(s) · Bs ${fmt2(valor)})`} right={<span className="row"><button className="sm" onClick={() => setSel(new Set(disp.map((d) => d.codigo)))}>Marcar todo</button><button className="sm" onClick={() => setSel(new Set())}>Desmarcar</button></span>}>
          <DataTable maxHeight="45vh" rows={disp} onRow={(r) => toggle(r.codigo)} cols={[{ key: 's', header: '', render: (r) => <input type="checkbox" readOnly checked={sel.has(r.codigo)} /> }, { key: 'codigo', header: 'Código' }, { key: 'auxiliar', header: 'Auxiliar' }, { key: 'descripcion', header: 'Descripción' }, { key: 'estado', header: 'Estado' }, { key: 'valor', header: 'Valor Bs', money: true }]} />
          {puede('af') && <div style={{ marginTop: 10 }}><button className="ok" disabled={busy || !sel.size} onClick={() => run(async () => {
            const r = await post('/af/asignaciones', { ...f, cod_edif: f.cod_edif === '' ? null : Number(f.cod_edif), cod_amb: f.cod_amb === '' ? null : Number(f.cod_amb), nro_sol: f.nro_sol || undefined, codigos: [...sel] });
            ui.ok(`Acta ${r.nro}: ${r.cantidad} activos por Bs ${fmt2(r.valor)}`); setDisp([]); setSel(new Set()); reload(); abrirDocumento('af-asignacion', r.nro);
          })}>Generar asignación e imprimir acta</button></div>}
        </Card>
      )}
      <Card title="Actas de asignación"><DataTable maxHeight="40vh" rows={actas ?? []} cols={[{ key: 'nro', header: 'Acta' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'funcionario', header: 'Servidor público' }, { key: 'nro_sol', header: 'Solicitud' }, { key: 'cantidad', header: 'Cant.', num: true }, { key: 'valor', header: 'Valor Bs', money: true }, { key: 'p', header: '', render: (r) => <button className="sm" onClick={() => abrirDocumento('af-asignacion', r.nro)}>PDF</button> }]} /></Card>
    </>
  );
}
