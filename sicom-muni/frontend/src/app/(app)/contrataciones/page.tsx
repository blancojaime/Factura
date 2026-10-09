"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import EstadoBadge from "@/components/EstadoBadge";
import { Alert, Card, CardBody, Cargando, Input, Select, Tabla, Td, Th } from "@/components/ui";
import { api, mensajeError } from "@/lib/api";
import { bs, ESTADO_LABEL, ESTADOS, fecha, METODO_LABEL, TIPO_OBJETO_LABEL } from "@/lib/format";
import type { Resumen } from "@/lib/tipos";

function Lista() {
  const params = useSearchParams();
  const [estado, setEstado] = useState(params.get("estado") ?? "");
  const [q, setQ] = useState("");
  const [filas, setFilas] = useState<Resumen[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      const qs = new URLSearchParams();
      if (estado) qs.set("estado", estado);
      if (q.trim()) qs.set("q", q.trim());
      api.get<Resumen[]>(`/contrataciones?${qs}`).then(setFilas).catch((e) => setError(mensajeError(e)));
    }, 250);
    return () => clearTimeout(t);
  }, [estado, q]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-brand-900">Contrataciones menores</h1>
      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-[1fr_16rem]">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" aria-hidden />
            <Input className="pl-9" placeholder="Buscar por número u objeto…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar" />
          </div>
          <Select value={estado} onChange={(e) => setEstado(e.target.value)} aria-label="Estado">
            <option value="">Todos los estados</option>
            {ESTADOS.map((e) => <option key={e} value={e}>{ESTADO_LABEL[e]}</option>)}
          </Select>
        </CardBody>
      </Card>
      {error && <Alert tipo="error">{error}</Alert>}
      {!filas && !error && <Cargando />}
      {filas && (
        <Card>
          {filas.length === 0 ? (
            <CardBody><p className="text-sm text-slate-500">No hay contrataciones con esos criterios.</p></CardBody>
          ) : (
            <Tabla>
              <thead><tr><Th>N°</Th><Th>Objeto</Th><Th>Tipo</Th><Th className="text-right">Monto (Bs)</Th><Th>Plazo</Th><Th>Formalización</Th><Th>Estado</Th><Th>Creado</Th></tr></thead>
              <tbody>
                {filas.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <Td className="font-medium"><Link className="text-brand-700 hover:underline" href={`/contrataciones/${c.id}`}>{c.correlativo_interno}</Link></Td>
                    <Td className="max-w-sm">{c.objeto_contratacion}</Td>
                    <Td>{TIPO_OBJETO_LABEL[c.tipo_objeto]}</Td>
                    <Td className="num text-right">{bs(c.monto_referencial_total)}</Td>
                    <Td>{c.plazo_dias_calendario} d</Td>
                    <Td>{c.metodo_formalizacion ? METODO_LABEL[c.metodo_formalizacion] : "—"}</Td>
                    <Td><EstadoBadge estado={c.estado} /></Td>
                    <Td className="whitespace-nowrap text-slate-500">{fecha(c.created_at)}</Td>
                  </tr>
                ))}
              </tbody>
            </Tabla>
          )}
        </Card>
      )}
    </div>
  );
}

export default function ContratacionesPage() {
  return <Suspense fallback={<Cargando />}><Lista /></Suspense>;
}
