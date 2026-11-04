import { useEffect, useRef, useState } from 'react';
import { del, get, post, put, subirImagenPut, urlConToken, fmtDate } from '../api';
import { useAuth } from '../auth';
import { Card, DataTable, Field, Modal, PageHead, SelectField, Tabs, TextField, useAction, useLoad, Badge } from '../ui';

import { ROLES_INFO, rolInfo } from '../roles';

const Chip = ({ r }: { r: string }) => <span className="rol-chip sm" style={{ background: rolInfo(r)?.color }}>{rolInfo(r)?.nombre ?? r}</span>;

/** Logo de la entidad: se examina un archivo de la PC y se inserta en todos los reportes y documentos. */
function LogoCampo({ valor, onCambio }: { valor: string; onCambio: () => void }) {
  const { esAdmin } = useAuth();
  const [run, busy] = useAction();
  const [ver, setVer] = useState(Date.now());
  const ref = useRef<HTMLInputElement>(null);
  const [hay, setHay] = useState(!!valor);
  useEffect(() => setHay(!!valor), [valor]);
  return (
    <div className="span2">
      <div className="muted" style={{ fontSize: 12, fontWeight: 600 }}>Logo de la entidad</div>
      <div className="row" style={{ alignItems: 'center', gap: 12 }}>
        <div style={{ width: 150, height: 80, border: '1px dashed var(--line, #b9c2cf)', borderRadius: 8, display: 'grid', placeItems: 'center', background: '#fff', overflow: 'hidden' }}>
          {hay ? <img key={ver} src={urlConToken('/config/logo', { v: ver })} alt="Logo" style={{ maxWidth: '100%', maxHeight: '100%' }} onError={() => setHay(false)} /> : <span className="muted">Sin logo</span>}
        </div>
        {esAdmin && (
          <>
            <button disabled={busy} onClick={() => ref.current?.click()}>Examinar… (JPG o PNG)</button>
            <input ref={ref} type="file" accept="image/png,image/jpeg" hidden onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) run(async () => { await subirImagenPut('/config/logo', f); setVer(Date.now()); setHay(true); onCambio(); }, 'Logo cargado: aparecerá en todos los reportes.'); }} />
            {hay && <button className="danger" disabled={busy} onClick={() => run(async () => { await del('/config/logo'); setHay(false); onCambio(); }, 'Logo quitado.')}>Quitar</button>}
          </>
        )}
      </div>
      <div className="muted" style={{ fontSize: 12 }}>Elija la imagen en su computadora (hasta 3 MB). Se inserta en el encabezado de todos los reportes y documentos PDF, en los reportes de Excel y en las etiquetas.</div>
    </div>
  );
}

function Config() {
  const { data, reload } = useLoad<any[]>(() => get('/config'));
  const { esAdmin } = useAuth();
  const [cambios, setCambios] = useState<Record<string, string>>({});
  const [run, busy] = useAction();
  const mods: Record<string, string> = { core: 'Entidad y firmantes', alm: 'Almacenes', af: 'Activos fijos', com: 'Combustible' };
  return (
    <>
      {Object.entries(mods).map(([m, titulo]) => (
        <Card key={m} title={titulo}>
          <div className="grid c2">
            {(data ?? []).filter((c) => c.modulo === m).map((c) => c.clave === 'Logo' ? (
              <LogoCampo key={c.clave} valor={c.valor ?? ''} onCambio={reload} />
            ) : c.clave === 'VsiafSoloAdmin' ? (
              <label key={c.clave} className="check span2"><input type="checkbox" disabled={!esAdmin} checked={(cambios[c.clave] ?? c.valor ?? 'NO').toUpperCase() === 'SI'} onChange={(e) => setCambios({ ...cambios, [c.clave]: e.target.checked ? 'SI' : 'NO' })} /> <span><b>Reservar al administrador el envío e importación con el VSIAF.</b> Si se marca, el encargado de Activos Fijos ya no ve ni usa «Enviar al VSIAF» ni «Importar desde el VSIAF».</span></label>
            ) : (
              <TextField key={c.clave} label={c.clave} hint={c.descripcion} disabled={!esAdmin} value={cambios[c.clave] ?? c.valor ?? ''} onChange={(v) => setCambios({ ...cambios, [c.clave]: v })} />
            ))}
          </div>
        </Card>
      ))}
      {esAdmin && <button className="primary" disabled={busy || !Object.keys(cambios).length} onClick={() => run(async () => { await put('/config', cambios); setCambios({}); reload(); }, 'Configuración guardada.')}>Guardar configuración</button>}
    </>
  );
}

function Usuarios() {
  const { data, reload } = useLoad<any[]>(() => get('/usuarios'));
  const [m, setM] = useState<any>(null);
  const [run, busy] = useAction();
  return (
    <Card title="Usuarios del sistema" right={<button className="primary" onClick={() => setM({ nuevo: true, roles: ['CONSULTA'] })}>+ Nuevo usuario</button>}>
      <DataTable rows={data ?? []} onRow={(r) => setM({ ...r, roles: String(r.roles).split(',') })} cols={[{ key: 'usuario', header: 'Usuario' }, { key: 'nombre', header: 'Nombre' }, { key: 'roles', header: 'Roles', render: (r: any) => <span className="row" style={{ gap: 4 }}>{String(r.roles).split(',').map((x) => <Chip key={x} r={x} />)}</span> }, { key: 'estado', header: 'Estado', badge: true }, { key: 'ultimo_acceso', header: 'Último acceso' }]} />
      <div className="rol-leyenda" style={{ margin: '10px 0 4px' }}>{ROLES_INFO.map((r) => <span key={r.codigo} className="rol-chip" style={{ background: r.color }} title={r.descripcion}>{r.nombre}</span>)}</div>
      <small className="muted">Cada rol tiene su color. Un usuario puede tener varios roles; Consulta solo ve y descarga.</small>
      {m && (
        <Modal title={m.nuevo ? 'Nuevo usuario' : `Usuario ${m.usuario}`} onClose={() => setM(null)} footer={<><button onClick={() => setM(null)}>Cancelar</button><button className="primary" disabled={busy} onClick={() => run(async () => {
          if (m.nuevo) await post('/usuarios', { usuario: m.usuario, nombre: m.nombre, roles: m.roles, clave: m.clave });
          else await put(`/usuarios/${m.usuario}`, { nombre: m.nombre, roles: m.roles, estado: m.estado, clave: m.clave || undefined });
          setM(null); reload();
        }, 'Usuario guardado.')}>Guardar</button></>}>
          <div className="grid c2">
            {m.nuevo && <TextField label="Usuario" req value={m.usuario} onChange={(v) => setM({ ...m, usuario: v })} />}
            <TextField label="Nombre" req value={m.nombre} onChange={(v) => setM({ ...m, nombre: v })} />
            <div className="span-all"><Field label="Roles (marque uno o varios)">{<div>{ROLES_INFO.map((r) => { const on = m.roles.includes(r.codigo); return <div key={r.codigo} className={'rol-card' + (on ? ' on' : '')} style={{ ['--rc' as any]: r.color }}><label><input type="checkbox" checked={on} onChange={(e) => setM({ ...m, roles: e.target.checked ? [...m.roles, r.codigo] : m.roles.filter((x: string) => x !== r.codigo) })} /><span><b style={{ color: r.color }}>{r.nombre}</b><small>{r.descripcion}</small></span></label></div>; })}</div>}</Field></div>
            {!m.nuevo && <SelectField label="Estado" blank={false} value={m.estado} onChange={(v) => setM({ ...m, estado: v })} options={['ACTIVO', 'INACTIVO']} />}
            <TextField label={m.nuevo ? 'Clave inicial' : 'Nueva clave (opcional, restablece)'} req={m.nuevo} value={m.clave} onChange={(v) => setM({ ...m, clave: v })} hint="Mínimo 8 caracteres con letras y números. El usuario deberá cambiarla al ingresar." />
          </div>
        </Modal>
      )}
    </Card>
  );
}

function Bitacora() {
  const [f, setF] = useState<Record<string, string>>({});
  const { data, reload } = useLoad<any[]>(() => get('/bitacora', f), [JSON.stringify(f)]);
  return (
    <Card title="Bitácora de operaciones (auditoría)">
      <div className="row" style={{ marginBottom: 8 }}>
        <SelectField label="Módulo" value={f.modulo} onChange={(v) => setF({ ...f, modulo: v })} options={['ALMACENES', 'COMBUSTIBLE', 'ACTIVOS FIJOS', 'SEGURIDAD', 'CATÁLOGOS']} />
        <TextField label="Usuario" value={f.usuario} onChange={(v) => setF({ ...f, usuario: v })} />
        <button onClick={reload}>Actualizar</button>
      </div>
      <DataTable maxHeight="60vh" rows={data ?? []} cols={[{ key: 'fecha', header: 'Fecha y hora' }, { key: 'usuario', header: 'Usuario' }, { key: 'modulo', header: 'Módulo' }, { key: 'accion', header: 'Acción' }, { key: 'documento', header: 'Documento' }, { key: 'detalle', header: 'Detalle' }]} />
    </Card>
  );
}

export default function Admin() {
  const { esAdmin } = useAuth();
  const [t, setT] = useState<'cfg' | 'usr' | 'bit' | 'resp'>('cfg');
  return (
    <>
      <PageHead title="Administración" sub="Configuración de la entidad, usuarios, auditoría y respaldo" />
      <Tabs value={t} onChange={setT} items={[{ id: 'cfg', label: 'Configuración' }, ...(esAdmin ? [{ id: 'usr' as const, label: 'Usuarios' }, { id: 'bit' as const, label: 'Bitácora' }, { id: 'resp' as const, label: 'Copia de seguridad' }] : [])]} />
      {t === 'cfg' && <Config />}
      {t === 'usr' && <Usuarios />}
      {t === 'bit' && <Bitacora />}
      {t === 'resp' && (
        <Card title="Copia de seguridad">
          <p>Descarga una copia completa de la base de datos SQLite. Con PostgreSQL use <code>pg_dump</code> en el servidor de base de datos.</p>
          <button className="primary" onClick={() => window.open(urlConToken('/backup'), '_blank')}>Descargar copia ahora</button>
          <p className="muted">Se recomienda realizarla a diario y antes del cierre de gestión. Última fecha: {fmtDate(new Date().toISOString().slice(0, 10))}</p>
        </Card>
      )}
    </>
  );
}
