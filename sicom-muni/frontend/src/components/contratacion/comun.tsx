"use client";

import { useCallback, useState, type ReactNode } from "react";
import { Alert } from "@/components/ui";
import { ApiError, mensajeError } from "@/lib/api";

export function ErrorApi({ error }: { error: ApiError | string | null }) {
  if (!error) return null;
  if (typeof error === "string") return <Alert tipo="error">{error}</Alert>;
  return (
    <Alert tipo="error" titulo={error.message}>
      {error.errores.length > 0 && (
        <ul className="list-inside list-disc space-y-0.5">{error.errores.map((m, i) => <li key={i}>{m}</li>)}</ul>
      )}
    </Alert>
  );
}

/** Ejecuta una accion contra la API, muestra el error y recarga el tramite al terminar. */
export function useAccion(recargar: () => Promise<void>) {
  const [cargando, setCargando] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | string | null>(null);
  const [ok, setOk] = useState("");

  const ejecutar = useCallback(
    async (clave: string, fn: () => Promise<unknown>, mensajeOk = "") => {
      setError(null);
      setOk("");
      setCargando(clave);
      try {
        await fn();
        await recargar();
        if (mensajeOk) setOk(mensajeOk);
        return true;
      } catch (e) {
        setError(e instanceof ApiError ? e : mensajeError(e));
        return false;
      } finally {
        setCargando(null);
      }
    },
    [recargar],
  );
  return { cargando, error, ok, ejecutar, limpiar: () => { setError(null); setOk(""); } };
}

export function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{etiqueta}</dt>
      <dd className="mt-0.5 text-sm text-slate-900">{children || "—"}</dd>
    </div>
  );
}

export interface Ctx {
  recargar: () => Promise<void>;
}
