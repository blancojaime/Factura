"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { ErrorApi } from "@/components/contratacion/comun";
import ImportarExcel from "@/components/ImportarExcel";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Cargando, Dialog, Field, Input, Tabla, Td, Th } from "@/components/ui";
import { api, ApiError, mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { bs } from "@/lib/format";
import type { Partida } from "@/lib/tipos";

interface Ejecucion { id: string; preventivo_activo: string }

export default function PresupuestoPage() {
  const { user } = useAuth();
  const [partidas, setPartidas] = useState<Partida[] | null>(null);
  const [activos, setActivos] = useState<Map<string, string>>(new Map());
  const [error, setError] = useState("");
  const [nueva, setNueva] = useState(false);
  const [importar, setImportar] = useState(false);
  const [filtro, setFiltro] = useState("");
  const [errForm, setErrForm] = useState<ApiError | string | null>(null);
  const gestiona = user?.rol === "ROL_PRESUPUESTO" || user?.rol === "ROL_ADMIN";

  const cargar = useCallback(async () => {
    try {
      const puedeReporte = user && ["ROL_PRESUPUESTO", "ROL_RPA", "ROL_CONTRATACIONES", "ROL_ADMIN"].includes(user.rol);
      const [p, e] = await Promise.all([api.get<Partida[]>("/partidas"), puedeReporte ? api.get<Ejecucion[]>("/reportes/presupuesto") : Promise.resolve([])]);
      setPartidas(p);
      setActivos(new Map(e.map((x) => [x.id, x.preventivo_activo])));
    } catch (e) { setError(mensajeError(e)); }
  }, [user]);
  useEffect(() => { void cargar(); }, [cargar]);

  async function crear(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setErrForm(null);
    try {
      await api.post("/partidas", {
        codigo_partida: String(f.get("codigo")), descripcion: String(f.get("desc")), descripcion_apertura: String(f.get("apertura")), saldo_disponible: String(f.get("saldo")),
        gestion: Number(f.get("gestion")), programa: String(f.get("programa")), proyecto: String(f.get("proyecto")), actividad: String(f.get("actividad")),
        fuente: String(f.get("fuente")), organismo: String(f.get("organismo")) });
      setNueva(false);
      await cargar();
    } catch (err) { setErrForm(err instanceof ApiError ? err : mensajeError(err)); }
  }

  const visibles = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    if (!partidas) return [];
    return q ? partidas.filter((p) => `${p.programa}-${p.proyecto}-${p.actividad} ${p.codigo_partida} ${p.descripcion} ${p.descripcion_apertura}`.toLowerCase().includes(q)) : partidas;
  }, [partidas, filtro]);

  if (error) return <Alert tipo="error">{error}</Alert>;
  if (!partidas) return <Cargando />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold text-brand-900">Presupuesto — aperturas programáticas y partidas</h1>
        {gestiona && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setImportar(true)}>Importar desde Excel</Button>
            {user?.rol === "ROL_PRESUPUESTO" && <Button onClick={() => { setErrForm(null); setNueva(true); }}>Registrar partida</Button>}
          </div>
        )}
      </div>
      <Input placeholder="Filtrar por apertura, partida o descripción…" value={filtro} onChange={(e) => setFiltro(e.target.value)} aria-label="Filtrar partidas" />
      <Card>
        <CardHeader><CardTitle>Presupuesto de la gestión ({visibles.length} filas)</CardTitle></CardHeader>
        <Tabla aria-label="Partidas presupuestarias">
          <thead><tr><Th>Apertura (Prog-Proy-Act)</Th><Th>Descripción apertura</Th><Th>Partida</Th><Th>Fte / Org</Th>
            <Th className="text-right">Presupuesto (Bs)</Th><Th className="text-right">Ejecutado (Bs)</Th><Th className="text-right">Preventivo activo (Bs)</Th><Th className="text-right">Saldo (Bs)</Th></tr></thead>
          <tbody>{visibles.map((p) => (
            <tr key={p.id}>
              <Td className="num whitespace-nowrap">{p.programa}-{p.proyecto}-{p.actividad}</Td><Td>{p.descripcion_apertura || "—"}</Td>
              <Td><span className="num font-medium">{p.codigo_partida}</span> <span className="text-slate-600">{p.descripcion}</span></Td>
              <Td className="num">{p.fuente} / {p.organismo}</Td>
              <Td className="num text-right">{bs(p.monto_aprobado)}</Td><Td className="num text-right">{bs(p.monto_ejecutado)}</Td>
              <Td className="num text-right">{activos.has(p.id) ? bs(activos.get(p.id)) : "—"}</Td><Td className="num text-right font-semibold">{bs(p.saldo_disponible)}</Td>
            </tr>
          ))}</tbody>
        </Tabla>
      </Card>
      <ImportarExcel abierto={importar} onCerrar={() => setImportar(false)} titulo="Importar presupuesto desde Excel" ruta="/partidas/importar"
        plantilla="presupuesto" columnas={["Código (apertura programática)", "Descripción apertura", "Partida", "Fuente", "Organismo", "Presupuesto", "Ejecutado", "Saldo"]}
        nota="El código de apertura va como Programa-Proyecto-Actividad (ej. 002-0000-001). Si la apertura se repite, puede dejar las celdas siguientes vacías. Al reimportar se actualizan las filas existentes (misma apertura, partida, fuente y organismo). Solo se importan partidas 1xxxx a 4xxxx."
        onHecho={() => void cargar()} />
      <Dialog abierto={nueva} onCerrar={() => setNueva(false)} titulo="Registrar partida presupuestaria" ancho="max-w-xl">
        <form onSubmit={crear} className="grid gap-3 sm:grid-cols-2">
          <Field label="Código de partida (1xxxx a 4xxxx)"><Input name="codigo" pattern="[1-4][0-9]{4}" required /></Field>
          <Field label="Gestión"><Input name="gestion" type="number" defaultValue={new Date().getFullYear()} required /></Field>
          <Field label="Descripción de la partida" className="sm:col-span-2"><Input name="desc" required minLength={3} /></Field>
          <Field label="Descripción de la apertura programática" className="sm:col-span-2"><Input name="apertura" /></Field>
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
