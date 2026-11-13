"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Alert, Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Tabla, Td, Textarea, Th } from "@/components/ui";
import { api } from "@/lib/api";
import { fecha, METODO_LABEL } from "@/lib/format";
import type { Contratacion } from "@/lib/tipos";
import { ErrorApi, useAccion } from "./comun";

function Requisito({ cumplido, children }: { cumplido: boolean; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2 text-sm">
      {cumplido ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" aria-hidden />}
      <span>{children}</span>
    </li>
  );
}

/** Formalizacion (Orden o Contrato segun el plazo) y recepcion con verificacion cuantitativa y cualitativa. */
export default function PanelFormalizacion({ c, recargar, esRpa, esRecepcion }: {
  c: Contratacion; recargar: () => Promise<void>; esRpa: boolean; esRecepcion: boolean;
}) {
  const { ejecutar, cargando, error, ok, limpiar } = useAccion(recargar);
  const [cuce, setCuce] = useState(c.cuce ?? "");
  const hoy = new Date().toISOString().slice(0, 10);
  const [conforme, setConforme] = useState(true);
  const [detalle, setDetalle] = useState<Record<number, { cant: string; ok: boolean }>>({});
  const esContrato = c.metodo_formalizacion === "CONTRATO";
  const adj = c.cotizaciones.find((q) => q.adjudicado);
  const consulta = c.modalidad_cuantia === "CONSULTA_PRECIOS_SICOES";

  async function recepcionar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await ejecutar("recepcion", () => api.post(`/contrataciones/${c.id}/recepcion`, {
      fecha_recepcion: String(f.get("fecha")), conforme, observaciones: String(f.get("obs") ?? ""),
      detalle: c.items.map((i) => ({ numero: i.numero, cantidad_recibida: detalle[i.numero]?.cant ?? i.cantidad, conforme: detalle[i.numero]?.ok ?? true })),
    }), conforme ? "Recepción registrada" : "Recepción observada registrada");
  }

  return (
    <div className="space-y-5">
      {(c.estado === "ADJUDICADO" || ["FORMALIZADO", "RECEPCIONADO", "DEVENGADO"].includes(c.estado)) && (
        <Card>
          <CardHeader><CardTitle>Formalización</CardTitle>
            <Badge className={esContrato ? "bg-violet-100 text-violet-800 ring-violet-300" : "bg-sky-100 text-sky-800 ring-sky-300"}>{c.metodo_formalizacion ? METODO_LABEL[c.metodo_formalizacion] : "—"}</Badge></CardHeader>
          <CardBody className="space-y-3">
            <Alert tipo={esContrato ? "warning" : "info"} titulo={esContrato ? "Contrato Administrativo obligatorio" : "Orden de Compra / Servicio"}>
              {esContrato
                ? `El plazo de ${c.plazo_dias_calendario} días calendario supera los 15 días: se emite Contrato Administrativo y se bloquea la emisión de órdenes simples.`
                : `El plazo de ${c.plazo_dias_calendario} días calendario (≤ 15) corresponde a ${c.tipo_objeto === "BIEN" ? "Orden de Compra" : "Orden de Servicio"}.`}
            </Alert>
            {adj && <p className="text-sm">Proveedor adjudicado: <b>{adj.razon_social}</b> — Bs {Number(adj.monto_total_ofertado).toLocaleString("es-BO", { minimumFractionDigits: 2 })}</p>}
            {c.estado === "ADJUDICADO" && (
              <>
                <ul className="space-y-1.5">
                  <Requisito cumplido={!!c.preventivo_c31_nro}>N° de comprobante C-31 registrado por Presupuesto {c.preventivo_c31_nro ? `(${c.preventivo_c31_nro})` : "— falta"}</Requisito>
                  <Requisito cumplido={!consulta || !!(cuce.trim() || c.cuce)}>CUCE del proceso{consulta ? " (obligatorio en Consulta de Precios)" : " (opcional)"}</Requisito>
                </ul>
                {esRpa && (
                  <div className="flex flex-wrap items-end gap-3">
                    <Field label="CUCE"><Input value={cuce} onChange={(e) => setCuce(e.target.value)} className="w-72" placeholder="26-1234-00-1234567-1-1" /></Field>
                    <Button variant="success" cargando={cargando === "formalizar"}
                      onClick={() => { limpiar(); void ejecutar("formalizar", () => api.post(`/contrataciones/${c.id}/formalizar`, { cuce: cuce.trim() || null }), "Trámite formalizado: se emitió el documento contractual"); }}>
                      Formalizar ({esContrato ? "Contrato" : c.tipo_objeto === "BIEN" ? "Orden de Compra" : "Orden de Servicio"})
                    </Button>
                  </div>
                )}
              </>
            )}
            {c.cuce && c.estado !== "ADJUDICADO" && <p className="text-sm">CUCE: <b>{c.cuce}</b></p>}
            {ok && <Alert tipo="success">{ok}</Alert>}
            <ErrorApi error={error} />
          </CardBody>
        </Card>
      )}

      {c.recepciones.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Recepciones registradas</CardTitle></CardHeader>
          <Tabla aria-label="Recepciones">
            <thead><tr><Th>Fecha</Th><Th>Resultado</Th><Th>NIA / Informe</Th><Th>Días de retraso</Th><Th>Observaciones</Th></tr></thead>
            <tbody>{c.recepciones.map((r) => (
              <tr key={r.id}><Td>{fecha(r.fecha_recepcion)}</Td>
                <Td><Badge className={r.conforme ? "bg-emerald-100 text-emerald-800 ring-emerald-300" : "bg-amber-100 text-amber-800 ring-amber-300"}>{r.conforme ? "Conforme" : "Observada"}</Badge></Td>
                <Td className="num">{r.nro_nia ?? "—"}</Td><Td>{r.dias_retraso}</Td><Td>{r.observaciones || "—"}</Td></tr>
            ))}</tbody>
          </Tabla>
        </Card>
      )}

      {esRecepcion && c.estado === "FORMALIZADO" && (
        <form onSubmit={recepcionar} aria-label="Registrar recepción">
          <Card>
            <CardHeader><CardTitle>Verificación y recepción</CardTitle><span className="text-xs text-slate-500">Se genera la NIA / Informe de Conformidad y el Acta Formulario 500</span></CardHeader>
            <CardBody className="space-y-4">
              <Tabla aria-label="Verificación cuantitativa y cualitativa">
                <thead><tr><Th>N°</Th><Th>Descripción</Th><Th className="text-right">Contratado</Th><Th className="text-right">Recibido</Th><Th>Conforme (cualitativo)</Th></tr></thead>
                <tbody>{c.items.map((i) => (
                  <tr key={i.id}><Td>{i.numero}</Td><Td>{i.descripcion_especifica}</Td><Td className="num text-right">{Number(i.cantidad)}</Td>
                    <Td className="text-right"><Input type="number" step="0.001" min={0} className="ml-auto w-28 text-right" aria-label={`Cantidad recibida ítem ${i.numero}`}
                      value={detalle[i.numero]?.cant ?? i.cantidad} onChange={(e) => setDetalle((d) => ({ ...d, [i.numero]: { cant: e.target.value, ok: d[i.numero]?.ok ?? true } }))} /></Td>
                    <Td><input type="checkbox" aria-label={`Conforme ítem ${i.numero}`} checked={detalle[i.numero]?.ok ?? true} onChange={(e) => setDetalle((d) => ({ ...d, [i.numero]: { cant: d[i.numero]?.cant ?? i.cantidad, ok: e.target.checked } }))} /></Td></tr>
                ))}</tbody>
              </Tabla>
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="Fecha de recepción"><Input name="fecha" type="date" defaultValue={hoy} max={hoy} required /></Field>
                <label className="flex items-end gap-2 pb-2 text-sm font-medium"><input type="checkbox" checked={conforme} onChange={(e) => setConforme(e.target.checked)} /> Recepción conforme</label>
                <div />
                <Field label="Observaciones (obligatorias si hay faltantes o no conformidad)" className="sm:col-span-3"><Textarea name="obs" /></Field>
              </div>
              {ok && <Alert tipo="success">{ok}</Alert>}
              <ErrorApi error={error} />
              <div className="flex justify-end"><Button type="submit" variant="success" cargando={cargando === "recepcion"}>Registrar recepción</Button></div>
            </CardBody>
          </Card>
        </form>
      )}
    </div>
  );
}
