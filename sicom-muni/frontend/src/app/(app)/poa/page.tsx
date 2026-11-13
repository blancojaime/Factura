"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorApi } from "@/components/contratacion/comun";
import ImportarExcel from "@/components/ImportarExcel";
import { Alert, Button, Card, CardHeader, CardTitle, Cargando, Dialog, Field, Input, Tabla, Td, Textarea, Th } from "@/components/ui";
import { api, ApiError, mensajeError } from "@/lib/api";
import type { ObjetivoPoa } from "@/lib/tipos";

/** Objetivos del POA por programa presupuestario: base de la Certificación del POA que se emite al certificar el presupuesto. */
export default function PoaPage() {
  const [lista, setLista] = useState<ObjetivoPoa[] | null>(null);
  const [error, setError] = useState("");
  const [filtro, setFiltro] = useState("");
  const [importar, setImportar] = useState(false);
  const [edita, setEdita] = useState<Partial<ObjetivoPoa> | null>(null);
  const [errForm, setErrForm] = useState<ApiError | string | null>(null);

  const cargar = useCallback(() => api.get<ObjetivoPoa[]>("/poa/objetivos").then(setLista).catch((e) => setError(mensajeError(e))), []);
  useEffect(() => { void cargar(); }, [cargar]);

  async function guardar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setErrForm(null);
    try {
      await api.put("/poa/objetivos", {
        gestion: Number(f.get("gestion")), programa: String(f.get("programa")).trim(), denominacion_programa: String(f.get("denominacion")).trim(),
        codigo_objetivo: String(f.get("codigo")).trim(), descripcion_objetivo: String(f.get("descripcion")).trim() });
      setEdita(null);
      await cargar();
    } catch (x) { setErrForm(x instanceof ApiError ? x : mensajeError(x)); }
  }
  async function eliminar(o: ObjetivoPoa) {
    if (!window.confirm(`¿Eliminar el objetivo ${o.codigo_objetivo} del programa ${o.programa}?`)) return;
    try { await api.del(`/poa/objetivos/${o.id}`); await cargar(); } catch (e) { setError(mensajeError(e)); }
  }

  if (!lista && !error) return <Cargando />;
  const q = filtro.trim().toLowerCase();
  const visibles = (lista ?? []).filter((o) => !q || `${o.programa} ${o.denominacion_programa} ${o.codigo_objetivo} ${o.descripcion_objetivo}`.toLowerCase().includes(q));
  const gestionActual = lista?.[0]?.gestion ?? new Date().getFullYear();
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold text-brand-900">Objetivos del POA por programa</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setImportar(true)}>Importar desde Excel</Button>
          <Button onClick={() => { setErrForm(null); setEdita({ gestion: gestionActual }); }}>Registrar objetivo</Button>
        </div>
      </div>
      {error && <Alert tipo="error">{error}</Alert>}
      <Alert tipo="info">Cada programa presupuestario se relaciona con un objetivo de gestión del POA. Al certificar el presupuesto, el sistema emite la <b>Certificación del POA</b> con el programa, su objetivo y la justificación del apoyo de la compra.</Alert>
      <Input placeholder="Filtrar por programa u objetivo…" value={filtro} onChange={(e) => setFiltro(e.target.value)} aria-label="Filtrar objetivos" />
      <Card>
        <CardHeader><CardTitle>Programas y objetivos ({visibles.length})</CardTitle></CardHeader>
        <Tabla aria-label="Objetivos del POA">
          <thead><tr><Th>Programa</Th><Th>Denominación del programa</Th><Th>Cód. objetivo</Th><Th>Descripción del objetivo</Th><Th /></tr></thead>
          <tbody>{visibles.map((o) => (
            <tr key={o.id}><Td className="num font-medium">{o.programa}</Td><Td>{o.denominacion_programa}</Td><Td className="num">{o.codigo_objetivo}</Td><Td>{o.descripcion_objetivo}</Td>
              <Td><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => { setErrForm(null); setEdita(o); }}>Editar</Button>
                <Button size="sm" variant="outline" onClick={() => eliminar(o)}>Eliminar</Button></div></Td></tr>
          ))}</tbody>
        </Tabla>
      </Card>
      <ImportarExcel abierto={importar} onCerrar={() => setImportar(false)} titulo="Importar objetivos del POA desde Excel" ruta="/poa/objetivos/importar"
        plantilla="poa" columnas={["PROG", "DENOMINACIÓN DEL PROGRAMA", "COD OBJ", "DESCRIPCIÓN OBJETIVO"]}
        nota="Si el programa ya existe se actualiza su objetivo ('2' y '002' se consideran el mismo programa)."
        onHecho={() => void cargar()} />
      <Dialog abierto={!!edita} onCerrar={() => setEdita(null)} titulo={edita?.id ? "Editar objetivo del POA" : "Registrar objetivo del POA"}>
        {edita && (
          <form onSubmit={guardar} className="space-y-3">
            <Field label="Gestión"><Input name="gestion" type="number" defaultValue={edita.gestion} required /></Field>
            <Field label="Programa (código)"><Input name="programa" defaultValue={edita.programa ?? ""} required maxLength={10} /></Field>
            <Field label="Denominación del programa"><Input name="denominacion" defaultValue={edita.denominacion_programa ?? ""} /></Field>
            <Field label="Código del objetivo"><Input name="codigo" defaultValue={edita.codigo_objetivo ?? ""} required maxLength={30} /></Field>
            <Field label="Descripción del objetivo de gestión"><Textarea name="descripcion" defaultValue={edita.descripcion_objetivo ?? ""} required minLength={3} /></Field>
            <ErrorApi error={errForm} />
            <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setEdita(null)}>Cancelar</Button><Button type="submit">Guardar</Button></div>
          </form>
        )}
      </Dialog>
    </div>
  );
}
