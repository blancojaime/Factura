"use client";

import { Lightbulb } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Textarea } from "@/components/ui";
import { api, ApiError, mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TIPO_OBJETO_LABEL } from "@/lib/format";
import { GUIA_ET } from "@/lib/guias";
import type { Contratacion, TipoObjeto } from "@/lib/tipos";

export default function NuevaPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [tipo, setTipo] = useState<TipoObjeto>("BIEN");
  const [error, setError] = useState<ApiError | string>("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setError("");
    setEnviando(true);
    try {
      const c = await api.post<Contratacion>("/contrataciones", {
        objeto_contratacion: String(f.get("objeto")).trim(), tipo_objeto: tipo,
        plazo_dias_calendario: Number(f.get("plazo")), unidad_solicitante: String(f.get("unidad")).trim(),
        justificacion: String(f.get("justificacion")).trim(), lugar_entrega: String(f.get("lugar")).trim(),
        especificaciones_tecnicas: String(f.get("et")).trim(),
      });
      router.push(`/contrataciones/${c.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err : mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  if (user && user.rol !== "ROL_SOLICITANTE") return <Alert tipo="warning">Solo la Unidad Solicitante puede crear solicitudes.</Alert>;
  const guia = GUIA_ET[tipo];
  return (
    <form onSubmit={enviar} className="mx-auto max-w-4xl space-y-5" aria-label="Nueva solicitud">
      <div>
        <h1 className="text-2xl font-bold text-brand-900">Nueva solicitud de contratación menor</h1>
        <p className="text-sm text-slate-600">Paso 1 de 2 — datos generales y especificaciones. En el siguiente paso agregará los ítems y consultará el Catálogo CHB.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Datos generales</CardTitle></CardHeader>
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Objeto de la contratación" className="sm:col-span-2" hint="Describa de forma clara y concreta qué se contrata">
            <Input name="objeto" required minLength={5} maxLength={400} placeholder="Ej.: Adquisición de material de construcción para mantenimiento de la plaza principal" />
          </Field>
          <Field label="Tipo de objeto">
            <Select value={tipo} onChange={(e) => setTipo(e.target.value as TipoObjeto)}>
              {Object.entries(TIPO_OBJETO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
          </Field>
          <Field label="Plazo de entrega / ejecución (días calendario)" hint="Hasta 15 días: Orden de Compra/Servicio. Más de 15: Contrato Administrativo">
            <Input name="plazo" type="number" min={1} max={3650} required defaultValue={10} />
          </Field>
          <Field label="Unidad solicitante"><Input name="unidad" required maxLength={160} defaultValue={user?.cargo ?? ""} /></Field>
          <Field label="Lugar de entrega / ejecución"><Input name="lugar" required maxLength={200} /></Field>
          <Field label="Justificación de la necesidad" className="sm:col-span-2">
            <Textarea name="justificacion" required minLength={10} placeholder="Indique la necesidad institucional y su vínculo con el POA/PAC" />
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader><CardTitle>{guia.titulo}</CardTitle></CardHeader>
        <CardBody className="space-y-3">
          <Alert tipo="info" titulo="Guía de redacción">
            <ul className="mt-1 list-inside list-disc space-y-0.5">{guia.puntos.map((p) => <li key={p}><Lightbulb className="mr-1 inline h-3 w-3" aria-hidden />{p}</li>)}</ul>
          </Alert>
          <Field label="Redacción (mínimo 20 caracteres)">
            <Textarea name="et" required minLength={20} className="min-h-[160px]" />
          </Field>
        </CardBody>
      </Card>

      {error && (
        <Alert tipo="error" titulo={typeof error === "string" ? undefined : error.message}>
          {typeof error === "string" ? error : error.errores.map((m) => <p key={m}>{m}</p>)}
        </Alert>
      )}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => router.push("/contrataciones")}>Cancelar</Button>
        <Button type="submit" cargando={enviando}>Guardar borrador y continuar</Button>
      </div>
    </form>
  );
}
