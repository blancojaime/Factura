import { useEffect, useMemo, useState } from 'react';
import { get, post, put, del } from '../api';
import { useAuth } from '../auth';
import { Card, DataTable, Datalist, Field, Modal, PageHead, SelectField, useAction, useLoad, useUi, Badge } from '../ui';

interface MCol { name: string; label: string; type: string; required?: boolean; options?: string[]; ref?: string; readonly?: boolean; width?: number }
interface Meta { key: string; titulo: string; modulo: string; pk: string[]; autoId: boolean; cols: MCol[] }
const MODS: Record<string, string> = { core: 'Compartidos', alm: 'Almacenes', com: 'Combustible', af: 'Activos fijos' };

function Editor({ meta, fila, onClose, onSaved }: { meta: Meta; fila: Record<string, any> | null; onClose: () => void; onSaved: () => void }) {
  const [v, setV] = useState<Record<string, any>>(fila ?? {});
  const [refs, setRefs] = useState<Record<string, string[]>>({});
  const [run, busy] = useAction();
  useEffect(() => { meta.cols.filter((c) => c.ref).forEach((c) => get('/ref/' + c.ref).then((o) => setRefs((r) => ({ ...r, [c.name]: o })))); }, [meta]);
  const pkVal = fila ? meta.pk.map((k) => encodeURIComponent(String(fila[k]))).join('~') : '';
  const guardar = () => run(async () => {
    if (fila) await put(`/maestros/${meta.key}/${pkVal}`, v); else await post(`/maestros/${meta.key}`, v);
    onSaved();
  }, 'Registro guardado.');
  return (
    <Modal title={(fila ? 'Modificar' : 'Nuevo') + ' — ' + meta.titulo} onClose={onClose} footer={<><button onClick={onClose}>Cancelar</button><button className="primary" disabled={busy} onClick={guardar}>Guardar</button></>}>
      <div className="grid c2">
        {meta.cols.map((c) => {
          const bloqueada = c.readonly || (!!fila && meta.pk.includes(c.name) && !meta.autoId);
          const opts = c.options ?? refs[c.name];
          if (c.type === 'select' || (c.ref && refs[c.name]?.length)) return <SelectField key={c.name} label={c.label} req={c.required} value={v[c.name]} disabled={bloqueada} onChange={(x) => setV({ ...v, [c.name]: x })} options={opts ?? []} />;
          return (
            <Field key={c.name} label={c.label} req={c.required} className={c.type === 'longtext' ? 'span2' : ''}>
              <input type={c.type === 'number' ? 'number' : c.type === 'date' ? 'date' : 'text'} step="any" disabled={bloqueada} value={v[c.name] ?? ''} onChange={(e) => setV({ ...v, [c.name]: e.target.value })} />
            </Field>
          );
        })}
      </div>
    </Modal>
  );
}

export default function Catalogos() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: metas } = useLoad<Meta[]>(() => get('/maestros'));
  const [key, setKey] = useState('funcionarios');
  const [q, setQ] = useState('');
  const [edit, setEdit] = useState<{ fila: any | null } | null>(null);
  const meta = metas?.find((m) => m.key === key);
  const { data: filas, reload } = useLoad<any[]>(() => get(`/maestros/${key}`, { q }), [key, q]);
  const [run] = useAction();
  const grupos = useMemo(() => {
    const g: Record<string, Meta[]> = {};
    for (const m of metas ?? []) (g[m.modulo] ??= []).push(m);
    return g;
  }, [metas]);
  if (!meta) return null;
  const editable = puede(meta.modulo as any) || (meta.modulo === 'core' && puede('alm')) || (meta.modulo === 'core' && puede('com')) || (meta.modulo === 'core' && puede('af'));
  const cols = meta.cols.slice(0, 9).map((c) => ({ key: c.name, header: c.label, num: c.type === 'number', badge: c.name === 'estado' }));
  return (
    <>
      <PageHead title="Catálogos y bases de datos" sub="Datos maestros compartidos por los tres módulos (equivalentes a las hojas BD_* de los sistemas originales)">
        {editable && <button className="primary" onClick={() => setEdit({ fila: null })}>+ Nuevo registro</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: '260px minmax(0,1fr)' }}>
        <Card>
          {Object.entries(grupos).map(([mod, items]) => (
            <div key={mod} style={{ marginBottom: 8 }}>
              <h3 className="muted" style={{ textTransform: 'uppercase', fontSize: 11 }}>{MODS[mod]}</h3>
              {items.map((m) => <div key={m.key}><button className="link" style={{ padding: '3px 0', fontWeight: m.key === key ? 700 : 400, textAlign: 'left' }} onClick={() => { setKey(m.key); setQ(''); }}>{m.titulo}</button></div>)}
            </div>
          ))}
        </Card>
        <Card title={meta.titulo} right={<input style={{ width: 220 }} placeholder="Buscar…" value={q} onChange={(e) => setQ(e.target.value)} />}>
          <DataTable
            rows={filas ?? []}
            cols={[...cols, { key: '_a', header: '', render: (r: any) => editable ? (
              <span className="nowrap">
                <button className="sm" onClick={() => setEdit({ fila: r })}>Editar</button>{' '}
                <button className="sm danger" onClick={async () => {
                  if (!(await ui.confirm('¿Eliminar este registro?'))) return;
                  run(async () => { await del(`/maestros/${key}/${meta.pk.map((k) => encodeURIComponent(String(r[k]))).join('~')}`); reload(); }, 'Registro eliminado.');
                }}>×</button>
              </span>) : <Badge v={r.estado} /> }]}
          />
          <small className="muted">{filas?.length ?? 0} registro(s)</small>
        </Card>
      </div>
      {edit && <Editor meta={meta} fila={edit.fila} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload(); }} />}
      <Datalist id="_none" options={[]} />
    </>
  );
}
