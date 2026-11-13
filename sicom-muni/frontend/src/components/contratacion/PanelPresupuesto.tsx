"use client";

import { Check, ClipboardCopy } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Alert, Badge, Button, Card, CardBody, CardHeader, CardTitle, Dialog, Field, Input, Tabla, Td, Textarea, Th } from "@/components/ui";
import { api } from "@/lib/api";
import { bs } from "@/lib/format";
import type { BloqueSigep, Contratacion, Partida, ProgramaPoa } from "@/lib/tipos";
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
  const [programas, setProgramas] = useState<ProgramaPoa[]>([]);
  const [justPoa, setJustPoa] = useState(c.justificacion_poa ?? "");

  useEffect(() => {
    api.get<Partida[]>("/partidas").then(setPartidas).catch(() => undefined);
  }, [c.estado]);
  useEffect(() => {
    api.get<BloqueSigep>(`/contrataciones/${c.id}/bloque-sigep`).then(setBloque).catch(() => setBloque(null));
  }, [c.id, c.estado, c.preventivos.length]);
  useEffect(() => setC31(c.preventivo_c31_nro ?? ""), [c.preventivo_c31_nro]);
  useEffect(() => {
    api.get<ProgramaPoa[]>(`/contrataciones/${c.id}/poa`).then(setProgramas).catch(() => setProgramas([]));
  }, [c.id, c.estado]);
  useEffect(() => setJustPoa(c.justificacion_poa ?? ""), [c.justificacion_poa]);
  const faltanObjetivos = programas.some((p) => !p.objetivo_registrado);

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

  // (+) resumen de ejecucion: antes de devengar (previsto) y despues (devengado real)
  const devengado = c.estado === "DEVENGADO";
  const adjudicada = c.cotizaciones.find((q) => q.adjudicado);
  const filasEjecucion = c.preventivos.map((p) => {
    const pa = partidas.find((x) => x.id === p.partida_id);
    return { p, pa };
  });
  const totReservado = c.preventivos.reduce((a, p) => a + Number(p.importe), 0);
  const montoAdj = Number(adjudicada?.monto_total_ofertado ?? 0);
  // lo que realmente se devengara en cada partida (reparto proporcional de lo adjudicado)
  const aDevengar = (importe: string) => devengado ? Number(importe) : (totReservado > 0 ? (montoAdj * Number(importe)) / totReservado : 0);
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

      {certificado && (c.estado === "RECEPCIONADO" || devengado) && (
        <Card>
          <CardHeader><CardTitle>{devengado ? "Ejecución presupuestaria — devengado registrado" : "Ejecución presupuestaria — previsión del devengado"}</CardTitle>
            <Badge className={devengado ? "bg-emerald-100 text-emerald-800 ring-emerald-300" : "bg-amber-100 text-amber-800 ring-amber-300"}>{devengado ? "Devengado" : "Pendiente de devengar"}</Badge></CardHeader>
          <Tabla aria-label="Ejecución presupuestaria del trámite">
            <thead><tr><Th>Apertura</Th><Th>Fte/Org</Th><Th>Partida</Th><Th className="text-right">Presupuesto (Bs)</Th>
              <Th className="text-right">{devengado ? "Devengado en este trámite (Bs)" : "Reservado (Bs)"}</Th>
              <Th className="text-right">{devengado ? "Ejecución acumulada de la partida (Bs)" : "Ejecución acumulada al devengar (Bs)"}</Th><Th className="text-right">Saldo disponible (Bs)</Th></tr></thead>
            <tbody>{filasEjecucion.map(({ p, pa }) => (
              <tr key={p.partida_id}>
                <Td className="num whitespace-nowrap">{pa ? `${pa.programa}-${pa.proyecto}-${pa.actividad}` : "—"}</Td>
                <Td className="num">{pa ? `${pa.fuente}/${pa.organismo}` : "—"}</Td>
                <Td><span className="num font-medium">{p.codigo_partida}</span> {p.descripcion}</Td>
                <Td className="num text-right">{pa ? bs(pa.monto_aprobado) : "—"}</Td>
                <Td className="num text-right">{bs(p.importe)}</Td>
                <Td className="num text-right">{pa ? bs(devengado ? pa.monto_ejecutado : Number(pa.monto_ejecutado) + aDevengar(p.importe)) : "—"}</Td>
                <Td className="num text-right font-semibold">{pa ? bs(pa.saldo_disponible) : "—"}</Td>
              </tr>
            ))}</tbody>
            <tfoot>
              <tr><Td colSpan={3} className="text-right font-semibold">TOTAL</Td>
                <Td className="num text-right font-bold">{bs(filasEjecucion.reduce((a, { pa }) => a + Number(pa?.monto_aprobado ?? 0), 0))}</Td>
                <Td className="num text-right font-bold">{bs(totReservado)}</Td>
                <Td className="num text-right font-bold">{bs(filasEjecucion.reduce((a, { p, pa }) => a + Number(pa?.monto_ejecutado ?? 0) + (devengado ? 0 : aDevengar(p.importe)), 0))}</Td>
                <Td className="num text-right font-bold">{bs(filasEjecucion.reduce((a, { pa }) => a + Number(pa?.saldo_disponible ?? 0), 0))}</Td></tr>
            </tfoot>
          </Tabla>
          <CardBody className="grid gap-2 text-sm sm:grid-cols-3">
            {devengado ? (
              <>
                <div><span className="text-xs text-slate-500">Total ejecución cargada (devengado)</span><p className="num text-lg font-bold text-emerald-700">Bs {bs(totReservado)}</p></div>
                <div><span className="text-xs text-slate-500">Monto adjudicado</span><p className="num text-lg font-semibold">Bs {bs(montoAdj)}</p></div>
                <div><span className="text-xs text-slate-500">Saldo liberado al presupuesto</span><p className="num text-lg font-semibold">Bs {bs(Math.max(0, Number(c.monto_referencial_total) - totReservado))}</p></div>
              </>
            ) : (
              <>
                <div><span className="text-xs text-slate-500">Reservado en el preventivo</span><p className="num text-lg font-semibold">Bs {bs(totReservado)}</p></div>
                <div><span className="text-xs text-slate-500">Se devengará (monto adjudicado)</span><p className="num text-lg font-bold text-emerald-700">Bs {bs(montoAdj)}</p></div>
                <div><span className="text-xs text-slate-500">Se liberará al presupuesto</span><p className="num text-lg font-semibold">Bs {bs(Math.max(0, totReservado - montoAdj))}</p></div>
              </>
            )}
          </CardBody>
        </Card>
      )}

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

      <Card>
        <CardHeader><CardTitle>Certificación del POA — programa y objetivo</CardTitle>
          {c.documentos.some((d) => d.tipo_doc === "CERTIFICACION_POA") && <Badge className="bg-emerald-100 text-emerald-800 ring-emerald-300">Certificación POA emitida</Badge>}</CardHeader>
        <CardBody className="space-y-3">
          <Tabla aria-label="Programas y objetivos del POA">
            <thead><tr><Th>Programa</Th><Th>Denominación</Th><Th>Partidas</Th><Th>Objetivo POA</Th><Th className="text-right">Monto (Bs)</Th></tr></thead>
            <tbody>{programas.map((p) => (
              <tr key={p.programa}><Td className="num">{p.programa}</Td><Td>{p.denominacion_programa}</Td><Td className="num">{p.partidas.join(", ")}</Td>
                <Td>{p.objetivo_registrado ? <><b>{p.codigo_objetivo}</b> — {p.descripcion_objetivo}</> : <Badge className="bg-red-100 text-red-800 ring-red-300">Sin objetivo registrado</Badge>}</Td>
                <Td className="num text-right">{bs(p.monto)}</Td></tr>
            ))}</tbody>
          </Tabla>
          {faltanObjetivos && <Alert tipo="error">Hay programas sin objetivo del POA: regístrelo o impórtelo en el menú «Objetivos POA» antes de certificar.</Alert>}
          {verificable && puedeOperar ? (
            <Field label="Justificación del apoyo de la compra al logro del objetivo del POA" hint="Mínimo 20 caracteres. Se imprime en la Certificación del POA">
              <Textarea value={justPoa} onChange={(e) => setJustPoa(e.target.value)} className="min-h-[90px]" />
            </Field>
          ) : (
            <div><p className="text-xs font-medium text-slate-500">Justificación del apoyo al objetivo del POA</p><p className="whitespace-pre-line text-sm">{c.justificacion_poa || "—"}</p></div>
          )}
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
                <Button variant="success" disabled={faltanObjetivos} cargando={cargando === "certificar"}
                  onClick={() => { limpiar(); void ejecutar("certificar", () => api.post(`/contrataciones/${c.id}/certificar`, { preventivo_c31_nro: c31.trim() || null, justificacion_poa: justPoa.trim() || null }), "Presupuesto certificado y saldo descontado"); }}>
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
