"use client";

import { Lock, Mail, MessageCircle, Printer, Send, Trophy } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Alert, Badge, Button, Card, CardBody, CardHeader, CardTitle, Dialog, Field, Input, Select, Tabla, Td, Textarea, Th } from "@/components/ui";
import { api } from "@/lib/api";
import { bs, fechaHora } from "@/lib/format";
import type { Contratacion, Cotizacion, Evaluacion } from "@/lib/tipos";
import { cn } from "@/lib/utils";
import { ErrorApi, useAccion } from "./comun";

interface ResultadoFichas { documento_id: string; resultados: { razon_social: string; canales: Record<string, string> }[] }

function aLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** Fichas de cotizacion, Formulario 110, ofertas selladas, apertura (desencriptacion), calificacion y matriz comparativa. */
export default function PanelCotizaciones({ c, recargar, esContrataciones, esRpa }: {
  c: Contratacion; recargar: () => Promise<void>; esContrataciones: boolean; esRpa: boolean;
}) {
  const { ejecutar, cargando, error, ok, limpiar } = useAccion(recargar);
  const enCotizacion = c.estado === "EN_COTIZACION";
  const gestiona = esContrataciones && enCotizacion;
  const consulta = c.modalidad_cuantia === "CONSULTA_PRECIOS_SICOES";
  const [evalu, setEvalu] = useState<Evaluacion | null>(null);
  const [califica, setCalifica] = useState<Cotizacion | null>(null);
  const [fichas, setFichas] = useState(false);
  const [resFichas, setResFichas] = useState<ResultadoFichas | null>(null);
  const [adjId, setAdjId] = useState("");
  const [motivoAdj, setMotivoAdj] = useState("");
  const [desierto, setDesierto] = useState(false);
  const [motivoDes, setMotivoDes] = useState("");

  // matriz comparativa en vivo cuando las ofertas estan abiertas
  useEffect(() => {
    if (!c.ofertas_abiertas || !(esContrataciones || esRpa)) { setEvalu(null); return; }
    api.get<Evaluacion>(`/contrataciones/${c.id}/evaluacion`).then((e) => { setEvalu(e); setAdjId((a) => a || e.recomendada || ""); }).catch(() => setEvalu(null));
  }, [c.id, c.ofertas_abiertas, c.cotizaciones, esContrataciones, esRpa]);

  async function guardarF110(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await ejecutar("f110", () => api.put(`/contrataciones/${c.id}/formulario-110`, {
      nro_formulario_110: String(f.get("nro")).trim(), fecha_limite_ofertas: new Date(String(f.get("limite"))).toISOString(),
      cuce: String(f.get("cuce") ?? "").trim() || null }), "Formulario 110 registrado");
  }

  async function nuevaOferta(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const rec = String(f.get("recibida") ?? "");
    const exito = await ejecutar("oferta", () => api.post(`/contrataciones/${c.id}/cotizaciones`, {
      nit_ci: String(f.get("nit")).trim(), razon_social: String(f.get("razon")).trim(), correo: String(f.get("correo") ?? ""),
      telefono: String(f.get("tel") ?? ""), monto_total_ofertado: String(f.get("monto")), plazo_ofertado_dias: Number(f.get("plazo")),
      fecha_recepcion: rec ? new Date(rec).toISOString() : null }), "Oferta registrada y sellada");
    if (exito) form.reset();
  }

  async function enviarFichas(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const destinatarios = String(f.get("dest")).split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
      const [razon_social, correo = "", telefono = ""] = l.split(";").map((x) => x.trim());
      return { razon_social, correo, telefono };
    });
    const canales = ["IMPRESO", "EMAIL", "WHATSAPP"].filter((k) => f.get(k));
    let res: ResultadoFichas | null = null;
    const exito = await ejecutar("fichas", async () => { res = await api.post<ResultadoFichas>(`/contrataciones/${c.id}/fichas-cotizacion`, { destinatarios, canales }); });
    if (exito && res) setResFichas(res);
  }

  async function guardarCalificacion(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!califica) return;
    const f = new FormData(e.currentTarget);
    const registro = String(f.get("registro"));
    const exito = await ejecutar("califica", () => api.patch(`/contrataciones/${c.id}/cotizaciones/${califica.id}`, {
      cumple_especificaciones: f.get("cumple") === "on", observaciones: String(f.get("obs") ?? ""), registro_preferencia: registro,
      registro_preferencia_valido: registro !== "NINGUNO" && f.get("valido") === "on",
      margen_preferencia_pct: registro === "NINGUNO" ? "0" : String(f.get("margen") || "0") }));
    if (exito) setCalifica(null);
  }

  const minimo = consulta ? 3 : 1;
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader><CardTitle>Proceso de cotización</CardTitle>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge className="bg-sky-50 text-sky-800 ring-sky-200">{consulta ? "Consulta de precios SICOES" : "Compra directa"}</Badge>
            <Badge className="bg-slate-100 text-slate-700 ring-slate-300">Mínimo {minimo} cotización(es)</Badge>
            <Badge className={c.ofertas_abiertas ? "bg-emerald-100 text-emerald-800 ring-emerald-300" : "bg-amber-100 text-amber-800 ring-amber-300"}>
              {c.ofertas_abiertas ? "Ofertas abiertas" : "Ofertas selladas"}</Badge>
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          {consulta && !c.nro_formulario_110 && enCotizacion && <Alert tipo="warning" titulo="Formulario 110 requerido">Publique la Consulta de Precios en SICOES y registre el número de Formulario 110 antes de emitir fichas o cargar cotizaciones.</Alert>}
          {(c.nro_formulario_110 || !consulta) && (
            <dl className="grid gap-3 text-sm sm:grid-cols-3">
              <div><dt className="text-xs uppercase text-slate-500">N° Formulario 110</dt><dd className="font-medium">{c.nro_formulario_110 ?? "No aplica"}</dd></div>
              <div><dt className="text-xs uppercase text-slate-500">Plazo de presentación</dt><dd className="font-medium">{fechaHora(c.fecha_limite_ofertas)}</dd></div>
              <div><dt className="text-xs uppercase text-slate-500">CUCE</dt><dd className="font-medium">{c.cuce ?? "—"}</dd></div>
            </dl>
          )}
          {gestiona && !c.ofertas_abiertas && (
            <form onSubmit={guardarF110} className="grid gap-3 rounded-md border border-slate-200 p-4 sm:grid-cols-4" aria-label="Formulario 110">
              <Field label="N° Formulario 110"><Input name="nro" defaultValue={c.nro_formulario_110 ?? ""} required minLength={3} /></Field>
              <Field label="Fecha y hora límite de presentación"><Input name="limite" type="datetime-local" defaultValue={aLocalInput(c.fecha_limite_ofertas)} required /></Field>
              <Field label="CUCE (opcional)"><Input name="cuce" defaultValue={c.cuce ?? ""} /></Field>
              <div className="flex items-end"><Button type="submit" variant="outline" cargando={cargando === "f110"}>Registrar</Button></div>
            </form>
          )}
          {gestiona && !c.ofertas_abiertas && (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => { limpiar(); setResFichas(null); setFichas(true); }}><Send className="h-4 w-4" aria-hidden /> Emitir y enviar fichas de cotización</Button>
            </div>
          )}
          {ok && <Alert tipo="success">{ok}</Alert>}
          <ErrorApi error={error} />
        </CardBody>
      </Card>

      {gestiona && !c.ofertas_abiertas && (
        <form onSubmit={nuevaOferta} aria-label="Registrar oferta">
          <Card>
            <CardHeader><CardTitle>Registrar cotización (sobre sellado)</CardTitle><span className="text-xs text-slate-500">El monto se cifra y solo se ve al abrir las ofertas</span></CardHeader>
            <CardBody className="grid gap-3 sm:grid-cols-4">
              <Field label="NIT / CI"><Input name="nit" required pattern="[0-9A-Za-z-]{5,20}" /></Field>
              <Field label="Razón social" className="sm:col-span-2"><Input name="razon" required /></Field>
              <Field label="Monto total ofertado (Bs)"><Input name="monto" type="number" step="0.01" min="0.01" required /></Field>
              <Field label="Plazo ofertado (días)"><Input name="plazo" type="number" min={1} defaultValue={c.plazo_dias_calendario} required /></Field>
              <Field label="Correo"><Input name="correo" type="email" /></Field>
              <Field label="Teléfono"><Input name="tel" /></Field>
              <Field label="Recibida el (opcional)" hint="Fecha y hora de recepción; vacío = ahora"><Input name="recibida" type="datetime-local" /></Field>
              <div className="sm:col-span-4 flex justify-end"><Button type="submit" cargando={cargando === "oferta"}>Registrar cotización</Button></div>
            </CardBody>
          </Card>
        </form>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Cotizaciones recibidas ({c.cotizaciones.length})</CardTitle>
          {gestiona && !c.ofertas_abiertas && c.cotizaciones.length > 0 && (
            <Button size="sm" cargando={cargando === "abrir"} onClick={() => ejecutar("abrir", () => api.post(`/contrataciones/${c.id}/abrir-ofertas`), "Ofertas abiertas")}>Abrir ofertas</Button>
          )}
        </CardHeader>
        <Tabla aria-label="Cotizaciones">
          <thead><tr><Th>Proveedor</Th><Th>NIT/CI</Th><Th className="text-right">Monto (Bs)</Th><Th>Plazo</Th><Th>Recibida</Th><Th>Calificación</Th>{gestiona && c.ofertas_abiertas && <Th />}</tr></thead>
          <tbody>
            {c.cotizaciones.length === 0 && <tr><Td colSpan={7} className="py-6 text-center text-slate-500">Aún no hay cotizaciones.</Td></tr>}
            {c.cotizaciones.map((q) => (
              <tr key={q.id} className={cn(q.adjudicado && "bg-violet-50")}>
                <Td className="font-medium">{q.razon_social}{q.adjudicado && <Badge className="ml-2 bg-violet-100 text-violet-800 ring-violet-300">Adjudicada</Badge>}</Td>
                <Td className="num">{q.nit_ci}</Td>
                <Td className="num text-right">{q.sellada ? <span className="inline-flex items-center gap-1 text-slate-500"><Lock className="h-3 w-3" aria-hidden /> Sellada</span> : bs(q.monto_total_ofertado)}</Td>
                <Td>{q.plazo_ofertado_dias} d</Td><Td className="whitespace-nowrap text-slate-600">{fechaHora(q.fecha_recepcion)}</Td>
                <Td>{q.sellada ? "—" : (
                  <div className="space-y-0.5">
                    <Badge className={q.cumple_especificaciones ? "bg-emerald-100 text-emerald-800 ring-emerald-300" : "bg-red-100 text-red-800 ring-red-300"}>{q.cumple_especificaciones ? "Cumple" : "No cumple"}</Badge>
                    {q.registro_preferencia_valido && <div className="text-xs text-slate-600">{q.registro_preferencia} · margen {q.margen_preferencia_pct}%</div>}
                  </div>)}</Td>
                {gestiona && c.ofertas_abiertas && <Td><Button size="sm" variant="outline" onClick={() => { limpiar(); setCalifica(q); }}>Calificar</Button></Td>}
              </tr>
            ))}
          </tbody>
        </Tabla>
      </Card>

      {evalu && (
        <Card>
          <CardHeader><CardTitle>Matriz comparativa — Precio Evaluado Más Bajo</CardTitle>
            {evalu.hay_desempate && <Badge className="bg-amber-100 text-amber-800 ring-amber-300">Empate: gana la primera recepción</Badge>}</CardHeader>
          <Tabla aria-label="Matriz comparativa">
            <thead><tr><Th>Orden</Th><Th>Proveedor</Th><Th className="text-right">Monto (Bs)</Th><Th className="text-right">Margen pref. %</Th><Th className="text-right">Precio evaluado (Bs)</Th><Th>Plazo</Th><Th>Resultado</Th>{esRpa && c.estado === "EVALUADO" && <Th>Adjudicar a</Th>}</tr></thead>
            <tbody>{evalu.ofertas.map((o) => (
              <tr key={o.id} className={cn(o.recomendada && "bg-emerald-50", !o.elegible && "text-slate-400")}>
                <Td>{o.ranking ?? "—"}</Td>
                <Td className="font-medium">{o.recomendada && <Trophy className="mr-1 inline h-4 w-4 text-amber-500" aria-label="Recomendada" />}{o.razon_social}</Td>
                <Td className="num text-right">{bs(o.monto)}</Td><Td className="num text-right">{o.margen_aplicado_pct}</Td>
                <Td className="num text-right font-medium">{bs(o.precio_evaluado)}</Td><Td>{o.plazo_dias} d</Td>
                <Td>{o.recomendada ? <Badge className="bg-emerald-100 text-emerald-800 ring-emerald-300">Recomendada</Badge> : (o.motivo || "Calificada")}</Td>
                {esRpa && c.estado === "EVALUADO" && <Td>{o.elegible && <input type="radio" name="adj" aria-label={`Adjudicar a ${o.razon_social}`} checked={adjId === o.id} onChange={() => setAdjId(o.id)} />}</Td>}
              </tr>
            ))}</tbody>
          </Tabla>
          {gestiona && (
            <CardBody className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100">
              <p className="text-sm text-slate-600">Al evaluar se fija el ranking y se genera el Cuadro Comparativo y Acta de Calificación.</p>
              <Button variant="success" cargando={cargando === "evaluar"} onClick={() => ejecutar("evaluar", () => api.post(`/contrataciones/${c.id}/evaluar`), "Evaluación registrada")}>Evaluar y generar cuadro comparativo</Button>
            </CardBody>
          )}
        </Card>
      )}

      {esRpa && c.estado === "EVALUADO" && (
        <Card>
          <CardHeader><CardTitle>Asistente de adjudicación</CardTitle></CardHeader>
          <CardBody className="space-y-3">
            <p className="text-sm text-slate-700">Se recomienda adjudicar a la oferta de Precio Evaluado Más Bajo. Si elige otra oferta elegible debe fundamentar el motivo.</p>
            {evalu && adjId && adjId !== evalu.recomendada && (
              <Field label="Motivo de la adjudicación distinta de la recomendada"><Textarea value={motivoAdj} onChange={(e) => setMotivoAdj(e.target.value)} /></Field>
            )}
            <div className="flex flex-wrap gap-3">
              <Button variant="success" disabled={!adjId} cargando={cargando === "adjudicar"}
                onClick={() => ejecutar("adjudicar", () => api.post(`/contrataciones/${c.id}/adjudicar`, { cotizacion_id: adjId || null, motivo: motivoAdj }), "Adjudicado: se emitió la nota de adjudicación")}>Adjudicar</Button>
              <Button variant="danger" onClick={() => { limpiar(); setDesierto(true); }}>Declarar desierto</Button>
            </div>
          </CardBody>
        </Card>
      )}

      <Dialog abierto={desierto} onCerrar={() => setDesierto(false)} titulo="Declarar desierto el proceso">
        <div className="space-y-4">
          <Alert tipo="warning">Se cerrará el trámite y se libera el saldo presupuestario reservado.</Alert>
          <Field label="Motivo (mínimo 10 caracteres)"><Textarea value={motivoDes} onChange={(e) => setMotivoDes(e.target.value)} /></Field>
          <ErrorApi error={error} />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDesierto(false)}>Cancelar</Button>
            <Button variant="danger" disabled={motivoDes.trim().length < 10} cargando={cargando === "desierto"}
              onClick={async () => { if (await ejecutar("desierto", () => api.post(`/contrataciones/${c.id}/declarar-desierta`, { motivo: motivoDes }))) setDesierto(false); }}>Declarar desierto</Button>
          </div>
        </div>
      </Dialog>

      <Dialog abierto={!!califica} onCerrar={() => setCalifica(null)} titulo={`Calificar: ${califica?.razon_social ?? ""}`}>
        {califica && (
          <form onSubmit={guardarCalificacion} className="space-y-4">
            <label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="cumple" defaultChecked={califica.cumple_especificaciones} /> Cumple las especificaciones técnicas</label>
            <Field label="Registro de preferencia">
              <Select name="registro" defaultValue={califica.registro_preferencia}><option value="NINGUNO">Ninguno</option><option value="PRO_BOLIVIA">Pro-Bolivia</option><option value="MYPE">MyPE</option></Select>
            </Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="valido" defaultChecked={califica.registro_preferencia_valido} /> El registro es válido y vigente</label>
            <Field label="Margen de preferencia (%)" hint="Solo se aplica si el registro es válido"><Input name="margen" type="number" min={0} max={100} step="0.01" defaultValue={califica.margen_preferencia_pct} /></Field>
            <Field label="Observaciones"><Textarea name="obs" defaultValue={califica.observaciones} /></Field>
            <ErrorApi error={error} />
            <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setCalifica(null)}>Cancelar</Button><Button type="submit" cargando={cargando === "califica"}>Guardar calificación</Button></div>
          </form>
        )}
      </Dialog>

      <Dialog abierto={fichas} onCerrar={() => setFichas(false)} titulo="Emitir y enviar fichas de cotización" ancho="max-w-2xl">
        {resFichas ? (
          <div className="space-y-3">
            <Alert tipo="success" titulo="Fichas emitidas">Se generó la ficha en el expediente.</Alert>
            <ul className="space-y-2 text-sm">
              {resFichas.resultados.map((r) => (
                <li key={r.razon_social} className="rounded-md border border-slate-200 p-3">
                  <div className="font-medium">{r.razon_social}</div>
                  <div className="mt-1 flex flex-wrap gap-3">
                    {r.canales.EMAIL && <span className="inline-flex items-center gap-1"><Mail className="h-4 w-4" aria-hidden /> Correo: {r.canales.EMAIL === "ENVIADO" ? "enviado" : r.canales.EMAIL === "NO_CONFIGURADO" ? "SMTP no configurado" : r.canales.EMAIL}</span>}
                    {r.canales.WHATSAPP && (r.canales.WHATSAPP.startsWith("http") ? <a className="inline-flex items-center gap-1 text-emerald-700 underline" href={r.canales.WHATSAPP} target="_blank" rel="noreferrer"><MessageCircle className="h-4 w-4" aria-hidden /> Abrir WhatsApp</a> : <span>WhatsApp: sin teléfono</span>)}
                    {r.canales.IMPRESO && <span className="inline-flex items-center gap-1"><Printer className="h-4 w-4" aria-hidden /> Impresa (ver pestaña Documentos)</span>}
                  </div>
                </li>
              ))}
            </ul>
            <div className="flex justify-end"><Button onClick={() => setFichas(false)}>Cerrar</Button></div>
          </div>
        ) : (
          <form onSubmit={enviarFichas} className="space-y-4">
            <Field label="Proveedores invitados (uno por línea: Razón social; correo; teléfono)">
              <Textarea name="dest" required className="min-h-[120px] font-mono text-xs" placeholder={"ELECTRO SERVICIOS S.R.L.; ventas@electro.bo; 71234567"} />
            </Field>
            <fieldset className="flex flex-wrap gap-4 text-sm"><legend className="mb-1 text-sm font-medium text-slate-700">Canales</legend>
              <label className="flex items-center gap-2"><input type="checkbox" name="IMPRESO" defaultChecked /> Impreso</label>
              <label className="flex items-center gap-2"><input type="checkbox" name="EMAIL" /> Correo electrónico</label>
              <label className="flex items-center gap-2"><input type="checkbox" name="WHATSAPP" /> WhatsApp (enlace)</label>
            </fieldset>
            <ErrorApi error={error} />
            <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setFichas(false)}>Cancelar</Button><Button type="submit" cargando={cargando === "fichas"}>Emitir fichas</Button></div>
          </form>
        )}
      </Dialog>
    </div>
  );
}
