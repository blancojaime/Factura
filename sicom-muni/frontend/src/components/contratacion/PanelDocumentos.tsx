"use client";

import { Copy, ExternalLink, FileDown } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Alert, Button, Card, CardHeader, CardTitle, Tabla, Td, Th } from "@/components/ui";
import { api, mensajeError } from "@/lib/api";
import { fechaHora, TIPO_DOC_LABEL } from "@/lib/format";
import type { Contratacion } from "@/lib/tipos";

export default function PanelDocumentos({ c }: { c: Contratacion }) {
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState<string | null>(null);

  async function abrir(docId: string) {
    setError("");
    setCargando(docId);
    try {
      const blob = await api.blob(`/contrataciones/${c.id}/documentos/${docId}/descargar`);
      window.open(URL.createObjectURL(blob), "_blank", "noopener");
    } catch (e) {
      setError(mensajeError(e));
    } finally {
      setCargando(null);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Expediente digital ({c.documentos.length})</CardTitle>
        <span className="text-xs text-slate-500">Cada PDF lleva membrete, marca de agua de estado, QR de verificación y hash SHA-256</span></CardHeader>
      {error && <div className="p-4"><Alert tipo="error">{error}</Alert></div>}
      <Tabla aria-label="Documentos del expediente">
        <thead><tr><Th>Documento</Th><Th>Versión</Th><Th>Generado</Th><Th>Estado al generar</Th><Th>SHA-256 (archivo)</Th><Th /></tr></thead>
        <tbody>
          {c.documentos.length === 0 && <tr><Td colSpan={6} className="py-6 text-center text-slate-500">Aún no hay documentos.</Td></tr>}
          {c.documentos.map((d) => (
            <tr key={d.id}>
              <Td className="font-medium">{TIPO_DOC_LABEL[d.tipo_doc] ?? d.tipo_doc}</Td><Td>v{d.version}</Td>
              <Td className="whitespace-nowrap">{fechaHora(d.fecha_generacion)}</Td><Td>{d.estado_tramite.replace(/_/g, " ")}</Td>
              <Td><button className="inline-flex items-center gap-1 font-mono text-xs text-slate-600 hover:text-brand-700" title="Copiar hash completo" onClick={() => navigator.clipboard.writeText(d.hash_sha256)}>
                {d.hash_sha256.slice(0, 16)}… <Copy className="h-3 w-3" aria-hidden /></button></Td>
              <Td><div className="flex gap-2">
                <Button size="sm" variant="outline" cargando={cargando === d.id} onClick={() => abrir(d.id)}><FileDown className="h-4 w-4" aria-hidden /> Ver PDF</Button>
                <Link href={`/verificar/${d.id}`} target="_blank" className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-xs text-brand-700 hover:bg-brand-50"><ExternalLink className="h-3 w-3" aria-hidden /> Verificar</Link>
              </div></Td>
            </tr>
          ))}
        </tbody>
      </Tabla>
    </Card>
  );
}
