import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post, put } from '../../api';
import { useAuth } from '../../auth';
import { useNavigate } from 'react-router-dom';
import { Badge, Card, DataTable, DateField, Modal, PageHead, SelectField, TextField, useAction, useLoad, useUi } from '../../ui';
import { nroUrl, useAlmMeta } from './common';

export default function AlmInventarios() {
  const { puede } = useAuth();
  const ui = useUi();
  const nav = useNavigate();
  const { data: meta } = useAlmMeta();
  const { data: lista, reload } = useLoad<any[]>(() => get('/alm/inventarios'));
  const [inv, setInv] = useState<any>(null);
  const [lineas, setLineas] = useState<Record<string, { conteo: string; estado_bien: string; obs: string }>>({});
  const [nuevo, setNuevo] = useState<any>(null);
  const [run, busy] = useAction();
  const { data: funcs } = useLoad<any[]>(() => get('/maestros/funcionarios'));
  const abierto = inv && inv.estado !== 'CERRADO';
  const ciego = inv && inv.items.length > 0 && inv.items[0].saldo_sist === null;

  const cargar = (nro: string) => run(async () => {
    const d = await get(`/alm/inventarios/${nroUrl(nro)}`);
    setInv(d);
    setLineas(Object.fromEntries(d.items.map((x: any) => [x.cod_item, { conteo: x.conteo ?? '', estado_bien: x.estado_bien ?? '', obs: x.obs ?? '' }])));
  });
  const setL = (cod: string, k: string, v: string) => setLineas({ ...lineas, [cod]: { ...lineas[cod], [k]: v } });
  const guardar = () => run(async () => {
    await put(`/alm/inventarios/${nroUrl(inv.nro)}/conteo`, { lineas: Object.entries(lineas).map(([cod_item, l]) => ({ cod_item, conteo: l.conteo === '' ? null : Number(l.conteo), estado_bien: l.estado_bien, obs: l.obs })) });
    await cargar(inv.nro);
  }, 'Conteo guardado.');
  const cerrar = async () => {
    if (!(await ui.confirm(`¿Cerrar el inventario ${inv.nro}? Ya no podrá modificarse.\nRecuerde imprimir el Acta de Inventario y, si hay diferencias, el informe al Director Administrativo Financiero.`))) return;
    run(async () => { await guardarSilencioso(); const r = await post(`/alm/inventarios/${nroUrl(inv.nro)}/cerrar`); await cargar(inv.nro); await reload(); ui.ok(`Inventario cerrado. Faltantes Bs ${fmt2(r.faltante_bs)} · Sobrantes Bs ${fmt2(r.sobrante_bs)}`); });
  };
  const guardarSilencioso = () => put(`/alm/inventarios/${nroUrl(inv.nro)}/conteo`, { lineas: Object.entries(lineas).map(([cod_item, l]) => ({ cod_item, conteo: l.conteo === '' ? null : Number(l.conteo), estado_bien: l.estado_bien, obs: l.obs })) });
  const sobrantes = async () => {
    if (!(await ui.confirm('Se registrará un ingreso por ajuste de los sobrantes valorados al último precio de compra (cotización de un bien similar). Luego deberá completar la autorización y los documentos y confirmar el ingreso.'))) return;
    run(async () => { const r = await post(`/alm/inventarios/${nroUrl(inv.nro)}/sobrantes`); ui.ok(`Se creó el ingreso por ajuste ${r.cgi}.`); nav('/almacenes/ingresos'); });
  };
  const faltantes = async () => {
    if (!(await ui.confirm('El Manual indica que el faltante debe ser REPUESTO por el encargado (Acta de Reposición). Si no se repone, corresponde iniciar la baja por pérdida y determinar responsabilidad.\n\n¿Iniciar el expediente de baja por los faltantes?'))) return;
    run(async () => { const d = await get(`/alm/inventarios/${nroUrl(inv.nro)}/baja-faltante`); const r = await post('/alm/bajas', { ...d, fecha: hoy() }); ui.ok(`Expediente ${r.nro} creado. Complete el trámite.`); nav('/almacenes/bajas'); });
  };
  const crear = () => run(async () => { const r = await post('/alm/inventarios', nuevo); setNuevo(null); await reload(); await cargar(r.nro); ui.ok(`Inventario ${r.nro} abierto con ${r.items} ítems.`); });
  const contados = inv ? Object.values(lineas).filter((l) => l.conteo !== '').length : 0;
  return (
    <>
      <PageHead title="Toma de inventario físico de existencias" sub="Programado · Sorpresivo · Cambio de encargado · Anual de cierre de gestión">
        {puede('alm') && <button className="primary" onClick={() => setNuevo({ fecha: hoy(), tipo: 'PROGRAMADO', cod_bod: '' })}>Nuevo inventario</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: 'minmax(260px,330px) minmax(0,1fr)' }}>
        <Card title="Inventarios">
          <DataTable maxHeight="70vh" rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === inv?.nro} cols={[{ key: 'nro', header: 'Nº' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'tipo', header: 'Tipo' }, { key: 'estado', header: 'Estado', badge: true }]} />
        </Card>
        {inv ? (
          <div>
            <Card title={`${inv.nro} · ${inv.bodega}`} right={<Badge v={inv.estado} />}>
              <div className="grid">
                <div><small className="muted">Tipo</small><div>{inv.tipo}</div></div>
                <div><small className="muted">Responsable</small><div>{inv.responsable}</div></div>
                <div><small className="muted">Designado(s)</small><div>{inv.designado}</div></div>
                <div><small className="muted">Observador</small><div>{inv.observador}</div></div>
                <div><small className="muted">Corte de documentación</small><div>{[inv.corte_ing, inv.corte_sal].filter(Boolean).join(' | ')}</div></div>
                <div><small className="muted">Contados</small><div>{contados} de {inv.items.length}</div></div>
                {inv.estado === 'CERRADO' && <div><small className="muted">Faltantes / sobrantes (Bs)</small><div>{fmt2(inv.faltante_bs)} / {fmt2(inv.sobrante_bs)}</div></div>}
              </div>
              {ciego && <div className="alert info" style={{ marginTop: 8 }}>Conteo ciego: el saldo del sistema se muestra recién al cerrar el inventario (buena práctica de control).</div>}
            </Card>
            <Card title="Conteo físico">
              <div className="table-wrap" style={{ maxHeight: '55vh' }}>
                <table className="t">
                  <thead><tr><th>Código</th><th>Descripción</th><th>Unid.</th>{!ciego && <th className="num">Saldo sist.</th>}<th className="num" style={{ width: 110 }}>Conteo físico</th>{!ciego && <th className="num">Dif.</th>}<th style={{ width: 130 }}>Estado del bien</th><th>Observación</th></tr></thead>
                  <tbody>
                    {inv.items.map((x: any) => {
                      const l = lineas[x.cod_item] ?? { conteo: '', estado_bien: '', obs: '' };
                      const dif = l.conteo === '' || ciego ? null : Number(l.conteo) - Number(x.saldo_sist);
                      return (
                        <tr key={x.cod_item}>
                          <td>{x.cod_item}</td><td>{x.descripcion}</td><td>{x.unidad}</td>
                          {!ciego && <td className="num">{x.saldo_sist}</td>}
                          <td><input type="number" step="any" disabled={!abierto || !puede('alm')} value={l.conteo} onChange={(e) => setL(x.cod_item, 'conteo', e.target.value)} /></td>
                          {!ciego && <td className="num" style={{ color: dif ? (dif < 0 ? 'var(--danger)' : 'var(--accent)') : undefined, fontWeight: dif ? 700 : 400 }}>{dif === null ? '' : dif}</td>}
                          <td><select disabled={!abierto} value={l.estado_bien} onChange={(e) => setL(x.cod_item, 'estado_bien', e.target.value)}><option />{(meta?.estados_bien ?? []).map((s) => <option key={s}>{s}</option>)}</select></td>
                          <td><input disabled={!abierto} value={l.obs} onChange={(e) => setL(x.cod_item, 'obs', e.target.value)} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
            <div className="row">
              {abierto && puede('alm') && <button className="primary" disabled={busy} onClick={guardar}>Guardar conteo</button>}
              {abierto && puede('alm') && <button disabled={busy} onClick={() => run(async () => { await post(`/alm/inventarios/${nroUrl(inv.nro)}/actualizar-saldos`); await cargar(inv.nro); }, 'Saldos actualizados.')}>Actualizar saldos</button>}
              {abierto && puede('alm') && <button className="ok" disabled={busy} onClick={cerrar}>Cerrar inventario</button>}
              <button onClick={() => abrirDocumento('alm-hoja-conteo', inv.nro)}>Hoja de conteo</button>
              <button onClick={() => abrirDocumento('alm-acta-inventario', inv.nro)}>Acta de inventario</button>
              <button onClick={() => abrirDocumento('alm-inventario-valorado', inv.nro)}>Inventario valorado</button>
              {inv.estado === 'CERRADO' && Number(inv.sobrante_bs) > 0 && puede('alm') && <button onClick={sobrantes}>Ingresar sobrantes</button>}
              {inv.estado === 'CERRADO' && Number(inv.faltante_bs) > 0 && <button onClick={() => abrirDocumento('alm-acta-reposicion', inv.nro)}>Acta de reposición</button>}
              {inv.estado === 'CERRADO' && Number(inv.faltante_bs) > 0 && puede('alm') && <button className="danger" onClick={faltantes}>Baja por faltantes</button>}
            </div>
          </div>
        ) : <Card><div className="empty">Seleccione un inventario o abra uno nuevo.</div></Card>}
      </div>
      {nuevo && (
        <Modal title="Nuevo inventario físico" onClose={() => setNuevo(null)} footer={<><button onClick={() => setNuevo(null)}>Cancelar</button><button className="primary" disabled={busy} onClick={crear}>Abrir inventario</button></>}>
          <div className="grid c2">
            <DateField label="Fecha" req value={nuevo.fecha} onChange={(v) => setNuevo({ ...nuevo, fecha: v })} />
            <SelectField label="Bodega" req value={nuevo.cod_bod} onChange={(v) => setNuevo({ ...nuevo, cod_bod: v })} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
            <SelectField label="Tipo de inventario" req blank={false} value={nuevo.tipo} onChange={(v) => setNuevo({ ...nuevo, tipo: v })} options={meta?.tipos_inventario ?? []} />
            <SelectField label="Filtrar por subgrupo (opcional)" value={nuevo.filtro_subgrupo} onChange={(v) => setNuevo({ ...nuevo, filtro_subgrupo: v })} options={(meta?.subgrupos ?? []).map((s) => ({ value: `${s.grupo}-${s.subgrupo}`, label: `${s.grupo}-${s.subgrupo} ${s.nombre}` }))} />
            <TextField label="Funcionario(s) designado(s)" value={nuevo.designado} onChange={(v) => setNuevo({ ...nuevo, designado: v })} />
            <SelectField label="Observador / testigo" value={nuevo.observador} onChange={(v) => setNuevo({ ...nuevo, observador: v })} options={(funcs ?? []).map((f) => f.nombre)} />
          </div>
        </Modal>
      )}
    </>
  );
}
