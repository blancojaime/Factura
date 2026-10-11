"use client";

import { ArrowRight, FilePlus2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import EstadoBadge from "@/components/EstadoBadge";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Cargando, Tabla, Td, Th } from "@/components/ui";
import { api, mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ACCION_PENDIENTE } from "@/lib/flujo";
import { bs, ESTADO_CLASE, ESTADO_LABEL, ESTADOS, fechaHora, ROL_LABEL } from "@/lib/format";
import type { Tablero } from "@/lib/tipos";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const { user } = useAuth();
  const [t, setT] = useState<Tablero | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Tablero>("/contrataciones/tablero").then(setT).catch((e) => setError(mensajeError(e)));
  }, []);

  if (!user) return null;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-brand-900">Hola, {user.nombre_completo.split(" ")[0]}</h1>
          <p className="text-sm text-slate-600">{ROL_LABEL[user.rol]} · {user.cargo}</p>
        </div>
        {user.rol === "ROL_SOLICITANTE" && (
          <Link href="/contrataciones/nueva">
            <Button><FilePlus2 className="h-4 w-4" aria-hidden /> Nueva solicitud</Button>
          </Link>
        )}
      </div>

      {error && <Alert tipo="error">{error}</Alert>}
      {!t && !error && <Cargando />}
      {t && (
        <>
          <section aria-label="Resumen por estado" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {ESTADOS.filter((e) => t.por_estado[e] > 0 || ["BORRADOR", "EN_COTIZACION", "FORMALIZADO", "DEVENGADO"].includes(e)).map((e) => (
              <Link key={e} href={`/contrataciones?estado=${e}`}>
                <Card className="p-4 transition-shadow hover:shadow-md">
                  <div className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", ESTADO_CLASE[e])}>{ESTADO_LABEL[e]}</div>
                  <div className="num mt-2 text-3xl font-bold text-slate-800">{t.por_estado[e]}</div>
                </Card>
              </Link>
            ))}
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Pendientes de mi atención</CardTitle>
              <span className="text-sm text-slate-500">{t.pendientes.length} trámite(s) · {t.total} en total</span>
            </CardHeader>
            {t.pendientes.length === 0 ? (
              <CardBody><p className="text-sm text-slate-500">No tiene trámites pendientes. ✔</p></CardBody>
            ) : (
              <Tabla>
                <thead><tr><Th>N°</Th><Th>Objeto</Th><Th className="text-right">Monto (Bs)</Th><Th>Estado</Th><Th>Qué debe hacer</Th><Th>Actualizado</Th><Th /></tr></thead>
                <tbody>
                  {t.pendientes.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <Td className="font-medium">{c.correlativo_interno}</Td>
                      <Td className="max-w-xs truncate" title={c.objeto_contratacion}>{c.objeto_contratacion}</Td>
                      <Td className="num text-right">{bs(c.monto_referencial_total)}</Td>
                      <Td><EstadoBadge estado={c.estado} /></Td>
                      <Td>{ACCION_PENDIENTE[user.rol][c.estado] ?? "—"}</Td>
                      <Td className="whitespace-nowrap text-slate-500">{fechaHora(c.updated_at)}</Td>
                      <Td><Link href={`/contrataciones/${c.id}`} className="inline-flex items-center gap-1 text-brand-700 hover:underline">Abrir <ArrowRight className="h-3 w-3" aria-hidden /></Link></Td>
                    </tr>
                  ))}
                </tbody>
              </Tabla>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
