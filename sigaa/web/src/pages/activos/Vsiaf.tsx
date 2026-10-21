import { useEffect, useState } from 'react';
import { ApiError, fmtDate, get, getToken, post, put } from '../../api';
import { useAuth } from '../../auth';
import { Badge, Card, DataTable, PageHead, SelectField, Tabs, TextField, useAction, useLoad, useUi } from '../../ui';

type Paso = 'destino' | 'seleccion' | 'equiv' | 'validar' | 'informe';
const TIPOS: Record<string, string> = { grupo: 'Grupo contable', estado: 'Estado del bien', org_fin: 'Organismo financiador', unidad: 'Unidad administrativa', motivo_baja: 'Motivo de baja', oficina: 'Oficina', resp_nombre: 'Responsable (nombre)', resp_cargo: 'Responsable (cargo)', auxiliar: 'Auxiliar' };
const AVISO_FINAL = 'Después de importar: abra el VSIAF → Administradores → Re-indexar, verifique con el Reporte 6 y apruebe los activos ELABORADOS.';

/** Descarga un Excel generado por POST. */
async function bajarXlsx(path: string, body: unknown, nombre: string) {
  const res = await fetch('/api' + path, { method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${getToken()}` }, body: JSON.stringify(body) });
  if (!res.ok) { const d = await res.json().catch(() => ({})); throw new ApiError(d.error || `Error ${res.status}`, res.status); }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(await res.blob()); a.download = nombre; a.click();
}

export default function AfVsiaf() {
  const { puede } = useAuth();
  const ui = useUi();
  const [run, busy] = useAction();
  const escribe = puede('af');
  const [paso, setPaso] = useState<Paso>('destino');
  const conf = useLoad<any>(() => get('/af/vsiaf/config'));
  const [c, setC] = useState({ ruta: '', unidad: '', usuario: 'admin' });
  const [dest, setDest] = useState<any>();
  const [filtro, setFiltro] = useState({ desde: '', hasta: '', texto: '', estado: 'PENDIENTES' });
  const [lista, setLista] = useState<any[]>([]);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [opc, setOpc] = useState({ estadoRegistro: 'ELABORADO', incluirAlmacen: true, movimientos: true, soloValidas: false });
  const [pend, setPend] = useState<any>();
  const [val, setVal] = useState<any>();
  const [fin, setFin] = useState<any>();
  const [eq, setEq] = useState<Record<string, string>>({});
  const lotes = useLoad<any[]>(() => get('/af/vsiaf/lotes'), [fin]);

  useEffect(() => { if (conf.data) setC({ ruta: conf.data.ruta, unidad: conf.data.unidad, usuario: conf.data.usuario }); }, [conf.data]);

  const params = () => ({ ruta: c.ruta || undefined, unidad: c.unidad || undefined, usuarioVsiaf: c.usuario || undefined, codigos: sel.size ? [...sel] : undefined, filtros: sel.size ? undefined : { desde: filtro.desde || undefined, hasta: filtro.hasta || undefined, texto: filtro.texto || undefined }, ...opc });
  const nSel = sel.size;

  const probar = () => run(async () => {
    await put('/af/vsiaf/config', c);
    const d = await get('/af/vsiaf/destino', { ruta: c.ruta });
    setDest(d);
    if (d.encontrada) ui.ok('Instalación del VSIAF encontrada.'); else ui.error(d.mensaje || 'No se encontró el VSIAF.');
  });
  const buscar = () => run(async () => {
    const r = await get('/af/vsiaf/seleccion', filtro);
    setLista(r); setSel(new Set());
    if (!r.length) ui.error('No hay activos con ese criterio.');
  });
  const revisarEquiv = () => run(async () => {
    const r = await post('/af/vsiaf/pendientes', params());
    setPend(r);
    setEq(Object.fromEntries(r.faltantes.map((f: any) => [`${f.tipo}|${f.clave}`, f.sugerencia ?? ''])));
  });
  const guardarEq = () => run(async () => {
    const items = pend.faltantes.map((f: any) => ({ tipo: f.tipo, clave: f.clave, valor: eq[`${f.tipo}|${f.clave}`] ?? '' })).filter((i: any) => i.valor);
    if (!items.length) { ui.error('Complete al menos una equivalencia.'); return; }
    await put('/af/vsiaf/equivalencias', { items });
    ui.ok(`${items.length} equivalencia(s) guardada(s).`);
    setPend(await post('/af/vsiaf/pendientes', params()));
  });
  const validar = () => run(async () => { setVal(await post('/af/vsiaf/validar', params())); setFin(undefined); });
  const importar = async () => {
    if (!(await ui.confirm(`Se escribirá en la base de datos del VSIAF (${val.resumen.activos} alta(s), ${val.resumen.transferencias} transferencia(s), ${val.resumen.bajas} baja(s)). Se hará un respaldo antes. ¿Continuar?\n\nRecuerde: el VSIAF debe estar cerrado en todas las PC.`))) return;
    run(async () => { const r = await post('/af/vsiaf/importar', { ...params(), confirmar: true }); setFin(r); setVal(undefined); setPaso('informe'); ui.ok(`Lote ${r.lote} importado.`); });
  };
  const exportar = (path: string, body: unknown, nombre: string) => run(() => bajarXlsx(path, body, nombre));

  const faltaDest = !dest?.encontrada;
  return (
    <>
      <PageHead title="Enviar al VSIAF" sub="Importa los activos de SIGAA al VSIAF 2.0 (base FoxPro) con validación, respaldo y reversión." />
      <Tabs value={paso} onChange={setPaso} items={[{ id: 'destino', label: '1. Destino' }, { id: 'seleccion', label: `2. Selección${nSel ? ` (${nSel})` : ''}` }, { id: 'equiv', label: '3. Equivalencias' }, { id: 'validar', label: '4. Validar' }, { id: 'informe', label: '5. Importar e informe' }]} />

      {paso === 'destino' && (
        <Card title="Instalación del VSIAF">
          <div className="form-grid">
            <TextField className="span2" label="Carpeta del VSIAF (contiene vsiaf.exe y dbfs)" value={c.ruta} onChange={(v) => setC({ ...c, ruta: v })} placeholder="C:\vsiaf" disabled={!escribe} />
            <TextField label="Unidad administrativa (máx. 5)" value={c.unidad} onChange={(v) => setC({ ...c, unidad: v.slice(0, 5) })} disabled={!escribe} />
            <TextField label="Usuario VSIAF (máx. 8)" value={c.usuario} onChange={(v) => setC({ ...c, usuario: v.slice(0, 8) })} disabled={!escribe} />
          </div>
          <div style={{ marginTop: 10 }}><button className="primary" disabled={busy || !escribe} onClick={probar}>Guardar y comprobar</button></div>
          {dest?.encontrada && (
            <div style={{ marginTop: 12 }}>
              <p><b>{dest.entidadNombre || dest.entidad}</b> · {dest.ruta}</p>
              {(dest.avisos ?? []).map((a: string) => <p key={a} className="warn">⚠ {a}</p>)}
              <DataTable rows={dest.unidades ?? []} cols={[{ key: 'codigo', header: 'Unidad' }, { key: 'descripcion', header: 'Descripción' }]} empty="Sin unidades." />
            </div>
          )}
          {dest && !dest.encontrada && <p className="warn">⚠ {dest.mensaje}</p>}
        </Card>
      )}

      {paso === 'seleccion' && (
        <Card title="Activos a enviar" right={<span className="muted">{nSel ? `${nSel} marcados` : 'Sin marcar = todos los del filtro'}</span>}>
          <div className="form-grid">
            <TextField label="Ingresados desde (aaaa-mm-dd)" value={filtro.desde} onChange={(v) => setFiltro({ ...filtro, desde: v })} />
            <TextField label="Hasta (aaaa-mm-dd)" value={filtro.hasta} onChange={(v) => setFiltro({ ...filtro, hasta: v })} />
            <TextField label="Código o descripción" value={filtro.texto} onChange={(v) => setFiltro({ ...filtro, texto: v })} />
            <SelectField blank={false} label="Mostrar" value={filtro.estado} onChange={(v) => setFiltro({ ...filtro, estado: v })} options={[{ value: 'PENDIENTES', label: 'Pendientes de envío' }, { value: 'ENVIADOS', label: 'Ya enviados' }, { value: 'TODOS', label: 'Todos' }]} />
            <SelectField blank={false} label="Estado de las altas en el VSIAF" value={opc.estadoRegistro} onChange={(v) => setOpc({ ...opc, estadoRegistro: v })} options={[{ value: 'ELABORADO', label: 'ELABORADO (recomendado: se aprueba en el VSIAF)' }, { value: 'APROBADO', label: 'APROBADO' }]} />
            <label className="check"><input type="checkbox" checked={opc.incluirAlmacen} onChange={(e) => setOpc({ ...opc, incluirAlmacen: e.target.checked })} /> Incluir activos en almacén (oficina «ALMACÉN»)</label>
            <label className="check"><input type="checkbox" checked={opc.movimientos} onChange={(e) => setOpc({ ...opc, movimientos: e.target.checked })} /> Enviar también transferencias y bajas</label>
          </div>
          <div className="row" style={{ margin: '10px 0' }}>
            <button className="primary" disabled={busy} onClick={buscar}>Buscar</button>
            {lista.length > 0 && <><button className="sm" onClick={() => setSel(new Set(lista.map((a) => a.codigo)))}>Marcar todo</button><button className="sm" onClick={() => setSel(new Set())}>Desmarcar</button></>}
          </div>
          <DataTable maxHeight="45vh" rows={lista} onRow={(r) => setSel((s) => { const n = new Set(s); n.has(r.codigo) ? n.delete(r.codigo) : n.add(r.codigo); return n; })}
            cols={[{ key: 's', header: '', render: (r) => <input type="checkbox" readOnly checked={sel.has(r.codigo)} /> }, { key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' }, { key: 'cuenta', header: 'Cuenta' }, { key: 'valor', header: 'Valor', money: true }, { key: 'fecha_ingreso', header: 'Ingreso', date: true }, { key: 'situacion', header: 'Situación', badge: true }, { key: 'lote_envio', header: 'Enviado', render: (r) => (r.lote_envio ? `Lote ${r.lote_envio}` : '—') }]}
            empty="Pulse «Buscar»." />
        </Card>
      )}

      {paso === 'equiv' && (
        <Card title="Equivalencias SIGAA → VSIAF" right={<button className="sm" onClick={revisarEquiv} disabled={busy}>Revisar lo que falta</button>}>
          <p className="muted">El VSIAF usa códigos propios (grupo contable, organismo financiador, oficinas…). Indique una sola vez a qué equivale cada valor de SIGAA; queda guardado.</p>
          {pend && !pend.faltantes.length && <p className="ok-txt">✔ No falta ninguna equivalencia para este envío.</p>}
          {pend?.faltantes.length > 0 && (
            <>
              <DataTable rows={pend.faltantes} cols={[{ key: 'tipo', header: 'Concepto', render: (r) => TIPOS[r.tipo] ?? r.tipo }, { key: 'clave', header: 'Valor en SIGAA' }, { key: 'detalle', header: 'Detalle' },
                { key: 'v', header: 'Equivale en el VSIAF a…', render: (r) => <input value={eq[`${r.tipo}|${r.clave}`] ?? ''} disabled={!escribe} onChange={(e) => setEq({ ...eq, [`${r.tipo}|${r.clave}`]: e.target.value })} /> }]} />
              {escribe && <div style={{ marginTop: 10 }}><button className="ok" disabled={busy} onClick={guardarEq}>Guardar equivalencias</button></div>}
            </>
          )}
        </Card>
      )}

      {paso === 'validar' && (
        <Card title="Vista previa (no escribe nada en el VSIAF)">
          <div className="row"><button className="primary" disabled={busy || !escribe} onClick={validar}>Validar y calcular</button>
            {val && <><button className="sm" disabled={busy} onClick={() => exportar('/af/vsiaf/exportar/informe', params(), 'informe_validacion.xlsx')}>Informe (Excel)</button></>}
            <button className="sm" disabled={busy || !escribe} onClick={() => exportar('/af/vsiaf/exportar/libro', params(), 'SIGAA_para_VSIAF.xlsx')} title="Libro para el aplicativo «Importador Excel → VSIAF»">Exportar libro Excel</button></div>
          {val && (
            <div style={{ marginTop: 12 }}>
              <p><b>{val.resumen.activos}</b> alta(s) · <b>{val.resumen.transferencias}</b> transferencia(s) · <b>{val.resumen.bajas}</b> baja(s) · oficinas nuevas {val.resumen.oficinas} · responsables nuevos {val.resumen.responsables} · auxiliares nuevos {val.resumen.auxiliares}</p>
              <p>{val.sinErrores ? <Badge v="OK" /> : <span className="badge bad">{val.errores} error(es)</span>} {val.avisos > 0 && <span className="badge warn">{val.avisos} aviso(s)</span>}</p>
              {val.faltantes.length > 0 && <p className="warn">⚠ Faltan {val.faltantes.length} equivalencia(s): complételas en el paso 3.</p>}
              {val.omitidos.length > 0 && <details><summary>{val.omitidos.length} activo(s) omitido(s)</summary><ul>{val.omitidos.map((o: any) => <li key={o.codigo}>{o.codigo}: {o.motivo}</li>)}</ul></details>}
              {val.incidencias.length > 0 && <DataTable maxHeight="30vh" rows={val.incidencias} cols={[{ key: 'nivel', header: 'Nivel', badge: true }, { key: 'tipo', header: 'Tipo' }, { key: 'codigo', header: 'Código' }, { key: 'etiqueta', header: 'Campo' }, { key: 'mensaje', header: 'Mensaje' }]} />}
              <h3 style={{ marginTop: 16 }}>Cálculo por grupo contable (Bs, a hoy)</h3>
              <DataTable rows={val.totalesPorGrupo} empty="Sin altas." cols={[{ key: 'grupo', header: 'Grupo' }, { key: 'cantidad', header: 'Cant.', num: true }, { key: 'costo_historico', header: 'Costo histórico', money: true }, { key: 'costo_total_actualizado', header: 'Costo actualizado', money: true }, { key: 'dep_acumulada', header: 'Dep. acumulada', money: true }, { key: 'valor_neto', header: 'Valor neto', money: true }]} />
              <label className="check" style={{ marginTop: 10 }}><input type="checkbox" checked={opc.soloValidas} onChange={(e) => setOpc({ ...opc, soloValidas: e.target.checked })} /> Importar solo las filas válidas (si hay errores)</label>
              <p className="warn">⚠ {AVISO_FINAL}</p>
              <button className="danger" disabled={busy || !escribe || (!val.sinErrores && !opc.soloValidas) || faltaDest && !c.ruta} onClick={importar}>Importar al VSIAF</button>
            </div>
          )}
        </Card>
      )}

      {paso === 'informe' && (
        <>
          {fin && (
            <Card title={`Importación realizada — lote ${fin.lote}`}>
              <p className="ok-txt">✔ Se importó correctamente. Respaldo: <code>{fin.respaldo ?? '—'}</code></p>
              <p className="warn">⚠ {fin.pasoFinal ?? AVISO_FINAL}</p>
              <p>Activos {fin.conteos.ACTIVOS ?? 0} · Transferencias {fin.conteos.TRANSFERENCIAS ?? 0} · Bajas {fin.conteos.BAJAS ?? 0}</p>
              <button className="sm" disabled={busy} onClick={() => exportar('/af/vsiaf/exportar/informe-importacion', { validacion: fin.validacion, lote: fin.lote, respaldo: fin.respaldo }, `informe_importacion_${fin.lote}.xlsx`)}>Informe (Excel)</button>
            </Card>
          )}
          <Card title="Historial de envíos">
            <DataTable rows={lotes.data ?? []} empty="Aún no se ha enviado nada." cols={[{ key: 'id', header: 'Lote' }, { key: 'fecha', header: 'Fecha', render: (r) => fmtDate(r.fecha) }, { key: 'usuario', header: 'Usuario' }, { key: 'unidad', header: 'Unidad' }, { key: 'estado_registro', header: 'Altas', badge: true }, { key: 'resultado', header: 'Resultado', badge: true },
              { key: 'r', header: 'Resumen', render: (r) => { try { const x = JSON.parse(r.resumen || '{}').resumen; return x ? `${x.activos} act · ${x.transferencias} transf · ${x.bajas} bajas` : ''; } catch { return ''; } } }, { key: 'respaldo', header: 'Respaldo' }]} />
          </Card>
        </>
      )}
    </>
  );
}
