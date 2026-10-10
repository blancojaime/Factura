"use client";

import { Check, ClipboardCopy } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Alert, Badge, Button, Card, CardBody, CardHeader, CardTitle, Dialog, Field, Input, Tabla, Td, Textarea, Th } from "@/components/ui";
import { api } from "@/lib/api";
import { bs } from "@/lib/format";
import type { BloqueSigep, Contratacion, Partida } from "@/lib/tipos";
import { ErrorApi, useAccion } from "./comun";

/** Verificacion presupuestaria, panel de captura rapida SIGEP (C-31), certificacion, devolucion y devengado. */
export default function PanelPresupuesto({ c, recargar, puedeOperar }: { c: Contratacion; recargar: () => Promise<void>; puedeOperar: boolean }) {
  const { ejecutar, cargando, error, ok, limpiar } = useAccion(recargar);
  const [partidas, setPartidas] = useState<Partida[]>([]);
  const [bloque, setBloque] = useState<BloqueSigep | null>(null);
  const [copiado, setCopiado] = useState(false);
  const [c31, setC31] = useState(c.preventivo_c31_nro ?? "");
  const [devolver, setDevolver] = useState(false);
  const [motivo, setMotivo] = useState("");

  useEffect(() => {
    api.get<Partida[]>("/partidas").then(setPartidas).catch(() => undefined);
  }, [c.estado]);
  useEffect(() => {
    api.get<BloqueSigep>(`/contrataciones/${c.id}/bloque-sigep`).then(setBloque).catch(() => setBloque(null));
  }, [c.id, c.estado, c.preventivos.length]);
  useEffect(() => setC31(c.preventivo_c31_nro ?? ""), [c.preventivo_c31_nro]);

  const requerido = useMemo(() => {
    const m = new Map<string, number>();
    c.items.forEach((i) => i.partida_id && m.set(i.partida_id, (m.get(i.partida_id) ?? 0) + Number(i.subtotal)));
    return [...m.entries()].map(([id, imp]) => ({ partida: partidas.find((p) => p.id === id), importe: imp }));
  }, [c.items, partidas]);

  async function copiar() {
    if (!bloque) return;
    await navigator.clipboard.writeText(bloque.texto_pipe);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2500);
  }

  const certificado = c.preventivos.length > 0;
  const verificable = c.estado === "SOLICITADO";

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader><CardTitle>Verificación de partidas presupuestarias</CardTitle>
          {certificado && <Badge className="bg-emerald-100 text-emerald-800 ring-emerald-300">Presupuesto certificado</Badge>}</CardHeader>
        {certificado ? (
          <Tabla aria-label="Preventivos">
            <thead><tr><Th>Partida</Th><Th>Descripción</Th><Th className="text-right">Importe (Bs)</Th><Th>Estado</Th></tr></thead>
            <tbody>{c.preventivos.map((p) => (
              <tr key={p.partida_id}><Td className="num">{p.codigo_partida}</Td><Td>{p.descripcion}</Td><Td className="num text-right">{bs(p.importe)}</Td><Td><Badge className="bg-slate-100 text-slate-700 ring-slate-300">{p.estado}</Badge></Td></tr>
            ))}</tbody>
          </Tabla>
        ) : (
          <Tabla aria-label="Saldo por partida">
            <thead><tr><Th>Partida</Th><Th>Descripción</Th><Th className="text-right">Requerido (Bs)</Th><Th className="text-right">Saldo disponible (Bs)</Th><Th>Resultado</Th></tr></thead>
            <tbody>{requerido.map(({ partida, importe }, i) => {
              const suficiente = partida ? Number(partida.saldo_disponible) >= importe : false;
              return (
                <tr key={i}><Td className="num">{partida?.codigo_partida}</Td><Td>{partida?.descripcion}</Td><Td className="num text-right">{bs(importe)}</Td>
                  <Td className="num text-right">{partida ? bs(partida.saldo_disponible) : "—"}</Td>
                  <Td><Badge className={suficiente ? "bg-emerald-100 text-emerald-800 ring-emerald-300" : "bg-red-100 text-red-800 ring-red-300"}>{suficiente ? "Saldo suficiente" : "Saldo insuficiente"}</Badge></Td></tr>
              );
            })}</tbody>
          </Tabla>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Panel de captura rápida SIGEP — comprobante C-31</CardTitle>
          {bloque && <Badge className="bg-sky-50 text-sky-800 ring-sky-200">{bloque.origen === "PREVENTIVO" ? "Preventivo certificado" : "Previsto (aún sin certificar)"}</Badge>}
        </CardHeader>
        <CardBody className="space-y-3">
          {bloque && bloque.filas.length > 0 ? (
            <>
              <Tabla aria-label="Bloque SIGEP">
                <thead><tr>{bloque.encabezado.map((h) => <Th key={h} className={h === "IMPORTE" ? "text-right" : ""}>{h}</Th>)}</tr></thead>
                <tbody>{bloque.filas.map((f, i) => (
                  <tr key={i}>{f.map((v, j) => <Td key={j} className={`num ${j === f.length - 1 ? "text-right font-medium" : ""}`}>{j === f.length - 1 ? bs(v) : v}</Td>)}</tr>
                ))}</tbody>
                <tfoot><tr><Td colSpan={8} className="text-right font-semibold">Total</Td><Td className="num text-right font-bold">{bs(bloque.total)}</Td></tr></tfoot>
              </Tabla>
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={copiar} variant="outline">
                  {copiado ? <Check className="h-4 w-4 text-emerald-600" aria-hidden /> : <ClipboardCopy className="h-4 w-4" aria-hidden />}
                  {copiado ? "¡Copiado!" : "Copiar Bloque SIGEP"}
                </Button>
                <code className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">DA | UE | PROGRAMA | PROYECTO | ACTIVIDAD | FTE | ORG | PARTIDA | IMPORTE</code>
              </div>
              <p className="text-xs text-slate-500">Copia una línea por partida con ese formato para pegarla en la pantalla de captura del C-31 del SIGEP.</p>
            </>
          ) : <p className="text-sm text-slate-500">Aún no hay partidas en la solicitud.</p>}
        </CardBody>
      </Card>

      {puedeOperar && (
        <Card>
          <CardHeader><CardTitle>Acciones de Presupuesto</CardTitle></CardHeader>
          <CardBody className="space-y-4">
            {(verificable || certificado) && (
              <Field label="N° de comprobante C-31 (SIGEP)" hint="Puede registrarlo al certificar o después, antes de la formalización">
                <div className="flex gap-2">
                  <Input value={c31} onChange={(e) => setC31(e.target.value)} placeholder="Ej.: C31-2026-00123" className="max-w-xs" />
                  {certificado && (
                    <Button variant="outline" disabled={!c31.trim() || c31 === c.preventivo_c31_nro} cargando={cargando === "c31"}
                      onClick={() => ejecutar("c31", () => api.put(`/contrataciones/${c.id}/c31`, { preventivo_c31_nro: c31 }), "N° de C-31 registrado")}>Guardar N° C-31</Button>
                  )}
                </div>
              </Field>
            )}
            {verificable && (
              <div className="flex flex-wrap gap-3">
                <Button variant="success" cargando={cargando === "certificar"}
                  onClick={() => { limpiar(); void ejecutar("certificar", () => api.post(`/contrataciones/${c.id}/certificar`, { preventivo_c31_nro: c31.trim() || null }), "Presupuesto certificado y saldo descontado"); }}>
                  Certificar presupuesto
                </Button>
                <Button variant="outline" onClick={() => { limpiar(); setDevolver(true); }}>Devolver a la unidad solicitante</Button>
              </div>
            )}
            {c.acciones.includes("devengar") && (
              <Alert tipo="info" titulo="Recepción conforme registrada">
                <p>Registre el devengado: se carga el monto adjudicado y se libera al presupuesto la diferencia con lo reservado.</p>
                <Button variant="success" className="mt-2" cargando={cargando === "devengar"} onClick={() => ejecutar("devengar", () => api.post(`/contrataciones/${c.id}/devengar`), "Devengado registrado")}>Registrar devengado</Button>
              </Alert>
            )}
            {ok && <Alert tipo="success">{ok}</Alert>}
            <ErrorApi error={error} />
          </CardBody>
        </Card>
      )}

      <Dialog abierto={devolver} onCerrar={() => setDevolver(false)} titulo="Devolver la solicitud">
        <div className="space-y-4">
          <Field label="Motivo de la devolución (p. ej. saldo insuficiente)"><Textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} /></Field>
          <ErrorApi error={error} />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDevolver(false)}>Cancelar</Button>
            <Button disabled={motivo.trim().length < 10} cargando={cargando === "devolver"}
              onClick={async () => { if (await ejecutar("devolver", () => api.post(`/contrataciones/${c.id}/devolver`, { motivo }))) setDevolver(false); }}>Devolver</Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
