"use client";

import { Check } from "lucide-react";
import { useState } from "react";
import EstadoBadge from "@/components/EstadoBadge";
import { Alert, Badge, Button, Card, CardBody, Dialog, Field, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { SECUENCIA } from "@/lib/flujo";
import { bs, ESTADO_LABEL, METODO_LABEL, MODALIDAD_LABEL, TIPO_OBJETO_LABEL } from "@/lib/format";
import type { Contratacion } from "@/lib/tipos";
import { cn } from "@/lib/utils";
import { ErrorApi, useAccion } from "./comun";

export function LineaTiempo({ estado }: { estado: Contratacion["estado"] }) {
  const anulado = estado === "ANULADO";
  const idx = SECUENCIA.indexOf(estado);
  return (
    <ol className="flex gap-1 overflow-x-auto pb-1" aria-label="Avance del trámite">
      {SECUENCIA.map((e, i) => {
        const hecho = !anulado && i < idx;
        const actual = !anulado && i === idx;
        return (
          <li key={e} className="flex min-w-[88px] flex-1 flex-col items-center text-center" aria-current={actual ? "step" : undefined}>
            <span className={cn("flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ring-2",
              hecho && "bg-emerald-600 text-white ring-emerald-600", actual && "bg-brand-700 text-white ring-brand-700",
              !hecho && !actual && "bg-white text-slate-400 ring-slate-300")}>
              {hecho ? <Check className="h-4 w-4" aria-hidden /> : i + 1}
            </span>
            <span className={cn("mt-1 text-[11px] leading-tight", actual ? "font-semibold text-brand-700" : "text-slate-500")}>{ESTADO_LABEL[e]}</span>
          </li>
        );
      })}
    </ol>
  );
}

export default function Cabecera({ c, recargar }: { c: Contratacion; recargar: () => Promise<void> }) {
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const { ejecutar, cargando, error, limpiar } = useAccion(recargar);
  const puedeAnular = c.acciones.includes("anular");

  return (
    <div className="space-y-4">
      <Card>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold text-brand-900">{c.correlativo_interno}</h1>
                <EstadoBadge estado={c.estado} />
              </div>
              <p className="mt-1 max-w-3xl text-sm text-slate-700">{c.objeto_contratacion}</p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                <Badge className="bg-slate-100 text-slate-700 ring-slate-300">{TIPO_OBJETO_LABEL[c.tipo_objeto]}</Badge>
                <Badge className="bg-slate-100 text-slate-700 ring-slate-300">{c.plazo_dias_calendario} días calendario</Badge>
                {c.modalidad_cuantia && <Badge className="bg-sky-50 text-sky-800 ring-sky-200">{MODALIDAD_LABEL[c.modalidad_cuantia]}</Badge>}
                {c.metodo_formalizacion && <Badge className="bg-violet-50 text-violet-800 ring-violet-200">{METODO_LABEL[c.metodo_formalizacion]}</Badge>}
                {c.requiere_excepcion_chb && <Badge className="bg-amber-50 text-amber-800 ring-amber-300">Excepción CHB</Badge>}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500">Monto referencial</div>
              <div className="num text-2xl font-bold text-brand-900">Bs {bs(c.monto_referencial_total)}</div>
              {puedeAnular && <Button variant="outline" size="sm" className="mt-2" onClick={() => { limpiar(); setAbierto(true); }}>Anular trámite</Button>}
            </div>
          </div>
          <LineaTiempo estado={c.estado} />
        </CardBody>
      </Card>
      {c.ultima_observacion && <Alert tipo="warning" titulo="Observación">{c.ultima_observacion}</Alert>}
      {c.motivo_cierre && <Alert tipo="error" titulo="Trámite cerrado">{c.motivo_cierre}</Alert>}

      <Dialog abierto={abierto} onCerrar={() => setAbierto(false)} titulo="Anular el trámite">
        <div className="space-y-4">
          <Alert tipo="warning">Esta acción libera el saldo presupuestario reservado y no puede deshacerse.</Alert>
          <Field label="Motivo (mínimo 10 caracteres)"><Textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} /></Field>
          <ErrorApi error={error} />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setAbierto(false)}>Cancelar</Button>
            <Button variant="danger" cargando={cargando === "anular"} disabled={motivo.trim().length < 10}
              onClick={async () => { if (await ejecutar("anular", () => api.post(`/contrataciones/${c.id}/anular`, { motivo }))) setAbierto(false); }}>
              Anular
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
