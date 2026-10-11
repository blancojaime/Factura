"use client";

import { ShieldCheck, ShieldX } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Alert, Card, CardBody, CardHeader, CardTitle, Cargando } from "@/components/ui";
import { api, mensajeError } from "@/lib/api";
import { fechaHora, TIPO_DOC_LABEL } from "@/lib/format";

interface Ficha {
  documento_id: string; tipo_doc: string; version: number; tramite: string; objeto: string; estado_tramite_al_generar: string;
  estado_tramite_actual: string; fecha_generacion: string; hash_sha256_archivo: string; hash_sha256_contenido: string;
  vigente: boolean; hash_sha256_cargado?: string; coincide?: boolean;
}

/** Pagina publica a la que apunta el QR de cada PDF: confirma que el documento existe y permite comprobar el archivo. */
export default function VerificarPage() {
  const { id } = useParams<{ id: string }>();
  const [f, setF] = useState<Ficha | null>(null);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState<Ficha | null>(null);

  useEffect(() => {
    api.publico<Ficha>(`/verificar/${id}`).then(setF).catch((e) => setError(mensajeError(e)));
  }, [id]);

  async function comprobar(archivo: File | undefined) {
    if (!archivo) return;
    const fd = new FormData();
    fd.append("archivo", archivo);
    setError("");
    try { setResultado(await api.publico<Ficha>(`/verificar/${id}/archivo`, { method: "POST", body: fd })); } catch (e) { setError(mensajeError(e)); }
  }

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4 md:p-8">
      <h1 className="text-2xl font-bold text-brand-900">Verificación de autenticidad</h1>
      {error && <Alert tipo="error">{error}</Alert>}
      {!f && !error && <Cargando />}
      {f && (
        <>
          <Alert tipo="success" titulo="Documento registrado en el expediente digital">Este documento fue emitido por el sistema SICOM-MUNI.</Alert>
          <Card>
            <CardHeader><CardTitle>{TIPO_DOC_LABEL[f.tipo_doc] ?? f.tipo_doc} — versión {f.version}</CardTitle></CardHeader>
            <CardBody className="space-y-2 text-sm">
              <p><b>Trámite:</b> {f.tramite} — {f.objeto}</p>
              <p><b>Generado:</b> {fechaHora(f.fecha_generacion)} (estado del trámite: {f.estado_tramite_al_generar.replace(/_/g, " ")})</p>
              <p><b>Estado actual del trámite:</b> {f.estado_tramite_actual.replace(/_/g, " ")}</p>
              <p>{f.vigente ? "Es la versión vigente de este documento." : <span className="font-medium text-amber-700">Existe una versión más reciente de este documento.</span>}</p>
              <p className="break-all"><b>SHA-256 del archivo:</b> <code className="text-xs">{f.hash_sha256_archivo}</code></p>
              <p className="break-all"><b>SHA-256 del contenido (impreso al pie):</b> <code className="text-xs">{f.hash_sha256_contenido}</code></p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader><CardTitle>Comprobar un archivo PDF</CardTitle></CardHeader>
            <CardBody className="space-y-3">
              <p className="text-sm text-slate-600">Cargue el PDF que recibió: se calcula su SHA-256 y se compara con el registrado. El archivo no se almacena.</p>
              <input type="file" accept="application/pdf" onChange={(e) => comprobar(e.target.files?.[0])} aria-label="Archivo PDF a comprobar" />
              {resultado && (resultado.coincide
                ? <Alert tipo="success" titulo="El archivo es auténtico"><span className="inline-flex items-center gap-1"><ShieldCheck className="h-4 w-4" aria-hidden /> Coincide exactamente con el documento emitido.</span></Alert>
                : <Alert tipo="error" titulo="El archivo NO coincide"><span className="inline-flex items-center gap-1"><ShieldX className="h-4 w-4" aria-hidden /> Fue alterado o no corresponde a este documento.</span><code className="mt-1 block break-all text-xs">{resultado.hash_sha256_cargado}</code></Alert>)}
            </CardBody>
          </Card>
        </>
      )}
    </main>
  );
}
