"use client";

import { Alert, Button, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { api } from "@/lib/api";
import type { Contratacion } from "@/lib/tipos";
import { ErrorApi, useAccion } from "./comun";

/** Aprobacion de inicio del proceso por el RPA (tras la certificacion presupuestaria). */
export default function AprobarInicio({ c, recargar }: { c: Contratacion; recargar: () => Promise<void> }) {
  const { ejecutar, cargando, error } = useAccion(recargar);
  return (
    <Card className="border-brand-500">
      <CardHeader><CardTitle>Aprobación de inicio del proceso</CardTitle></CardHeader>
      <CardBody className="space-y-3">
        <Alert tipo="info">El presupuesto está certificado (C-31 {c.preventivo_c31_nro ?? "pendiente de registrar"}). Al aprobar, Contrataciones podrá emitir las fichas y recibir cotizaciones.</Alert>
        <ErrorApi error={error} />
        <Button variant="success" cargando={cargando === "aprobar"} onClick={() => ejecutar("aprobar", () => api.post(`/contrataciones/${c.id}/aprobar-inicio`))}>Aprobar inicio del proceso</Button>
      </CardBody>
    </Card>
  );
}
