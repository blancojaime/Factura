"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Cargando, Dialog, Field, Input, Tabla, Td, Th } from "@/components/ui";
import { api, ApiError, mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { bs } from "@/lib/format";
import type { Partida } from "@/lib/tipos";
import { ErrorApi } from "@/components/contratacion/comun";

interface Ejecucion { codigo_partida: string; descripcion: string; gestion: number; aprobado: string; saldo_disponible: string; preventivo_activo: string }

export default function PresupuestoPage() {
  const { user } = useAuth();
  const [filas, setFilas] = useState<Ejecucion[] | null>(null);
  const [partidas, setPartidas] = useState<Partida[]>([]);
  const [error, setError] = useState("");
  const [nueva, setNueva] = useState(false);
  const [errForm, setErrForm] = useState<ApiError | string | null>(null);

  const cargar = useCallback(async () => {
    try {
      const puedeReporte = user && ["ROL_PRESUPUESTO", "ROL_RPA", "ROL_CONTRATACIONES", "ROL_ADMIN"].includes(user.rol);
      const [p, e] = await Promise.all([api.get<Partida[]>("/partidas"), puedeReporte ? api.get<Ejecucion[]>("/reportes/presupuesto") : Promise.resolve([])]);
      setPartidas(p);
      setFilas(e);
    } catch (e) { setError(mensajeError(e)); }
  }, [user]);
  useEffect(() => { void cargar(); }, [cargar]);

  async function crear(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setErrForm(null);
    try {
      await api.post("/partidas", {
        codigo_partida: String(f.get("codigo")), descripcion: String(f.get("desc")), saldo_disponible: String(f.get("saldo")), gestion: Number(f.get("gestion")),
        programa: String(f.get("programa")), proyecto: String(f.get("proyecto")), actividad: String(f.get("actividad")), fuente: String(f.get("fuente")), organismo: String(f.get("organismo")) });
      setNueva(false);
      await cargar();
    } catch (err) { setErrForm(err instanceof ApiError ? err : mensajeError(err)); }
  }

  if (error) return <Alert tipo="error">{error}</Alert>;
  if (!filas) return <Cargando />;
  const porId = new Map(filas.map((f) => [f.codigo_partida + f.gestion, f]));
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-brand-900">Presupuesto — partidas y ejecución</h1>
        {user?.rol === "ROL_PRESUPUESTO" && <Button onClick={() => { setErrForm(null); setNueva(true); }}>Registrar partida</Button>}
      </div>
      <Card>
        <CardHeader><CardTitle>Partidas de la gestión</CardTitle></CardHeader>
        <Tabla aria-label="Partidas presupuestarias">
          <thead><tr><Th>Partida</Th><Th>Descripción</Th><Th>Estructura (Prog/Proy/Act/Fte/Org)</Th><Th className="text-right">Aprobado (Bs)</Th><Th className="text-right">Preventivo activo (Bs)</Th><Th className="text-right">Saldo disponible (Bs)</Th></tr></thead>
          <tbody>{partidas.map((p) => {
            const e = porId.get(p.codigo_partida + p.gestion);
            return (
              <tr key={p.id}><Td className="num font-medium">{p.codigo_partida}</Td><Td>{p.descripcion}</Td>
                <Td className="num text-slate-600">{p.programa}/{p.proyecto}/{p.actividad}/{p.fuente}/{p.organismo}</Td>
                <Td className="num text-right">{bs(p.monto_aprobado)}</Td><Td className="num text-right">{e ? bs(e.preventivo_activo) : "—"}</Td>
                <Td className="num text-right font-semibold">{bs(p.saldo_disponible)}</Td></tr>
            );
          })}</tbody>
        </Tabla>
      </Card>
      <Dialog abierto={nueva} onCerrar={() => setNueva(false)} titulo="Registrar partida presupuestaria" ancho="max-w-xl">
        <form onSubmit={crear} className="grid gap-3 sm:grid-cols-2">
          <Field label="Código de partida (1xxxx a 4xxxx)"><Input name="codigo" pattern="[1-4][0-9]{4}" required /></Field>
          <Field label="Gestión"><Input name="gestion" type="number" defaultValue={new Date().getFullYear()} required /></Field>
          <Field label="Descripción" className="sm:col-span-2"><Input name="desc" required minLength={3} /></Field>
          <Field label="Saldo inicial (Bs)"><Input name="saldo" type="number" step="0.01" min={0} required /></Field>
          <div />
          <Field label="Programa"><Input name="programa" defaultValue="01" /></Field><Field label="Proyecto"><Input name="proyecto" defaultValue="0000" /></Field>
          <Field label="Actividad"><Input name="actividad" defaultValue="001" /></Field><Field label="Fuente"><Input name="fuente" defaultValue="20" /></Field>
          <Field label="Organismo"><Input name="organismo" defaultValue="230" /></Field>
          <div className="sm:col-span-2"><ErrorApi error={errForm} /></div>
          <div className="flex justify-end gap-2 sm:col-span-2"><Button variant="outline" onClick={() => setNueva(false)}>Cancelar</Button><Button type="submit">Guardar</Button></div>
        </form>
      </Dialog>
      <CardBody className="p-0 text-xs text-slate-500">Las partidas siguen el Clasificador Presupuestario (1xxxx a 4xxxx). Los códigos de las pruebas son ilustrativos.</CardBody>
    </div>
  );
}
