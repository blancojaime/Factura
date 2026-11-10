import { useMemo, useState } from 'react';
import { get, post } from '../../api';
import { Badge, DataTable, Modal, TextField, useAction, useLoad, useUi } from '../../ui';

/** Qué datos de la ficha se pueden copiar (por defecto lo propio del lote: no la serie ni el valor). */
const DATOS: { key: string; label: string; def: boolean; aviso?: string }[] = [
  { key: 'marca', label: 'Marca', def: true },
  { key: 'modelo', label: 'Modelo', def: true },
  { key: 'color', label: 'Color', def: true },
  { key: 'caracteristicas', label: 'Características técnicas (material, dimensiones…)', def: true },
  { key: 'observaciones', label: 'Observaciones', def: true },
  { key: 'descripcion', label: 'Descripción del activo', def: false },
  { key: 'estado', label: 'Estado físico', def: false },
  { key: 'valor', label: 'Valor (Bs)', def: false },
  { key: 'serie', label: 'Serie', def: false, aviso: 'La serie es propia de cada bien; cópiela solo si corresponde.' },
  { key: 'fotos', label: 'Fotografías (cada activo recibe su propia copia)', def: false },
];

/** Copia la ficha técnica de un activo a uno o varios activos (p. ej. 100 pupitres de una misma compra). */
export default function CopiarFicha({ origen, onClose, onDone }: { origen: any; onClose: () => void; onDone: () => void }) {
  const ui = useUi();
  const [run, busy] = useAction();
  const [mismo, setMismo] = useState(true);
  const [texto, setTexto] = useState('');
  const [pegados, setPegados] = useState('');
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [datos, setDatos] = useState<Record<string, boolean>>(Object.fromEntries(DATOS.map((d) => [d.key, d.def])));
  const [reemplazar, setReemplazar] = useState(false);
  const { data: lista } = useLoad<any[]>(
    () => get('/af/activos', { texto, id_cta: mismo ? origen.id_cta : undefined, id_aux: mismo ? origen.id_aux : undefined, limite: 2000 }),
    [texto, mismo, origen.codigo],
  );
  const filas = useMemo(() => (lista ?? []).filter((x) => x.codigo !== origen.codigo && x.situacion !== 'BAJA'), [lista, origen.codigo]);
  const sinFicha = (x: any) => !x.marca && !x.modelo && !x.color;
  const toggle = (c: string) => { const n = new Set(sel); n.has(c) ? n.delete(c) : n.add(c); setSel(n); };
  const marcar = (f: (x: any) => boolean) => setSel(new Set([...sel, ...filas.filter(f).map((x) => x.codigo)]));
  const codigosPegados = useMemo(() => pegados.split(/[\s,;]+/).map((x) => x.trim().toUpperCase()).filter(Boolean), [pegados]);
  const destinos = useMemo(() => [...new Set([...sel, ...codigosPegados])].filter((c) => c !== origen.codigo), [sel, codigosPegados, origen.codigo]);
  const elegidos = Object.entries(datos).filter(([, v]) => v).map(([k]) => k);

  const copiar = async () => {
    if (!destinos.length) return ui.error('Marque al menos un activo de destino.');
    if (!elegidos.length) return ui.error('Marque al menos un dato para copiar.');
    const msg = `¿Copiar la ficha de ${origen.codigo} a ${destinos.length} activo(s)?\nSe copiará: ${DATOS.filter((d) => datos[d.key]).map((d) => d.label.split(' (')[0]).join(', ')}.\n${reemplazar ? 'Se REEMPLAZARÁN los datos que ya tengan.' : 'Solo se completarán los datos que estén vacíos.'}`;
    if (!(await ui.confirm(msg))) return;
    run(async () => {
      const r = await post(`/af/activos/${encodeURIComponent(origen.codigo)}/copiar-ficha`, { destinos, copiar: elegidos, solo_vacios: !reemplazar });
      let m = `Ficha copiada a ${r.copiados} activo(s).`;
      if (r.sin_caracteristicas) m += `\n${r.sin_caracteristicas} activo(s) son de otra cuenta: no se copiaron las características técnicas.`;
      if (r.omitidos?.length) m += `\nOmitidos (${r.omitidos.length}): ${r.omitidos.slice(0, 8).map((o: any) => `${o.codigo} (${o.motivo})`).join('; ')}${r.omitidos.length > 8 ? '…' : ''}`;
      ui.ok(m);
      onDone();
      onClose();
    });
  };

  return (
    <Modal wide title={`Copiar la ficha técnica de ${origen.codigo}`} onClose={onClose}
      footer={<><button onClick={onClose}>Cancelar</button><button className="primary" disabled={busy || !destinos.length} onClick={copiar}>Copiar a {destinos.length} activo(s)</button></>}>
      <div className="alert info"><span><b>{origen.descripcion}</b> — {origen.auxiliar ?? ''}. Marque qué datos copiar y a qué activos. Útil cuando se compran varios bienes iguales (por ejemplo, 100 pupitres).</span></div>

      <h3 style={{ marginTop: 10 }}>1. Qué datos copiar</h3>
      <div className="grid c2">
        {DATOS.map((d) => (
          <label key={d.key} style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
            <input type="checkbox" checked={datos[d.key]} onChange={(e) => setDatos({ ...datos, [d.key]: e.target.checked })} />
            <span>{d.label}{datos[d.key] && d.aviso && <small className="muted" style={{ display: 'block' }}>{d.aviso}</small>}</span>
          </label>
        ))}
      </div>
      <div className="row" style={{ marginTop: 6, gap: 16 }}>
        <label className="row" style={{ gap: 6 }}><input type="radio" checked={!reemplazar} onChange={() => setReemplazar(false)} /> Solo completar lo que esté vacío</label>
        <label className="row" style={{ gap: 6 }}><input type="radio" checked={reemplazar} onChange={() => setReemplazar(true)} /> Reemplazar lo que ya tengan</label>
      </div>

      <h3 style={{ marginTop: 12 }}>2. A qué activos copiar</h3>
      <div className="row" style={{ marginBottom: 6 }}>
        <label className="row" style={{ gap: 6 }}><input type="checkbox" checked={mismo} onChange={(e) => setMismo(e.target.checked)} /> Solo de la misma cuenta y auxiliar</label>
        <TextField label="Buscar (código o descripción)" value={texto} onChange={setTexto} />
        <button className="sm" onClick={() => marcar((x) => x.nro_ingreso && x.nro_ingreso === origen.nro_ingreso)} disabled={!origen.nro_ingreso}>Marcar los del mismo ingreso</button>
        <button className="sm" onClick={() => marcar(sinFicha)}>Marcar los sin ficha</button>
        <button className="sm" onClick={() => marcar(() => true)}>Marcar todos los de la lista</button>
        <button className="sm" onClick={() => setSel(new Set())}>Desmarcar</button>
      </div>
      <DataTable maxHeight="32vh" rows={filas} onRow={(r) => toggle(r.codigo)} cols={[
        { key: 's', header: '', render: (r: any) => <input type="checkbox" readOnly checked={sel.has(r.codigo)} /> },
        { key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' },
        { key: 'marca', header: 'Marca' }, { key: 'color', header: 'Color' },
        { key: 'ficha', header: 'Ficha', render: (r: any) => (sinFicha(r) ? <Badge v="PENDIENTE" /> : null) },
        { key: 'situacion', header: 'Situación', badge: true },
      ]} />
      <small className="muted">{filas.length} activo(s) en la lista · {sel.size} marcado(s){filas.length >= 2000 ? ' · mostrando los primeros 2.000' : ''}</small>
      <div style={{ marginTop: 8 }}>
        <label className="f"><span>O pegue códigos (uno por línea, o separados por coma): {codigosPegados.length ? `${codigosPegados.length} código(s)` : ''}</span>
          <textarea rows={2} value={pegados} onChange={(e) => setPegados(e.target.value)} placeholder="001-02-03007-02&#10;001-02-03007-03" /></label>
      </div>
      <p className="muted" style={{ marginBottom: 0 }}>Total de destinos: <b>{destinos.length}</b></p>
    </Modal>
  );
}
