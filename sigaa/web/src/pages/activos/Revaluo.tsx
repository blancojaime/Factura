import { useEffect, useMemo, useState } from 'react';
import { bajarArchivo, fmt2, fmtDate, get, hoy, post, put, del, urlConToken, subirArchivo } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, Kpi, Modal, NumField, PageHead, SelectField, Tabs, TextField, useAction, useLoad, useUi } from '../../ui';

type Vista = 'bandeja' | 'lotes';

/** Revalúo técnico de activos fijos (NC 4): bandeja → hoja de tasación → consolidación y aprobación. */
export default function AfRevaluo() {
  const [vista, setVista] = useState<Vista>('bandeja');
  const [loteId, setLoteId] = useState<number | null>(null);
  if (loteId) return <Lote id={loteId} volver={() => { setLoteId(null); setVista('lotes'); }} />;
  return (
    <>
      <PageHead title="Revalúo técnico de activos fijos" sub="Activos totalmente depreciados (valor en libros Bs 1), en estado Bueno, Regular o Malo y operativos. Método comparativo de mercado según la NC 4." />
      <Tabs value={vista} onChange={setVista} items={[{ id: 'bandeja', label: '1. Bandeja de selección' }, { id: 'lotes', label: '2. Lotes de revalúo (hojas de tasación y aprobación)' }]} />
      {vista === 'bandeja' ? <Bandeja abrir={setLoteId} /> : <Lotes abrir={setLoteId} />}
    </>
  );
}

function Bandeja({ abrir }: { abrir: (id: number) => void }) {
  const { puede } = useAuth();
  const ui = useUi();
  const [run, busy] = useAction();
  const meta = useLoad<any>(() => get('/af/revaluo/meta'));
  const [f, setF] = useState({ id_cta: '', id_aux: '', texto: '' });
  const [filas, setFilas] = useState<any[]>([]);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [modal, setModal] = useState(false);
  const [d, setD] = useState({ descripcion: '', perito: '', perito_cargo: '', comision: '' });
  const cargar = () => run(async () => { setFilas(await get('/af/revaluo/bandeja', f)); setSel(new Set()); });
  useEffect(() => { cargar(); /* eslint-disable-next-line */ }, [f.id_cta, f.id_aux]);
  const auxs = (meta.data?.auxiliares ?? []).filter((a: any) => !f.id_cta || a.id_cta === Number(f.id_cta));
  const todos = filas.length > 0 && sel.size === filas.length;
  const crear = () => run(async () => { const r = await post('/af/revaluo/lotes', { ...d, codigos: [...sel] }); ui.ok(`Lote ${r.nro} creado.`); setModal(false); abrir(r.id); });
  const noOperativo = async (a: any) => {
    const m = await ui.prompt(`Motivo por el que ${a.codigo} NO es operativo (desuso, obsoleto inservible o propuesto para baja):`);
    if (m) run(async () => { await put(`/af/revaluo/operativo/${encodeURIComponent(a.codigo)}`, { operativo: 'NO', motivo: m }); cargar(); }, 'Marcado como no operativo: sale de la bandeja.');
  };
  return (
    <>
      <Card title="Filtros">
        <div className="grid">
          <SelectField label="Cuenta contable" value={f.id_cta} onChange={(v) => setF({ ...f, id_cta: v, id_aux: '' })} options={(meta.data?.cuentas ?? []).map((c: any) => ({ value: c.id_cta, label: `${String(c.id_cta).padStart(2, '0')} - ${c.cuenta}` }))} />
          <SelectField label="Auxiliar contable" value={f.id_aux} onChange={(v) => setF({ ...f, id_aux: v })} options={auxs.map((a: any) => ({ value: a.id_aux, label: a.auxiliar }))} />
          <TextField label="Buscar (código, descripción, responsable)" value={f.texto} onChange={(v) => setF({ ...f, texto: v })} />
        </div>
        <div style={{ marginTop: 8 }}><button disabled={busy} onClick={cargar}>Buscar</button></div>
      </Card>
      <Card title={`Activos elegibles: ${filas.length}`} right={puede('af') && <button className="primary" disabled={!sel.size} onClick={() => setModal(true)}>Crear lote con {sel.size} seleccionado(s)</button>}>
        <DataTable maxHeight="55vh" rows={filas} empty="No hay activos que cumplan las tres condiciones (valor Bs 1 + estado Bueno/Regular/Malo + operativo)."
          cols={[
            { key: 's', header: '', render: (a) => <input type="checkbox" checked={sel.has(a.codigo)} onChange={(e) => { const n = new Set(sel); e.target.checked ? n.add(a.codigo) : n.delete(a.codigo); setSel(n); }} />, width: 30 },
            { key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' }, { key: 'auxiliar', header: 'Auxiliar' },
            { key: 'estado', header: 'Estado', badge: true }, { key: 'funcionario', header: 'Responsable' }, { key: 'valor_neto', header: 'Valor neto', money: true },
            { key: 'a', header: '', render: (a) => puede('af') && <button onClick={() => noOperativo(a)}>No operativo</button> },
          ]}
          foot={filas.length ? <tr><td><input type="checkbox" checked={todos} onChange={(e) => setSel(e.target.checked ? new Set(filas.map((x) => x.codigo)) : new Set())} title="Seleccionar todos" /></td><td colSpan={7} className="muted">Seleccionar todos</td></tr> : undefined} />
      </Card>
      {modal && (
        <Modal title="Nuevo lote de revalúo" onClose={() => setModal(false)} footer={<><button onClick={() => setModal(false)}>Cancelar</button><button className="primary" disabled={busy} onClick={crear}>Crear lote</button></>}>
          <div className="grid">
            <TextField className="span2" label="Descripción del lote" value={d.descripcion} onChange={(v) => setD({ ...d, descripcion: v })} placeholder="Revalúo técnico de mobiliario de oficina" />
            <TextField label="Perito / responsable de la tasación" req value={d.perito} onChange={(v) => setD({ ...d, perito: v })} />
            <TextField label="Cargo del perito" value={d.perito_cargo} onChange={(v) => setD({ ...d, perito_cargo: v })} />
            <AreaField className="span2" rows={3} label="Comisión calificadora (una persona por línea: Nombre | Cargo)" value={d.comision} onChange={(v) => setD({ ...d, comision: v })} />
          </div>
        </Modal>
      )}
    </>
  );
}

function Lotes({ abrir }: { abrir: (id: number) => void }) {
  const l = useLoad<any[]>(() => get('/af/revaluo/lotes'));
  return (
    <Card title="Lotes de revalúo">
      <DataTable rows={l.data ?? []} onRow={(r) => abrir(r.id)} empty="Aún no hay lotes. Cree uno desde la bandeja de selección."
        cols={[{ key: 'nro', header: 'Lote' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'descripcion', header: 'Descripción' }, { key: 'estado', header: 'Estado', render: (r) => <span className={'badge ' + (r.estado === 'APROBADO' ? 'b-ok' : 'b-warn')}>{r.estado}</span> }, { key: 'activos', header: 'Activos', num: true }, { key: 'vtr_total', header: 'Valor revaluado', money: true }, { key: 'incremento_total', header: 'Incremento', money: true }, { key: 'perito', header: 'Perito' }]} />
      <p className="muted">Haga clic en un lote para abrir sus hojas de tasación.</p>
    </Card>
  );
}

function Lote({ id, volver }: { id: number; volver: () => void }) {
  const { puede } = useAuth();
  const ui = useUi();
  const [run, busy] = useAction();
  const lote = useLoad<any>(() => get(`/af/revaluo/lotes/${id}`), [id]);
  const l = lote.data;
  const [sel, setSel] = useState<number | null>(null);
  const [cab, setCab] = useState({ descripcion: '', perito: '', perito_cargo: '', comision: '' });
  useEffect(() => { if (l) setCab({ descripcion: l.descripcion || '', perito: l.perito || '', perito_cargo: l.perito_cargo || '', comision: l.comision || '' }); }, [l?.id, l?.estado]);
  if (!l) return <p>Cargando…</p>;
  const abierto = l.estado === 'BORRADOR' && puede('af');
  const item = l.items.find((i: any) => i.id === sel);
  const guardarCab = () => run(async () => { await put(`/af/revaluo/lotes/${id}`, cab); lote.reload(); }, 'Datos del lote guardados.');
  const aprobar = async () => {
    const res = await ui.prompt('Número de resolución administrativa que aprueba el revalúo (opcional):');
    if (res === null) return;
    if (!(await ui.confirm(`Se actualizará el valor de ${l.totales.activos} activo(s) a Bs ${fmt2(l.totales.vtr)} y se registrará un incremento de Bs ${fmt2(l.totales.incremento)} en "Reserva por Revalúos Técnicos". Esta acción no se puede deshacer. ¿Aprobar?`))) return;
    run(async () => { await post(`/af/revaluo/lotes/${id}/aprobar`, { resolucion: res }); lote.reload(); }, 'Revalúo aprobado y aplicado a los activos.');
  };
  const eliminar = async () => { if (await ui.confirm('¿Eliminar este lote y sus cotizaciones?')) run(async () => { await del(`/af/revaluo/lotes/${id}`); volver(); }); };
  return (
    <>
      <PageHead title={`Lote ${l.nro}`} sub={`${l.descripcion || ''} · ${l.estado === 'APROBADO' ? 'Aprobado el ' + fmtDate(l.fecha_aprob) + (l.resolucion ? ' · Res. ' + l.resolucion : '') : 'En elaboración (borrador)'}`}>
        <button onClick={volver}>← Volver</button>
      </PageHead>
      <div className="kpis">
        <Kpi mod="af" label="Activos" value={l.totales.activos} />
        <Kpi mod="af" label="Hojas completas" value={`${l.totales.completos} / ${l.totales.activos}`} tone={l.totales.completos < l.totales.activos ? 'warn' : undefined} />
        <Kpi mod="af" label="Valor anterior (Bs)" value={fmt2(l.totales.valor_anterior)} />
        <Kpi mod="af" label="Valor revaluado (Bs)" value={fmt2(l.totales.vtr)} />
        <Kpi mod="af" label="Incremento a Reserva (Bs)" value={fmt2(l.totales.incremento)} />
      </div>
      <Card title="Perito y comisión calificadora" right={abierto && <button disabled={busy} onClick={guardarCab}>Guardar</button>}>
        <div className="grid">
          <TextField className="span2" label="Descripción" value={cab.descripcion} onChange={(v) => setCab({ ...cab, descripcion: v })} disabled={!abierto} />
          <TextField label="Perito / responsable de la tasación" value={cab.perito} onChange={(v) => setCab({ ...cab, perito: v })} disabled={!abierto} />
          <TextField label="Cargo" value={cab.perito_cargo} onChange={(v) => setCab({ ...cab, perito_cargo: v })} disabled={!abierto} />
          <AreaField className="span2" rows={3} label="Comisión (Nombre | Cargo, una por línea)" value={cab.comision} onChange={(v) => setCab({ ...cab, comision: v })} disabled={!abierto} />
        </div>
      </Card>
      <Card title="Hojas de tasación (seleccione un activo para tasarlo)">
        <DataTable rows={l.items} selected={(r) => r.id === sel} onRow={(r) => setSel(r.id === sel ? null : r.id)} empty="El lote no tiene activos."
          cols={[{ key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' }, { key: 'estado_fisico', header: 'Estado', badge: true }, { key: 'cot', header: 'Cotiz.', ctr: true, render: (r) => r.cotizaciones.length }, { key: 'vn_base', header: 'VN base', money: true }, { key: 'factor', header: 'Factor', ctr: true, render: (r) => (r.factor ?? '') }, { key: 'vtr', header: 'VTR', money: true }, { key: 'incremento', header: 'Incremento', money: true }, { key: 'ok', header: 'Hoja', ctr: true, render: (r) => (r.completo ? '✔ completa' : '⚠ incompleta') }]} />
      </Card>
      {item && <Hoja key={item.id} item={item} abierto={abierto} recargar={lote.reload} cerrar={() => setSel(null)} />}
      <Card title="Consolidación y aprobación — vista preliminar de incrementos patrimoniales">
        <DataTable rows={l.por_cuenta} empty="Sin datos" cols={[{ key: 'cuenta', header: 'Cuenta contable (Débito: Activo Fijo)' }, { key: 'activos', header: 'Activos', num: true }, { key: 'incremento', header: 'Incremento (VTR − Bs 1)', money: true }]}
          foot={<tr><td><b>Crédito: {l.reserva}</b></td><td className="num"><b>{l.totales.activos}</b></td><td className="num"><b>{fmt2(l.totales.incremento)}</b></td></tr>} />
        <div className="row" style={{ marginTop: 10, gap: 8, flexWrap: 'wrap' }}>
          <button onClick={() => run(() => bajarArchivo(`/af/revaluo/lotes/${id}/informe`, `Informe_Tecnico_Revaluo_${l.nro.replace('/', '-')}.docx`))}>⬇ Informe Técnico de Revalúo (Word)</button>
          <button onClick={() => run(() => bajarArchivo(`/af/revaluo/lotes/${id}/anexos`, `Anexos_Revaluo_${l.nro.replace('/', '-')}.docx`))}>⬇ Cuadros de soporte y anexos (Word)</button>
          {abierto && <button className="primary" disabled={busy || l.totales.completos < l.totales.activos || !l.totales.activos} onClick={aprobar}>Aprobar y aplicar el revalúo</button>}
          {abierto && <button onClick={eliminar}>Eliminar lote</button>}
        </div>
        {abierto && l.totales.completos < l.totales.activos && <p className="warn">⚠ Para aprobar, todas las hojas deben estar completas (cotización, factor, vida útil y justificación).</p>}
      </Card>
    </>
  );
}

const vacioCot = () => ({ proveedor: '', nit: '', fecha: hoy(), nro_proforma: '', referencia: '', valor: null as number | null });

function Hoja({ item, abierto, recargar, cerrar }: { item: any; abierto: boolean; recargar: () => void; cerrar: () => void }) {
  const ui = useUi();
  const [run, busy] = useAction();
  const [h, setH] = useState({ metodo: item.metodo, factor: item.factor as number | null, vida_anios: item.vida_anios, vida_meses: item.vida_meses, justificacion: item.justificacion || '' });
  const [c, setC] = useState(vacioCot());
  const fotos = [1, 2, 3, 4].map((n) => item['foto' + n]).filter(Boolean);
  const r = item.rango;
  const previo = useMemo(() => {
    const v = item.cotizaciones.map((x: any) => x.valor).sort((a: number, b: number) => a - b);
    if (!v.length || h.factor == null) return { vn: 0, vtr: 0 };
    const vn = h.metodo === 'MEDIANA' ? (v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : v.reduce((a: number, b: number) => a + b, 0) / v.length;
    return { vn, vtr: Math.max(1, vn * h.factor) };
  }, [item.cotizaciones, h.metodo, h.factor]);
  const guardar = () => run(async () => { await put(`/af/revaluo/items/${item.id}`, h); recargar(); }, 'Hoja de tasación guardada.');
  const addCot = () => run(async () => { await post(`/af/revaluo/items/${item.id}/cotizaciones`, c); setC(vacioCot()); recargar(); });
  const quitarCot = async (x: any) => { if (await ui.confirm('¿Quitar esta cotización?')) run(async () => { await del(`/af/revaluo/cotizaciones/${x.id}`); recargar(); }); };
  const soporte = (x: any, file?: File) => file && run(async () => { await subirArchivoPut(`/af/revaluo/cotizaciones/${x.id}/soporte`, file); recargar(); }, 'Soporte adjuntado.');
  const quitarActivo = async () => { if (await ui.confirm(`¿Retirar ${item.codigo} del lote?`)) run(async () => { await del(`/af/revaluo/items/${item.id}`); cerrar(); recargar(); }); };
  return (
    <Card title={`Hoja de tasación — ${item.codigo}`} right={<button onClick={cerrar}>Cerrar hoja</button>}>
      <div className="grid c2">
        <div>
          <p><b>{item.descripcion}</b><br /><span className="muted">{item.auxiliar} · {item.cuenta}</span></p>
          <p>Responsable: {item.funcionario || '—'} · Estado: <Badge v={item.estado_fisico} /> · Operativo: {item.operativo === 'NO' ? 'No' : 'Sí'}<br />Marca/modelo/serie: {[item.marca, item.modelo, item.serie].filter(Boolean).join(' / ') || '—'}<br />Valor anterior: Bs {fmt2(item.valor_anterior)}</p>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
            {fotos.length ? fotos.map((f: string) => <a key={f} href={urlConToken(`/af/fotos/${f}`)} target="_blank" rel="noreferrer"><img alt="Foto del activo" style={{ height: 96, borderRadius: 6, border: '1px solid var(--line)' }} src={urlConToken(`/af/fotos/${f}`)} /></a>) : <span className="muted">Sin fotografías: súbalas en Fichas técnicas (se recomienda para justificar la inspección).</span>}
          </div>
        </div>
        <div>
          <div className="grid">
            <SelectField label="Valor base de comparación" blank={false} value={h.metodo} onChange={(v) => setH({ ...h, metodo: v })} options={[{ value: 'PROMEDIO', label: 'Promedio simple' }, { value: 'MEDIANA', label: 'Mediana' }]} disabled={!abierto} />
            <NumField label={`Factor de conservación (${r ? r.min.toFixed(2) + ' – ' + r.max.toFixed(2) : ''})`} step="0.01" value={h.factor} onChange={(v) => setH({ ...h, factor: v })} disabled={!abierto} />
            <NumField label="Vida útil residual (años)" step="1" value={h.vida_anios} onChange={(v) => setH({ ...h, vida_anios: v ?? 0 })} disabled={!abierto} />
            <NumField label="Meses (0-11)" step="1" value={h.vida_meses} onChange={(v) => setH({ ...h, vida_meses: v ?? 0 })} disabled={!abierto} />
          </div>
          <p style={{ marginTop: 8 }}>VN base: <b>Bs {fmt2(previo.vn)}</b> · VTR = VN × factor: <b>Bs {fmt2(previo.vtr)}</b> · Incremento: <b>Bs {fmt2(previo.vtr ? previo.vtr - item.valor_anterior : 0)}</b> <span className="muted">(guarde para que quede registrado)</span></p>
        </div>
      </div>
      <AreaField rows={3} label="Justificación técnica del perito (inspección, fotos, estado de uso)" value={h.justificacion} onChange={(v) => setH({ ...h, justificacion: v })} disabled={!abierto} />
      {abierto && <div className="row" style={{ marginTop: 8, gap: 8 }}><button className="primary" disabled={busy} onClick={guardar}>Guardar hoja</button><button onClick={quitarActivo}>Retirar del lote</button></div>}
      <h3 style={{ marginTop: 14 }}>Cotizaciones de mercado (Valor a Nuevo) — de 1 a 3</h3>
      <DataTable rows={item.cotizaciones} empty="Sin cotizaciones: registre al menos una." cols={[
        { key: 'proveedor', header: 'Proveedor / fuente' }, { key: 'nit', header: 'NIT' }, { key: 'fecha', header: 'Fecha', date: true }, { key: 'nro_proforma', header: 'Proforma' },
        { key: 'referencia', header: 'Referencia / enlace', render: (x: any) => (/^https?:\/\//.test(x.referencia || '') ? <a href={x.referencia} target="_blank" rel="noreferrer">enlace</a> : x.referencia) }, { key: 'valor', header: 'VN (Bs)', money: true },
        { key: 'sop', header: 'Soporte', render: (x: any) => <>{x.soporte && <a href={urlConToken(`/af/revaluo/soporte/${x.soporte}`)} target="_blank" rel="noreferrer">ver</a>}{abierto && <label style={{ marginLeft: 6, cursor: 'pointer' }}>📎<input type="file" hidden accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => soporte(x, e.target.files?.[0])} /></label>}</> },
        { key: 'q', header: '', render: (x: any) => abierto && <button onClick={() => quitarCot(x)}>Quitar</button> },
      ]} />
      {abierto && item.cotizaciones.length < 3 && (
        <div className="grid" style={{ marginTop: 8 }}>
          <TextField label="Proveedor / fuente" value={c.proveedor} onChange={(v) => setC({ ...c, proveedor: v })} />
          <TextField label="NIT" value={c.nit} onChange={(v) => setC({ ...c, nit: v })} />
          <DateField label="Fecha" value={c.fecha} onChange={(v) => setC({ ...c, fecha: v })} />
          <TextField label="N° proforma" value={c.nro_proforma} onChange={(v) => setC({ ...c, nro_proforma: v })} />
          <TextField label="Enlace (link) o referencia del bien similar" value={c.referencia} onChange={(v) => setC({ ...c, referencia: v })} />
          <NumField label="Valor a nuevo VN (Bs)" value={c.valor} onChange={(v) => setC({ ...c, valor: v })} />
          <div style={{ alignSelf: 'end' }}><button className="primary" disabled={busy} onClick={addCot}>Agregar cotización</button></div>
        </div>
      )}
    </Card>
  );
}

async function subirArchivoPut(path: string, file: File) {
  const { getToken } = await import('../../api');
  const res = await fetch('/api' + path, { method: 'PUT', headers: { authorization: `Bearer ${getToken()}`, 'content-type': 'application/octet-stream' }, body: file });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(d.error || `Error ${res.status}`);
  return d;
}
