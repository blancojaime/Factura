"use client";

import { Check, Copy, KeyRound, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Badge, Button, Card, CardBody, CardHeader, CardTitle, Cargando, Field, Textarea } from "@/components/ui";
import { ApiError, api, mensajeError } from "@/lib/api";
import { fecha } from "@/lib/format";
import type { EstadoLicencia } from "@/lib/tipos";

const MODO: Record<EstadoLicencia["modo"], { texto: string; clase: string }> = {
  LICENCIADA: { texto: "Licencia activa", clase: "bg-emerald-100 text-emerald-800 ring-emerald-300" },
  PRUEBA: { texto: "Modo de prueba", clase: "bg-amber-100 text-amber-800 ring-amber-300" },
  PRUEBA_VENCIDA: { texto: "Prueba terminada", clase: "bg-red-100 text-red-800 ring-red-300" },
  VENCIDA: { texto: "Licencia vencida", clase: "bg-red-100 text-red-800 ring-red-300" },
  NO_REQUERIDA: { texto: "Sin licencia obligatoria", clase: "bg-slate-100 text-slate-700 ring-slate-300" },
};

/** Muestra el ID del equipo y el estado de la licencia, y permite activar una licencia (archivo .sicomlic o clave SICOM1-…). */
export default function PanelLicencia({ alActivar }: { alActivar?: (e: EstadoLicencia) => void }) {
  const [e, setE] = useState<EstadoLicencia | null>(null);
  const [error, setError] = useState("");
  const [texto, setTexto] = useState("");
  const [ok, setOk] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const entrada = useRef<HTMLInputElement>(null);

  const cargar = useCallback(() => api.publico<EstadoLicencia>("/licencia").then(setE).catch((x) => setError(mensajeError(x))), []);
  useEffect(() => { void cargar(); }, [cargar]);

  async function activar() {
    setError(""); setOk(""); setEnviando(true);
    try {
      const nuevo = await api.publico<EstadoLicencia>("/licencia", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ texto }),
      });
      setE(nuevo); setTexto(""); setOk(`Licencia activada para «${nuevo.entidad}»`);
      alActivar?.(nuevo);
    } catch (x) { setError(x instanceof ApiError ? x.message : mensajeError(x)); } finally { setEnviando(false); }
  }

  function leerArchivo(f: File | undefined) {
    if (!f) return;
    const r = new FileReader();
    r.onload = () => setTexto(String(r.result ?? ""));
    r.readAsText(f);
  }

  async function copiar() {
    if (!e) return;
    await navigator.clipboard.writeText(e.id_equipo).catch(() => undefined);
    setCopiado(true); setTimeout(() => setCopiado(false), 2000);
  }

  if (!e) return error ? <Alert tipo="error">{error}</Alert> : <Cargando />;
  const m = MODO[e.modo];
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Estado de la licencia</CardTitle><Badge className={m.clase}>{m.texto}</Badge></CardHeader>
        <CardBody className="space-y-3 text-sm">
          <Alert tipo={e.operativo ? "info" : "error"}>{e.mensaje}</Alert>
          <dl className="grid gap-3 sm:grid-cols-2">
            <div><dt className="text-xs text-slate-500">ID de este equipo (envíelo para solicitar la licencia)</dt>
              <dd className="mt-1 flex items-center gap-2"><code className="rounded bg-slate-100 px-2 py-1 text-base font-semibold tracking-wider">{e.id_equipo}</code>
                <Button size="sm" variant="outline" onClick={copiar}>{copiado ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />} {copiado ? "Copiado" : "Copiar"}</Button></dd></div>
            {e.entidad && <div><dt className="text-xs text-slate-500">Entidad licenciada</dt><dd className="mt-1 font-medium">{e.entidad}</dd></div>}
            {e.modo === "LICENCIADA" && <div><dt className="text-xs text-slate-500">Vencimiento</dt><dd className="mt-1">{e.vence ? `${fecha(e.vence)} (${e.dias_restantes} días)` : "Sin vencimiento"}</dd></div>}
            {e.modo === "LICENCIADA" && <div><dt className="text-xs text-slate-500">Usuarios permitidos</dt><dd className="mt-1">{e.max_usuarios ?? "Sin límite"}</dd></div>}
            {e.modo === "PRUEBA" && <div><dt className="text-xs text-slate-500">Días de prueba restantes</dt><dd className="mt-1 font-medium">{e.dias_restantes}</dd></div>}
          </dl>
        </CardBody>
      </Card>
      <Card>
        <CardHeader><CardTitle>Activar una licencia</CardTitle></CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-slate-600">Cargue el archivo <b>.sicomlic</b> que recibió o pegue la <b>clave de activación</b> (empieza con <code>SICOM1-</code>).</p>
          <div className="flex flex-wrap items-center gap-3">
            <input ref={entrada} type="file" accept=".sicomlic,.json,.txt" aria-label="Archivo de licencia" onChange={(ev) => leerArchivo(ev.target.files?.[0])} />
            <span className="text-xs text-slate-500">o pegue la clave:</span>
          </div>
          <Field label="Clave de activación o contenido de la licencia"><Textarea value={texto} onChange={(ev) => setTexto(ev.target.value)} className="min-h-[90px] font-mono text-xs" /></Field>
          {error && <Alert tipo="error">{error}</Alert>}
          {ok && <Alert tipo="success">{ok}</Alert>}
          <Button disabled={texto.trim().length < 20} cargando={enviando} onClick={activar}><KeyRound className="h-4 w-4" aria-hidden /> Activar licencia</Button>
          {texto && <button className="ml-3 text-xs text-slate-500 hover:underline" onClick={() => { setTexto(""); if (entrada.current) entrada.current.value = ""; }}><Upload className="mr-1 inline h-3 w-3" aria-hidden />Limpiar</button>}
        </CardBody>
      </Card>
    </div>
  );
}
