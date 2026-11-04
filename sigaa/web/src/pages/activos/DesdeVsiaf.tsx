import { useEffect, useState } from 'react';
import { fmtDate, get, post } from '../../api';
import { useAuth } from '../../auth';
import { Card, DataTable, PageHead, SelectField, TextField, useAction, useLoad, useUi } from '../../ui';
import { optsAmb, optsEdif, useAfMeta } from './common';

/** Trae al módulo de Activos Fijos de SIGAA los activos que ya están en el VSIAF (lo que el VSIAF tenga). */
export default function AfDesdeVsiaf() {
  const { puede } = useAuth();
  const ui = useUi();
  const [run, busy] = useAction();
  const { data: meta } = useAfMeta();
  const conf = useLoad<any>(() => get('/af/vsiaf/config'));
  const [p, setP] = useState({ ruta: '', unidad: '', cod_edif: '', cod_amb: '0', estado: 'TODOS', crearAuxiliares: true, crearFuncionarios: true });
  const [info, setInfo] = useState<any>();
  const [prev, setPrev] = useState<any>();
  const [fin, setFin] = useState<any>();
  useEffect(() => {
    if (!conf.data) return;
    setP((x) => ({ ...x, ruta: x.ruta || conf.data.ruta, unidad: x.unidad || conf.data.unidad }));
    if (conf.data.ruta) get('/af/vsiaf/leer/info', { ruta: conf.data.ruta }).then(setInfo).catch(() => undefined);
  }, [conf.data]);

  const cuerpo = () => ({ ruta: p.ruta || undefined, unidad: p.unidad || undefined, cod_edif: p.cod_edif ? Number(p.cod_edif) : undefined, cod_amb: Number(p.cod_amb || 0), estado: p.estado, crearAuxiliares: p.crearAuxiliares, crearFuncionarios: p.crearFuncionarios });
  const comprobar = () => run(async () => { setInfo(await get('/af/vsiaf/leer/info', { ruta: p.ruta })); setPrev(undefined); setFin(undefined); });
  const leer = () => run(async () => { setPrev(await post('/af/vsiaf/leer/previsualizar', cuerpo())); setFin(undefined); });
  const traer = async () => {
    if (!p.cod_edif) { ui.error('Elija el edificio de SIGAA donde quedarán los activos.'); return; }
    if (!(await ui.confirm(`Se crearán ${prev.nuevos} activo(s) en SIGAA (edificio ${p.cod_edif}). El VSIAF no se modifica. ¿Continuar?`))) return;
    run(async () => { const r = await post('/af/vsiaf/leer/traer', { ...cuerpo(), confirmar: true }); setFin(r); setPrev(undefined); ui.ok(`Se importaron ${r.importados} activo(s).`); });
  };
  return (
    <>
      <PageHead title="Importar desde el VSIAF" sub="Trae a SIGAA los activos que ya están en el VSIAF. El VSIAF no se modifica; lo que no tenga (fotos, marca, modelo, serie) queda para completarlo en SIGAA" />
      <Card title="1. Origen">
        <div className="form-grid">
          <TextField className="span2" label="Carpeta del VSIAF (contiene vsiaf.exe y dbfs)" value={p.ruta} onChange={(v) => setP({ ...p, ruta: v })} placeholder="C:\vsiaf" />
          <SelectField label="Unidad administrativa del VSIAF" value={p.unidad} onChange={(v) => setP({ ...p, unidad: v })} options={[{ value: '', label: 'Todas las unidades' }, ...((info?.unidades ?? []) as any[]).map((u) => ({ value: u.unidad, label: `${u.unidad} - ${u.descripcion}` }))]} blank={false} />
          <SelectField label="Activos a traer" blank={false} value={p.estado} onChange={(v) => setP({ ...p, estado: v })} options={[{ value: 'TODOS', label: 'Todos (elaborados y aprobados)' }, { value: 'APROBADOS', label: 'Solo los aprobados' }]} />
        </div>
        <div style={{ marginTop: 10 }}><button disabled={busy} onClick={comprobar}>Comprobar carpeta</button></div>
        {info && <p className="ok-txt" style={{ marginTop: 8 }}>✔ {info.entidad} · {info.unidades.length} unidad(es){info.vsiafAbierto ? ' · ⚠ el VSIAF está abierto (puede leer igual, pero cierre el VSIAF para estar seguro de los datos).' : ''}</p>}
      </Card>
      <Card title="2. Dónde quedarán en SIGAA">
        <div className="form-grid">
          <SelectField label="Edificio de SIGAA" req value={p.cod_edif} onChange={(v) => setP({ ...p, cod_edif: v, cod_amb: '0' })} options={optsEdif(meta)} />
          <SelectField label="Ambiente (los demás se ubican por el nombre de la oficina)" blank={false} value={p.cod_amb} onChange={(v) => setP({ ...p, cod_amb: v })} options={optsAmb(meta, p.cod_edif)} disabled={!p.cod_edif} />
          <label className="check"><input type="checkbox" checked={p.crearAuxiliares} onChange={(e) => setP({ ...p, crearAuxiliares: e.target.checked })} /> Crear los auxiliares contables que falten</label>
          <label className="check"><input type="checkbox" checked={p.crearFuncionarios} onChange={(e) => setP({ ...p, crearFuncionarios: e.target.checked })} /> Crear los funcionarios (responsables) que falten</label>
        </div>
        <p className="muted">Cada activo conserva el <b>código del VSIAF</b>. Si su responsable en el VSIAF existe, queda <b>asignado</b> a esa persona; el nombre de la oficina se guarda en las observaciones.</p>
        <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={leer}>Leer el VSIAF (vista previa)</button></div>
      </Card>
      {prev && (
        <Card title="3. Vista previa">
          <p><b>{prev.leidos}</b> activo(s) leídos · <b>{prev.nuevos}</b> nuevos para SIGAA · {prev.yaExisten} ya existen (se omiten) · {prev.auxiliaresNuevos} auxiliar(es) y {prev.funcionariosNuevos} funcionario(s) por crear</p>
          {prev.problemas.map((x: any, i: number) => <p key={i} className="warn">⚠ {x.codigo ? x.codigo + ': ' : ''}{x.mensaje}</p>)}
          <DataTable rows={prev.porGrupo} empty="Nada nuevo para traer." cols={[{ key: 'grupo', header: 'Grupo contable' }, { key: 'cantidad', header: 'Cant.', num: true }, { key: 'costo', header: 'Costo Bs', money: true }]} />
          <h3 style={{ marginTop: 14 }}>Primeros activos</h3>
          <DataTable maxHeight="30vh" rows={prev.muestra} cols={[{ key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' }, { key: 'grupo', header: 'Grupo' }, { key: 'auxiliar', header: 'Auxiliar' }, { key: 'oficina', header: 'Oficina' }, { key: 'responsable', header: 'Responsable' }, { key: 'fecha', header: 'Fecha', render: (r) => fmtDate(r.fecha) }, { key: 'costo', header: 'Costo Bs', money: true }]} />
          {puede('af') && <div style={{ marginTop: 10 }}><button className="ok" disabled={busy || !prev.nuevos} onClick={traer}>Importar {prev.nuevos} activo(s) a SIGAA</button></div>}
        </Card>
      )}
      {fin && (
        <Card title={`Importación realizada — lote ${fin.lote}`}>
          <p className="ok-txt">✔ {fin.importados} activo(s) importados · {fin.auxiliaresNuevos} auxiliar(es) y {fin.funcionariosNuevos} funcionario(s) creados · {fin.yaExistian} ya existían.</p>
          <p className="muted">Complete en <b>Fichas técnicas</b> lo que el VSIAF no tiene (marca, modelo, serie, fotografías) y emita las <b>etiquetas con QR</b>.</p>
        </Card>
      )}
    </>
  );
}
