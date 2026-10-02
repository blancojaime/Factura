import { useRef, useState } from 'react';
import { abrirDocumento, del, get, put, subirFoto, urlConToken } from '../../api';
import { useAuth } from '../../auth';
import { Badge, Card, DataTable, Field, NumField, PageHead, SelectField, TextField, AreaField, useAction, useLoad } from '../../ui';
import { useAfMeta } from './common';

export default function AfFichas() {
  const { puede } = useAuth();
  const { data: meta } = useAfMeta();
  const [texto, setTexto] = useState('');
  const { data: lista } = useLoad<any[]>(() => get('/af/activos', { texto, limite: 200 }), [texto]);
  const [a, setA] = useState<any>(null);
  const [f, setF] = useState<any>({});
  const [run, busy] = useAction();
  const fileRef = useRef<HTMLInputElement>(null);
  const [slot, setSlot] = useState(1);
  const cargar = (codigo: string) => run(async () => {
    const d = await get(`/af/activos/${encodeURIComponent(codigo)}`);
    setA(d);
    setF({ descripcion: d.descripcion, marca: d.marca ?? '', modelo: d.modelo ?? '', serie: d.serie ?? '', color: d.color ?? '', estado: d.estado, valor: d.valor, observaciones: d.observaciones ?? '', campos: Object.fromEntries(d.campos.map((c: any) => [String(c.nro), c.valor ?? ''])) });
  });
  const idx = a ? (lista ?? []).findIndex((x) => x.codigo === a.codigo) : -1;
  const editable = puede('af');
  return (
    <>
      <PageHead title="Ficha técnica del activo fijo" sub="Registro a detalle de cada código: características propias según su cuenta y hasta 4 fotografías" />
      <div className="split" style={{ gridTemplateColumns: 'minmax(260px,340px) minmax(0,1fr)' }}>
        <Card title="Buscar activo">
          <TextField label="Código o descripción" value={texto} onChange={setTexto} />
          <div style={{ marginTop: 8 }}><DataTable maxHeight="62vh" rows={lista ?? []} onRow={(r) => cargar(r.codigo)} selected={(r) => r.codigo === a?.codigo} cols={[{ key: 'codigo', header: 'Código' }, { key: 'auxiliar', header: 'Auxiliar' }, { key: 'situacion', header: '', badge: true }]} /></div>
        </Card>
        {a ? (
          <div>
            <Card title={`${a.codigo}`} right={<span className="row"><button className="sm" disabled={idx <= 0} onClick={() => cargar(lista![idx - 1].codigo)}>← Anterior</button><button className="sm" disabled={idx < 0 || idx >= (lista?.length ?? 0) - 1} onClick={() => cargar(lista![idx + 1].codigo)}>Siguiente →</button><Badge v={a.situacion} /></span>}>
              <div className="grid">
                <TextField className="span2" label="Descripción" req value={f.descripcion} onChange={(v) => setF({ ...f, descripcion: v })} disabled={!editable} />
                <SelectField label="Estado físico" blank={false} value={f.estado} onChange={(v) => setF({ ...f, estado: v })} disabled={!editable} options={(meta?.estados ?? []).map((e) => e.estado)} />
                <NumField label="Valor (Bs)" value={f.valor} onChange={(v) => setF({ ...f, valor: v })} disabled={!editable} />
                <Field label="Cuenta contable"><input readOnly value={a.cuenta ?? ''} /></Field>
                <Field label="Auxiliar"><input readOnly value={a.auxiliar ?? ''} /></Field>
                <Field label="Fecha de ingreso"><input readOnly value={a.fecha_ingreso ?? ''} /></Field>
                <Field label="Funcionario / ubicación"><input readOnly value={`${a.funcionario ?? 'En almacén'} — ${a.ubicacion_actual ?? ''}`} /></Field>
                <TextField label="Marca" value={f.marca} onChange={(v) => setF({ ...f, marca: v })} disabled={!editable} />
                <TextField label="Modelo" value={f.modelo} onChange={(v) => setF({ ...f, modelo: v })} disabled={!editable} />
                <TextField label="Serie" value={f.serie} onChange={(v) => setF({ ...f, serie: v })} disabled={!editable} />
                <TextField label="Color" value={f.color} onChange={(v) => setF({ ...f, color: v })} disabled={!editable} />
              </div>
              <h3 style={{ marginTop: 12 }}>Características técnicas de la cuenta «{a.cuenta}»</h3>
              <div className="grid c2">
                {a.campos.map((c: any) => <TextField key={c.nro} label={c.campo} hint={c.descripcion} value={f.campos?.[String(c.nro)] ?? ''} onChange={(v) => setF({ ...f, campos: { ...f.campos, [String(c.nro)]: v } })} disabled={!editable} />)}
              </div>
              <AreaField label="Observaciones" value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} disabled={!editable} />
            </Card>
            <Card title="Registro fotográfico (4 fotos por activo)">
              <div className="photos">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n}>
                    <div className="photo">{a['foto' + n] ? <img alt={`Foto ${n}`} src={urlConToken(`/af/fotos/${a['foto' + n]}`) + `&t=${Date.now() % 100000}`} /> : `Foto ${n}`}</div>
                    {editable && <div className="row" style={{ marginTop: 4, gap: 4 }}><button className="sm" onClick={() => { setSlot(n); fileRef.current?.click(); }}>{a['foto' + n] ? 'Cambiar' : 'Subir'}</button>{a['foto' + n] && <button className="sm danger" onClick={() => run(async () => { await del(`/af/activos/${encodeURIComponent(a.codigo)}/foto/${n}`); await cargar(a.codigo); })}>Quitar</button>}</div>}
                  </div>))}
              </div>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => { const file = e.target.files?.[0]; e.target.value = ''; if (file) run(async () => { await subirFoto(a.codigo, slot, file); await cargar(a.codigo); }, 'Fotografía guardada.'); }} />
            </Card>
            <div className="row">
              {editable && <button className="primary" disabled={busy} onClick={() => run(async () => { await put(`/af/activos/${encodeURIComponent(a.codigo)}`, f); await cargar(a.codigo); }, 'Ficha guardada.')}>Guardar ficha</button>}
              <button onClick={() => abrirDocumento('af-ficha', a.codigo)}>Imprimir ficha (PDF)</button>
            </div>
          </div>
        ) : <Card><div className="empty">Busque un activo y selecciónelo de la lista.</div></Card>}
      </div>
    </>
  );
}
