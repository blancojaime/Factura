"use client";

import { ShieldCheck, ShieldX } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Cargando, Input, Tabla, Td, Th } from "@/components/ui";
import { api, mensajeError } from "@/lib/api";
import { fechaHora } from "@/lib/format";
import type { AuditoriaFila } from "@/lib/tipos";

export default function AuditoriaPage() {
  const [filas, setFilas] = useState<AuditoriaFila[] | null>(null);
  const [accion, setAccion] = useState("");
  const [verif, setVerif] = useState<{ ok: boolean; total: number; primera_ruptura: number | null } | null>(null);
  const [error, setError] = useState("");
  const [abierta, setAbierta] = useState<number | null>(null);

  const cargar = useCallback(() => {
    const qs = new URLSearchParams({ limite: "200" });
    if (accion.trim()) qs.set("accion", accion.trim().toUpperCase());
    return api.get<AuditoriaFila[]>(`/admin/auditoria?${qs}`).then(setFilas).catch((e) => setError(mensajeError(e)));
  }, [accion]);
  useEffect(() => { const t = setTimeout(() => void cargar(), 250); return () => clearTimeout(t); }, [cargar]);

  async function verificar() {
    setError("");
    try { setVerif(await api.get("/admin/auditoria/verificar")); } catch (e) { setError(mensajeError(e)); }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-brand-900">Auditoría (Audit Trail inalterable)</h1>
      <Card>
        <CardBody className="flex flex-wrap items-center gap-3">
          <Button variant="outline" onClick={verificar}><ShieldCheck className="h-4 w-4" aria-hidden /> Verificar integridad de la cadena</Button>
          {verif && (verif.ok
            ? <span className="flex items-center gap-1 text-sm font-medium text-emerald-700"><ShieldCheck className="h-4 w-4" aria-hidden /> Cadena íntegra: {verif.total} registros verificados</span>
            : <span className="flex items-center gap-1 text-sm font-medium text-red-700"><ShieldX className="h-4 w-4" aria-hidden /> Se detectó alteración desde el registro N° {verif.primera_ruptura}</span>)}
          <Input className="ml-auto w-64" placeholder="Filtrar por acción (ej. ADJUDICADO)" value={accion} onChange={(e) => setAccion(e.target.value)} aria-label="Filtrar por acción" />
        </CardBody>
      </Card>
      {error && <Alert tipo="error">{error}</Alert>}
      {!filas && !error && <Cargando />}
      {filas && (
        <Card>
          <CardHeader><CardTitle>Últimos registros</CardTitle><span className="text-xs text-slate-500">Cada fila encadena el hash SHA-256 de la anterior</span></CardHeader>
          <Tabla aria-label="Registros de auditoría">
            <thead><tr><Th>N°</Th><Th>Fecha y hora</Th><Th>Acción</Th><Th>Tabla</Th><Th>IP</Th><Th>Hash</Th><Th /></tr></thead>
            <tbody>{filas.map((f) => (
              <>
                <tr key={f.secuencia}><Td className="num">{f.secuencia}</Td><Td className="whitespace-nowrap">{fechaHora(f.timestamp)}</Td><Td className="font-medium">{f.accion}</Td><Td>{f.tabla_afectada}</Td>
                  <Td className="num">{f.ip}</Td><Td className="font-mono text-xs text-slate-500">{f.hash_registro.slice(0, 12)}…</Td>
                  <Td><button className="text-xs text-brand-700 hover:underline" onClick={() => setAbierta(abierta === f.secuencia ? null : f.secuencia)}>{abierta === f.secuencia ? "Ocultar" : "Detalle"}</button></Td></tr>
                {abierta === f.secuencia && <tr key={`${f.secuencia}d`}><Td colSpan={7} className="bg-slate-50"><pre className="max-h-64 overflow-auto text-xs">{JSON.stringify({ previos: f.datos_previos, nuevos: f.datos_nuevos, registro: f.registro_id }, null, 2)}</pre></Td></tr>}
              </>
            ))}</tbody>
          </Tabla>
        </Card>
      )}
    </div>
  );
}
