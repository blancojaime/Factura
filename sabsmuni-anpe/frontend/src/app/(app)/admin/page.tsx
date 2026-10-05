'use client';
import { ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useSession } from '@/components/session';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input, Select } from '@/components/ui/form';
import { Table, TD, TH, THead, TR } from '@/components/ui/table';
import { api } from '@/lib/api';
import { ROL_ETIQUETA } from '@/lib/types';
import { fecha } from '@/lib/utils';

interface U { id: string; email: string; nombre: string; activo: boolean; rol: { nombre: keyof typeof ROL_ETIQUETA } }
interface Log { id: string; fecha: string; usuarioEmail: string | null; ip: string | null; accion: string; entidad: string; entidadId: string | null }

export default function Admin() {
  const { rol } = useSession();
  const esAdmin = rol === 'ADMINISTRADOR_SISTEMA';
  const [usuarios, setUsuarios] = useState<U[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [integridad, setIntegridad] = useState<{ integra: boolean; registros: number } | null>(null);
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; t: string } | null>(null);
  const [nu, setNu] = useState({ email: '', nombre: '', rol: 'UNIDAD_SOLICITANTE', password: '' });
  const cargar = () => { if (esAdmin) api<U[]>('/usuarios').then(setUsuarios).catch(() => undefined); api<Log[]>('/auditoria?limite=50').then(setLogs).catch(() => undefined); };
  useEffect(cargar, [esAdmin]); // eslint-disable-line react-hooks/exhaustive-deps
  const crear = async (e: React.FormEvent) => { e.preventDefault(); setMsg(null); try { await api('/usuarios', { body: nu }); setNu({ ...nu, email: '', nombre: '', password: '' }); setMsg({ tipo: 'ok', t: 'Usuario creado.' }); cargar(); } catch (er) { setMsg({ tipo: 'error', t: (er as Error).message }); } };
  const alternar = async (u: U) => { try { await api(`/usuarios/${u.id}`, { method: 'PATCH', body: { activo: !u.activo } }); cargar(); } catch (er) { setMsg({ tipo: 'error', t: (er as Error).message }); } };
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Administración y auditoría</h1>
      {esAdmin && (
        <Card>
          <CardHeader><CardTitle>Usuarios y roles</CardTitle><CardDescription>Contraseña de al menos 10 caracteres con letras y números.</CardDescription></CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Table><THead><TR><TH>Nombre</TH><TH>Correo</TH><TH>Rol</TH><TH>Estado</TH><TH /></TR></THead><tbody>{usuarios.map((u) => <TR key={u.id}><TD>{u.nombre}</TD><TD>{u.email}</TD><TD>{ROL_ETIQUETA[u.rol.nombre]}</TD><TD>{u.activo ? <Badge variant="success">Activo</Badge> : <Badge variant="destructive">Inactivo</Badge>}</TD><TD><Button size="sm" variant="outline" onClick={() => alternar(u)}>{u.activo ? 'Desactivar' : 'Activar'}</Button></TD></TR>)}</tbody></Table>
            <form onSubmit={crear} className="grid gap-2 md:grid-cols-5">
              <Field label="Nombre"><Input required value={nu.nombre} onChange={(e) => setNu({ ...nu, nombre: e.target.value })} /></Field>
              <Field label="Correo"><Input required type="email" value={nu.email} onChange={(e) => setNu({ ...nu, email: e.target.value })} /></Field>
              <Field label="Rol"><Select value={nu.rol} onChange={(e) => setNu({ ...nu, rol: e.target.value })}>{Object.entries(ROL_ETIQUETA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
              <Field label="Contraseña inicial"><Input required type="password" minLength={10} value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} /></Field>
              <div className="flex items-end"><Button type="submit" className="w-full">Crear usuario</Button></div>
            </form>
            {msg && <Alert tipo={msg.tipo}>{msg.t}</Alert>}
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader className="flex-row items-start justify-between"><div><CardTitle>Registro de auditoría</CardTitle><CardDescription>Cadena de hashes: cada registro sella al anterior (fecha, IP, usuario, acción, estado previo/posterior).</CardDescription></div>
          <Button variant="outline" onClick={() => api<{ integra: boolean; registros: number }>('/auditoria/verificar').then(setIntegridad)}><ShieldCheck className="h-4 w-4" />Verificar integridad</Button></CardHeader>
        <CardContent className="flex flex-col gap-3">
          {integridad && <Alert tipo={integridad.integra ? 'ok' : 'error'}>{integridad.integra ? `Cadena íntegra: ${integridad.registros} registros verificados.` : 'ALERTA: se detectó alteración en la cadena de auditoría.'}</Alert>}
          <Table><THead><TR><TH>Fecha</TH><TH>Usuario</TH><TH>IP</TH><TH>Acción</TH><TH>Entidad</TH></TR></THead><tbody>{logs.map((l) => <TR key={l.id}><TD className="whitespace-nowrap">{fecha(l.fecha)} {l.fecha.slice(11, 19)}</TD><TD>{l.usuarioEmail ?? '—'}</TD><TD>{l.ip ?? '—'}</TD><TD className="font-mono text-xs">{l.accion}</TD><TD className="text-xs">{l.entidad} {l.entidadId?.slice(0, 8)}</TD></TR>)}</tbody></Table>
        </CardContent>
      </Card>
    </div>
  );
}
