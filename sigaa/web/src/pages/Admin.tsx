import { useState } from 'react';
import { get, post, put, urlConToken, fmtDate } from '../api';
import { useAuth } from '../auth';
import { Card, DataTable, Field, Modal, PageHead, SelectField, Tabs, TextField, useAction, useLoad, Badge } from '../ui';

const ROLES = ['ADMIN', 'ALMACEN', 'COMBUSTIBLE', 'ACTIVOS', 'CONSULTA'];

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
            {(data ?? []).filter((c) => c.modulo === m).map((c) => (
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
      <DataTable rows={data ?? []} onRow={(r) => setM({ ...r, roles: String(r.roles).split(',') })} cols={[{ key: 'usuario', header: 'Usuario' }, { key: 'nombre', header: 'Nombre' }, { key: 'roles', header: 'Roles' }, { key: 'estado', header: 'Estado', badge: true }, { key: 'ultimo_acceso', header: 'Último acceso' }]} />
      <small className="muted">Roles: ADMIN (todo), ALMACEN, COMBUSTIBLE, ACTIVOS (escriben en su módulo) y CONSULTA (solo lectura). Un usuario puede tener varios roles.</small>
      {m && (
        <Modal title={m.nuevo ? 'Nuevo usuario' : `Usuario ${m.usuario}`} onClose={() => setM(null)} footer={<><button onClick={() => setM(null)}>Cancelar</button><button className="primary" disabled={busy} onClick={() => run(async () => {
          if (m.nuevo) await post('/usuarios', { usuario: m.usuario, nombre: m.nombre, roles: m.roles, clave: m.clave });
          else await put(`/usuarios/${m.usuario}`, { nombre: m.nombre, roles: m.roles, estado: m.estado, clave: m.clave || undefined });
          setM(null); reload();
        }, 'Usuario guardado.')}>Guardar</button></>}>
          <div className="grid c2">
            {m.nuevo && <TextField label="Usuario" req value={m.usuario} onChange={(v) => setM({ ...m, usuario: v })} />}
            <TextField label="Nombre" req value={m.nombre} onChange={(v) => setM({ ...m, nombre: v })} />
            <Field label="Roles"><div className="row">{ROLES.map((r) => <label key={r} className="row" style={{ gap: 4 }}><input type="checkbox" checked={m.roles.includes(r)} onChange={(e) => setM({ ...m, roles: e.target.checked ? [...m.roles, r] : m.roles.filter((x: string) => x !== r) })} />{r}</label>)}</div></Field>
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
