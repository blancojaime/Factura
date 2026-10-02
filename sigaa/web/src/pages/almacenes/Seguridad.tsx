import { useState } from 'react';
import { abrirDocumento, get, hoy, post, fmtDate } from '../../api';
import { useAuth } from '../../auth';
import { Badge, Card, DataTable, DateField, PageHead, SelectField, Tabs, TextField, useAction, useLoad } from '../../ui';
import { nroUrl, useAlmMeta } from './common';

export default function AlmSeguridad() {
  const { puede } = useAuth();
  const { data: meta } = useAlmMeta();
  const [t, setT] = useState<'insp' | 'ext'>('insp');
  const { data: lista, reload } = useLoad<any[]>(() => get('/alm/inspecciones'));
  const { data: al } = useLoad<any>(() => get('/alm/alertas-seguridad'));
  const { data: ext } = useLoad<any[]>(() => get('/maestros/extintores'));
  const { data: seg } = useLoad<any[]>(() => get('/maestros/seguros'));
  const [h, setH] = useState<any>({ nro: '', fecha: hoy(), cod_bod: '', inspector: '' });
  const [res, setRes] = useState<{ resultado: string; obs: string }[]>([]);
  const [run, busy] = useAction();
  const criterios = meta?.criterios_inspeccion ?? [];
  const nueva = () => { setH({ nro: '', fecha: hoy(), cod_bod: '', inspector: meta?.config.NombreALM ?? '' }); setRes(criterios.map(() => ({ resultado: '', obs: '' }))); };
  const cargar = (nro: string) => run(async () => {
    const d = await get(`/alm/inspecciones/${nroUrl(nro)}`);
    setH({ nro: d.nro, fecha: d.fecha, cod_bod: d.cod_bod, inspector: d.inspector });
    setRes(criterios.map((c) => { const x = d.items.find((i: any) => i.criterio === c); return { resultado: x?.resultado ?? '', obs: x?.obs ?? '' }; }));
  });
  const cumple = res.filter((r) => r.resultado === 'CUMPLE').length;
  const no = res.filter((r) => r.resultado === 'NO CUMPLE').length;
  return (
    <>
      <PageHead title="Higiene, seguridad y salvaguarda de almacenes" sub="Inspección periódica · medidas correctivas · extintores y seguros" />
      {al && (al.extintoresVencidos.length + al.extintoresPorVencer.length + al.segurosVencidos.length + al.segurosPorVencer.length > 0) && (
        <Card title="Alertas">
          {al.extintoresVencidos.map((e: any) => <div key={e.cod} className="alert critico">Extintor {e.cod}: recarga VENCIDA el {fmtDate(e.venc_recarga)}</div>)}
          {al.extintoresPorVencer.map((e: any) => <div key={e.cod} className="alert aviso">Extintor {e.cod}: recarga vence el {fmtDate(e.venc_recarga)}</div>)}
          {al.segurosVencidos.map((e: any) => <div key={e.poliza} className="alert critico">Póliza {e.poliza}: VENCIDA el {fmtDate(e.hasta)}</div>)}
          {al.segurosPorVencer.map((e: any) => <div key={e.poliza} className="alert aviso">Póliza {e.poliza}: vence el {fmtDate(e.hasta)}</div>)}
        </Card>
      )}
      <Tabs value={t} onChange={setT} items={[{ id: 'insp', label: 'Inspecciones' }, { id: 'ext', label: 'Extintores y seguros' }]} />
      {t === 'insp' && (
        <div className="split" style={{ gridTemplateColumns: 'minmax(240px,300px) minmax(0,1fr)' }}>
          <Card title="Inspecciones" right={puede('alm') && <button className="primary sm" onClick={nueva}>Nueva</button>}>
            <DataTable rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === h.nro} cols={[{ key: 'nro', header: 'Nº' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'cumple', header: 'Cumple', num: true }, { key: 'no_cumple', header: 'No', num: true }]} />
          </Card>
          <Card title={h.nro || (res.length ? 'Nueva inspección' : 'Seleccione o cree una inspección')} right={res.length ? <span>Cumple {cumple} · No cumple {no}{cumple + no ? ` (${Math.round((cumple / (cumple + no)) * 100)}%)` : ''}</span> : undefined}>
            {res.length > 0 && (
              <>
                <div className="grid"><DateField label="Fecha" req value={h.fecha} onChange={(v) => setH({ ...h, fecha: v })} /><SelectField label="Bodega inspeccionada" req value={h.cod_bod} onChange={(v) => setH({ ...h, cod_bod: v })} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} /><TextField label="Inspector / responsable" req value={h.inspector} onChange={(v) => setH({ ...h, inspector: v })} /></div>
                <div className="table-wrap" style={{ marginTop: 10, maxHeight: '55vh' }}>
                  <table className="t"><thead><tr><th>N°</th><th>Criterio de verificación</th><th style={{ width: 130 }}>Resultado</th><th>Observación / medida correctiva</th></tr></thead>
                    <tbody>{criterios.map((c, i) => (
                      <tr key={i}><td className="ctr">{i + 1}</td><td>{c}</td>
                        <td><select value={res[i]?.resultado ?? ''} onChange={(e) => setRes(res.map((r, j) => (j === i ? { ...r, resultado: e.target.value } : r)))}><option value="" />{['CUMPLE', 'NO CUMPLE', 'N/A'].map((x) => <option key={x}>{x}</option>)}</select></td>
                        <td><input value={res[i]?.obs ?? ''} onChange={(e) => setRes(res.map((r, j) => (j === i ? { ...r, obs: e.target.value } : r)))} /></td></tr>))}</tbody></table>
                </div>
                <div className="row" style={{ marginTop: 10 }}>
                  {puede('alm') && <button className="primary" disabled={busy} onClick={() => run(async () => { const r = await post('/alm/inspecciones', { ...h, items: criterios.map((c, i) => ({ criterio: c, resultado: res[i].resultado, obs: res[i].obs })) }); await reload(); await cargar(r.nro); }, 'Inspección guardada.')}>Guardar</button>}
                  {h.nro && <button onClick={() => abrirDocumento('alm-acta-inspeccion', h.nro)}>Acta de inspección</button>}
                  {h.nro && no > 0 && <button onClick={() => abrirDocumento('alm-nota-mantenimiento', h.nro)}>Nota de mantenimiento</button>}
                </div>
              </>
            )}
          </Card>
        </div>
      )}
      {t === 'ext' && (
        <>
          <Card title="Extintores"><DataTable rows={ext ?? []} cols={[{ key: 'cod', header: 'Código' }, { key: 'cod_bod', header: 'Bodega' }, { key: 'tipo', header: 'Tipo' }, { key: 'capacidad', header: 'Capacidad' }, { key: 'ult_recarga', header: 'Últ. recarga', date: true }, { key: 'venc_recarga', header: 'Vence', date: true }, { key: 'estado', header: 'Estado', render: (r) => <Badge v={r.venc_recarga && r.venc_recarga < hoy() ? 'VENCIDO' : r.estado} /> }]} /><small className="muted">Administre extintores y pólizas en Catálogos y bases de datos → Almacenes.</small></Card>
          <Card title="Pólizas de seguro"><DataTable rows={seg ?? []} cols={[{ key: 'poliza', header: 'Póliza' }, { key: 'aseguradora', header: 'Aseguradora' }, { key: 'cobertura', header: 'Cobertura' }, { key: 'desde', header: 'Desde', date: true }, { key: 'hasta', header: 'Hasta', date: true }, { key: 'monto_asegurado', header: 'Monto Bs', money: true }, { key: 'estado', header: 'Estado', badge: true }]} /></Card>
        </>
      )}
    </>
  );
}
