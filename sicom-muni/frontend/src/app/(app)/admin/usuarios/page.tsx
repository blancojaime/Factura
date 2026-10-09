"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorApi } from "@/components/contratacion/comun";
import { Alert, Badge, Button, Card, CardHeader, CardTitle, Cargando, Dialog, Field, Input, Select, Tabla, Td, Th } from "@/components/ui";
import { api, ApiError, mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROL_LABEL } from "@/lib/format";
import type { Rol, Usuario } from "@/lib/tipos";

export default function UsuariosPage() {
  const { user } = useAuth();
  const [lista, setLista] = useState<Usuario[] | null>(null);
  const [error, setError] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [errForm, setErrForm] = useState<ApiError | string | null>(null);

  const cargar = useCallback(() => api.get<Usuario[]>("/admin/usuarios").then(setLista).catch((e) => setError(mensajeError(e))), []);
  useEffect(() => { void cargar(); }, [cargar]);

  async function crear(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setErrForm(null);
    try {
      await api.post("/admin/usuarios", { username: String(f.get("username")), password: String(f.get("password")), nombre_completo: String(f.get("nombre")),
        cargo: String(f.get("cargo")), rol: String(f.get("rol")), email: String(f.get("email")) });
      setAbierto(false);
      await cargar();
    } catch (err) { setErrForm(err instanceof ApiError ? err : mensajeError(err)); }
  }

  async function alternar(u: Usuario) {
    try { await api.patch(`/admin/usuarios/${u.id}`, { activo: !u.activo }); await cargar(); } catch (e) { setError(mensajeError(e)); }
  }
  async function restablecer(u: Usuario) {
    const nueva = window.prompt(`Nueva contraseña para ${u.username} (mín. 10 caracteres, mayúsculas, minúsculas y números)`);
    if (!nueva) return;
    try { await api.patch(`/admin/usuarios/${u.id}`, { password: nueva }); setError(""); } catch (e) { setError(mensajeError(e)); }
  }

  if (!lista && !error) return <Cargando />;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-2xl font-bold text-brand-900">Usuarios y roles</h1><Button onClick={() => { setErrForm(null); setAbierto(true); }}>Nuevo usuario</Button></div>
      {error && <Alert tipo="error">{error}</Alert>}
      <Card>
        <CardHeader><CardTitle>Usuarios del sistema</CardTitle><span className="text-xs text-slate-500">Argon2id · bloqueo tras 5 intentos fallidos</span></CardHeader>
        <Tabla aria-label="Usuarios">
          <thead><tr><Th>Usuario</Th><Th>Nombre</Th><Th>Cargo</Th><Th>Rol</Th><Th>Estado</Th><Th /></tr></thead>
          <tbody>{(lista ?? []).map((u) => (
            <tr key={u.id}><Td className="font-medium">{u.username}</Td><Td>{u.nombre_completo}</Td><Td>{u.cargo}</Td><Td>{ROL_LABEL[u.rol]}</Td>
              <Td><Badge className={u.activo ? "bg-emerald-100 text-emerald-800 ring-emerald-300" : "bg-slate-100 text-slate-600 ring-slate-300"}>{u.activo ? "Activo" : "Inactivo"}</Badge></Td>
              <Td><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => restablecer(u)}>Restablecer clave</Button>
                {u.id !== user?.id && <Button size="sm" variant="outline" onClick={() => alternar(u)}>{u.activo ? "Desactivar" : "Activar"}</Button>}</div></Td></tr>
          ))}</tbody>
        </Tabla>
      </Card>
      <Dialog abierto={abierto} onCerrar={() => setAbierto(false)} titulo="Nuevo usuario">
        <form onSubmit={crear} className="space-y-3">
          <Field label="Usuario"><Input name="username" required minLength={3} pattern="[A-Za-z0-9_.\-]+" /></Field>
          <Field label="Nombre completo"><Input name="nombre" required minLength={3} /></Field>
          <Field label="Cargo"><Input name="cargo" /></Field><Field label="Correo"><Input name="email" type="email" /></Field>
          <Field label="Rol"><Select name="rol" defaultValue="ROL_SOLICITANTE">{(Object.keys(ROL_LABEL) as Rol[]).map((r) => <option key={r} value={r}>{ROL_LABEL[r]}</option>)}</Select></Field>
          <Field label="Contraseña inicial" hint="Mínimo 10 caracteres con mayúsculas, minúsculas y números"><Input name="password" type="password" required minLength={10} autoComplete="new-password" /></Field>
          <ErrorApi error={errForm} />
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setAbierto(false)}>Cancelar</Button><Button type="submit">Crear usuario</Button></div>
        </form>
      </Dialog>
    </div>
  );
}
