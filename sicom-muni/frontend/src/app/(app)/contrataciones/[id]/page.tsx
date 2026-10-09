"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import AprobarInicio from "@/components/contratacion/AprobarInicio";
import Cabecera from "@/components/contratacion/Cabecera";
import Formulador from "@/components/contratacion/Formulador";
import PanelCotizaciones from "@/components/contratacion/PanelCotizaciones";
import PanelDocumentos from "@/components/contratacion/PanelDocumentos";
import PanelFormalizacion from "@/components/contratacion/PanelFormalizacion";
import PanelPresupuesto from "@/components/contratacion/PanelPresupuesto";
import Resumen from "@/components/contratacion/Resumen";
import { Alert, Cargando, Tabs } from "@/components/ui";
import { api, ApiError, mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Contratacion, Rol } from "@/lib/tipos";

type Pestana = "resumen" | "presupuesto" | "cotizaciones" | "formalizacion" | "documentos";

/** Pestana inicial segun el rol y el estado: la que contiene la accion pendiente. */
function inicial(c: Contratacion, rol: Rol): Pestana {
  if (rol === "ROL_PRESUPUESTO" && ["SOLICITADO", "RECEPCIONADO"].includes(c.estado)) return "presupuesto";
  if (["ROL_CONTRATACIONES"].includes(rol) && c.estado === "EN_COTIZACION") return "cotizaciones";
  if (rol === "ROL_RPA" && c.estado === "EVALUADO") return "cotizaciones";
  if (rol === "ROL_RPA" && c.estado === "ADJUDICADO") return "formalizacion";
  if (rol === "ROL_RECEPCION" && c.estado === "FORMALIZADO") return "formalizacion";
  return "resumen";
}

export default function DetallePage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [c, setC] = useState<Contratacion | null>(null);
  const [error, setError] = useState<string>("");
  const [tab, setTab] = useState<Pestana | null>(null);

  const recargar = useCallback(async () => {
    try {
      setC(await api.get<Contratacion>(`/contrataciones/${id}`));
      setError("");
    } catch (e) {
      setError(e instanceof ApiError && e.status === 404 ? "La contratación no existe o no tiene acceso." : mensajeError(e));
    }
  }, [id]);

  useEffect(() => { void recargar(); }, [recargar]);
  useEffect(() => { if (c && user && tab === null) setTab(inicial(c, user.rol)); }, [c, user, tab]);

  if (error) return <Alert tipo="error">{error}</Alert>;
  if (!c || !user) return <Cargando />;

  const esCreador = c.created_by_id === user.id;
  if (c.estado === "BORRADOR" && user.rol === "ROL_SOLICITANTE" && esCreador) {
    return (
      <div className="space-y-5">
        <Cabecera c={c} recargar={recargar} />
        <Formulador c={c} recargar={recargar} />
      </div>
    );
  }

  const puedePresupuesto = ["ROL_PRESUPUESTO", "ROL_RPA", "ROL_ADMIN", "ROL_CONTRATACIONES"].includes(user.rol);
  const items: { id: Pestana; etiqueta: string; contador?: number }[] = [
    { id: "resumen", etiqueta: "Resumen" },
    ...(puedePresupuesto ? [{ id: "presupuesto" as const, etiqueta: "Presupuesto y SIGEP" }] : []),
    { id: "cotizaciones", etiqueta: "Cotizaciones y adjudicación", contador: c.cotizaciones.length },
    { id: "formalizacion", etiqueta: "Formalización y recepción" },
    { id: "documentos", etiqueta: "Documentos", contador: c.documentos.length },
  ];
  const actual: Pestana = tab ?? "resumen";

  return (
    <div className="space-y-5">
      <Cabecera c={c} recargar={recargar} />
      <Tabs valor={actual} onCambio={setTab} items={items} />
      {actual === "resumen" && <Resumen c={c} />}
      {actual === "presupuesto" && <PanelPresupuesto c={c} recargar={recargar} puedeOperar={user.rol === "ROL_PRESUPUESTO"} />}
      {actual === "cotizaciones" && <PanelCotizaciones c={c} recargar={recargar} esContrataciones={user.rol === "ROL_CONTRATACIONES"} esRpa={user.rol === "ROL_RPA"} />}
      {actual === "formalizacion" && <PanelFormalizacion c={c} recargar={recargar} esRpa={user.rol === "ROL_RPA"} esRecepcion={user.rol === "ROL_RECEPCION"} />}
      {actual === "documentos" && <PanelDocumentos c={c} />}
      {c.acciones.includes("aprobar_inicio") && user.rol === "ROL_RPA" && <AprobarInicio c={c} recargar={recargar} />}
    </div>
  );
}

