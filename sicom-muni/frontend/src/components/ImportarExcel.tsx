"use client";

import { Download, FileSpreadsheet, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { ErrorApi } from "@/components/contratacion/comun";
import { Alert, Button, Dialog, Tabla, Td, Th } from "@/components/ui";
import { ApiError, api, descargarPlantilla, mensajeError } from "@/lib/api";
import type { ResultadoImportacion } from "@/lib/tipos";

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  titulo: string;
  /** Ruta del endpoint de importacion (sin query), p. ej. "/partidas/importar". */
  ruta: string;
  /** Parametros fijos de la query (gestion, etc.). */
  query?: Record<string, string>;
  plantilla: "presupuesto" | "chb" | "poa";
  columnas: string[];
  nota?: string;
  onHecho: (r: ResultadoImportacion) => void;
}

/** Importacion en dos pasos: 1) validar el archivo y ver el resumen; 2) confirmar (todo o nada). */
export default function ImportarExcel({ abierto, onCerrar, titulo, ruta, query = {}, plantilla, columnas, nota, onHecho }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [previa, setPrevia] = useState<ResultadoImportacion | null>(null);
  const [hecho, setHecho] = useState<ResultadoImportacion | null>(null);
  const [error, setError] = useState<ApiError | string | null>(null);
  const [cargando, setCargando] = useState<"validar" | "confirmar" | null>(null);
  const entrada = useRef<HTMLInputElement>(null);

  function reiniciar() {
    setArchivo(null); setPrevia(null); setHecho(null); setError(null);
    if (entrada.current) entrada.current.value = "";
  }
  function cerrar() { reiniciar(); onCerrar(); }

  async function enviar(confirmar: boolean) {
    if (!archivo) return;
    setError(null);
    setCargando(confirmar ? "confirmar" : "validar");
    try {
      const fd = new FormData();
      fd.append("archivo", archivo);
      const qs = new URLSearchParams({ ...query, confirmar: String(confirmar) });
      const r = await api.subir<ResultadoImportacion>(`${ruta}?${qs}`, fd);
      if (confirmar) { setHecho(r); onHecho(r); } else setPrevia(r);
    } catch (e) {
      setError(e instanceof ApiError ? e : mensajeError(e));
    } finally {
      setCargando(null);
    }
  }

  const res = hecho ?? previa;
  return (
    <Dialog abierto={abierto} onCerrar={cerrar} titulo={titulo} ancho="max-w-3xl">
      <div className="space-y-4">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
          <p className="font-medium">Columnas que debe tener la hoja de Excel (.xlsx):</p>
          <p className="mt-1 text-slate-700">{columnas.join(" · ")}</p>
          {nota && <p className="mt-1 text-xs text-slate-500">{nota}</p>}
          <Button variant="outline" size="sm" className="mt-2" onClick={() => descargarPlantilla(plantilla).catch((e) => setError(mensajeError(e)))}>
            <Download className="h-4 w-4" aria-hidden /> Descargar plantilla de ejemplo
          </Button>
        </div>

        {!hecho && (
          <div className="flex flex-wrap items-center gap-3">
            <input ref={entrada} type="file" accept=".xlsx,.xlsm" aria-label="Archivo Excel a importar"
              onChange={(e) => { setArchivo(e.target.files?.[0] ?? null); setPrevia(null); setError(null); }} />
            <Button variant="outline" disabled={!archivo} cargando={cargando === "validar"} onClick={() => enviar(false)}>
              <FileSpreadsheet className="h-4 w-4" aria-hidden /> Validar archivo
            </Button>
          </div>
        )}

        <ErrorApi error={error} />

        {res && (
          <div className="space-y-3" aria-live="polite">
            {hecho
              ? <Alert tipo="success" titulo="Importación realizada">Se registraron {hecho.nuevas} nuevos y se actualizaron/reemplazaron {hecho.actualizadas}.</Alert>
              : res.errores.length === 0
                ? <Alert tipo="info" titulo="Archivo válido (aún no se guardó nada)">{res.total_filas} filas leídas: {res.nuevas} nuevas, {res.actualizadas} existentes que se actualizarán{res.omitidas ? `, ${res.omitidas} omitidas` : ""}.</Alert>
                : <Alert tipo="error" titulo={`Se encontraron ${res.errores.length} error(es): corrija el archivo y vuelva a validarlo`}>No se puede importar hasta que no haya errores.</Alert>}
            {res.omitidas > 0 && <p className="text-xs text-slate-500">Omitidas: partidas fuera del rango 10000–49999 (el sistema solo usa el clasificador 1xxxx a 4xxxx).</p>}
            {res.errores.length > 0 && (
              <Tabla aria-label="Errores del archivo">
                <thead><tr><Th>Fila</Th><Th>Error</Th></tr></thead>
                <tbody>{res.errores.slice(0, 30).map((e) => <tr key={e.fila + e.mensaje}><Td className="num">{e.fila}</Td><Td>{e.mensaje}</Td></tr>)}</tbody>
              </Tabla>
            )}
            {res.advertencias.length > 0 && (
              <Alert tipo="warning" titulo="Advertencias">
                <ul className="list-inside list-disc">{res.advertencias.slice(0, 10).map((a, i) => <li key={i}>{a}</li>)}</ul>
              </Alert>
            )}
            {res.muestra.length > 0 && (
              <div className="overflow-x-auto">
                <p className="mb-1 text-xs font-medium text-slate-500">Vista previa de las primeras filas válidas</p>
                <Tabla aria-label="Vista previa">
                  <thead><tr>{Object.keys(res.muestra[0]).map((k) => <Th key={k}>{k}</Th>)}</tr></thead>
                  <tbody>{res.muestra.map((m, i) => <tr key={i}>{Object.values(m).map((v, j) => <Td key={j} className="whitespace-nowrap">{v}</Td>)}</tr>)}</tbody>
                </Tabla>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={cerrar}>{hecho ? "Cerrar" : "Cancelar"}</Button>
          {!hecho && (
            <Button variant="success" disabled={!previa || previa.errores.length > 0 || previa.nuevas + previa.actualizadas === 0}
              cargando={cargando === "confirmar"} onClick={() => enviar(true)}>
              <Upload className="h-4 w-4" aria-hidden /> Confirmar importación
            </Button>
          )}
        </div>
      </div>
    </Dialog>
  );
}
