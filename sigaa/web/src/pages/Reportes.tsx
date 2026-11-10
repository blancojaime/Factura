import { useMemo, useState } from 'react';
import { abrirDocumento, abrirReporte, get, hoy } from '../api';
import { Card, DataTable, DateField, Datalist, PageHead, SelectField, Tabs, TextField, useAction, useLoad } from '../ui';

const MOD: Record<string, string> = { alm: 'Almacenes', com: 'Combustible', af: 'Activos fijos' };

export default function Reportes() {
  const { data: reps } = useLoad<any[]>(() => get('/reportes'));
  const { data: docs } = useLoad<any[]>(() => get('/documentos'));
  const { data: bods } = useLoad<any[]>(() => get('/alm/meta').then((m) => m.bodegas));
  const { data: funcs } = useLoad<any[]>(() => get('/maestros/funcionarios'));
  const { data: edifs } = useLoad<any[]>(() => get('/maestros/edificios'));
  const [mod, setMod] = useState<'alm' | 'com' | 'af'>('alm');
  const [sel, setSel] = useState<string>('');
  const [params, setParams] = useState<Record<string, string>>({ desde: `${hoy().slice(0, 4)}-01-01`, hasta: hoy() });
  const [vista, setVista] = useState<any>(null);
  const [run, busy] = useAction();
  const [docId, setDocId] = useState('');
  const [docRef, setDocRef] = useState('');
  const [docDoc, setDocDoc] = useState('ACTAVER');
  const lista = useMemo(() => (reps ?? []).filter((r) => r.modulo === mod), [reps, mod]);
  const rep = reps?.find((r) => r.id === sel);
  const q = () => Object.fromEntries(Object.entries(params).filter(([, v]) => v));
  const docsMod = (docs ?? []).filter((d) => d.modulo === mod);
  const doc = docs?.find((d) => d.id === docId);

  return (
    <>
      <PageHead title="Reportes y documentos" sub="Los mismos productos de los sistemas originales, en PDF y Excel" />
      <Tabs value={mod} onChange={(m) => { setMod(m); setSel(''); setVista(null); setDocId(''); }} items={[{ id: 'alm', label: 'Almacenes' }, { id: 'com', label: 'Combustible' }, { id: 'af', label: 'Activos fijos' }]} />
      <div className="split" style={{ gridTemplateColumns: 'minmax(280px,360px) minmax(0,1fr)' }}>
        <div>
          <Card title={`Reportes de ${MOD[mod]}`}>
            {lista.map((r) => <div key={r.id}><button className="link" style={{ padding: '4px 0', textAlign: 'left', fontWeight: r.id === sel ? 700 : 400 }} onClick={() => { setSel(r.id); setVista(null); }}>{r.nombre}</button></div>)}
          </Card>
          <Card title={`Documentos de ${MOD[mod]}`}>
            <SelectField label="Documento" value={docId} onChange={(v) => { setDocId(v); setDocRef(''); }} options={docsMod.map((d) => ({ value: d.id, label: d.nombre }))} />
            {doc && (
              <div style={{ marginTop: 8 }}>
                <TextField label={doc.ref} value={docRef} onChange={setDocRef} placeholder="Ej.: CGI-0001/2026" />
                {doc.id === 'alm-baja' && <SelectField label="Documento del expediente" value={docDoc} onChange={setDocDoc} blank={false} options={['ACTAVER', 'INFSOL', 'INFTEC', 'MEMOCOM', 'ACTADEST', 'ACTAENT', 'REGBAJA', 'CONVOC']} />}
                {doc.id === 'alm-kardex' && <div className="grid" style={{ gridTemplateColumns: '1fr' }}><SelectField label="Bodega" value={params.bodega} onChange={(v) => setParams({ ...params, bodega: v })} options={(bods ?? []).map((b: any) => ({ value: b.cod, label: b.nombre }))} /><DateField label="Desde" value={params.desde} onChange={(v) => setParams({ ...params, desde: v })} /><DateField label="Hasta" value={params.hasta} onChange={(v) => setParams({ ...params, hasta: v })} /></div>}
                <div style={{ marginTop: 8 }}><button className="primary" disabled={!docRef} onClick={() => abrirDocumento(doc.id, docRef, { doc: docDoc, bodega: params.bodega, desde: params.desde, hasta: params.hasta })}>Generar PDF</button></div>
              </div>
            )}
          </Card>
        </div>
        <div>
          {!rep && <Card><div className="empty">Seleccione un reporte de la lista.</div></Card>}
          {rep && (
            <Card title={rep.nombre}>
              <div className="grid">
                {rep.params.map((p: any) => {
                  const set = (v: string) => setParams({ ...params, [p.name]: v });
                  if (p.type === 'date') return <DateField key={p.name} label={p.label} value={params[p.name]} onChange={set} />;
                  if (p.type === 'bodega') return <SelectField key={p.name} label={p.label} value={params[p.name]} onChange={set} options={[{ value: 'TODAS', label: 'TODAS LAS BODEGAS' }, ...(bods ?? []).map((b: any) => ({ value: b.cod, label: b.nombre }))]} blank={false} />;
                  if (p.type === 'funcionario') return <SelectField key={p.name} label={p.label} value={params[p.name]} onChange={set} options={(funcs ?? []).map((f: any) => f.nombre)} />;
                  if (p.type === 'edificio') return <SelectField key={p.name} label={p.label} value={params[p.name]} onChange={set} options={(edifs ?? []).map((e: any) => ({ value: e.cod_edif, label: `${String(e.cod_edif).padStart(3, '0')} - ${e.edificio}` }))} />;
                  if (p.type === 'select') return <SelectField key={p.name} label={p.label} value={params[p.name]} onChange={set} options={p.options ?? []} blank={false} />;
                  return <TextField key={p.name} label={p.label} value={params[p.name]} onChange={set} />;
                })}
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <button className="primary" onClick={() => abrirReporte(rep.id, 'pdf', q())}>PDF</button>
                <button className="ok" onClick={() => abrirReporte(rep.id, 'xlsx', q())}>Excel</button>
                <button disabled={busy} onClick={() => run(async () => setVista(await get(`/reportes/${rep.id}`, q())))}>Vista previa</button>
              </div>
              {vista && (
                <div style={{ marginTop: 14 }}>
                  <h3>{vista.titulo}</h3><p className="muted">{vista.subtitulo}</p>
                  <DataTable rows={vista.filas.map((f: any[]) => Object.fromEntries(f.map((x, i) => [String(i), x])))} cols={vista.cols.map((c: any, i: number) => ({ key: String(i), header: c.header, num: !!c.num }))} maxHeight="50vh" />
                  <small className="muted">{vista.filas.length} fila(s)</small>
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
      <Datalist id="_x" options={[]} />
    </>
  );
}
