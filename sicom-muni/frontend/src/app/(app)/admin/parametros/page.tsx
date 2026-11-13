"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Cargando, Field, Input } from "@/components/ui";
import { api, mensajeError } from "@/lib/api";
import type { Parametro } from "@/lib/tipos";

export default function ParametrosPage() {
  const [params, setParams] = useState<Parametro[] | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<{ tipo: "success" | "error"; texto: string } | null>(null);

  useEffect(() => {
    api.get<Parametro[]>("/admin/parametros").then((p) => { setParams(p); setValores(Object.fromEntries(p.map((x) => [x.clave, x.valor]))); })
      .catch((e) => setMsg({ tipo: "error", texto: mensajeError(e) }));
  }, []);

  async function guardar(clave: string) {
    try {
      await api.put(`/admin/parametros/${clave}`, { valor: valores[clave] });
      setMsg({ tipo: "success", texto: `Parámetro «${clave}» guardado` });
    } catch (e) { setMsg({ tipo: "error", texto: mensajeError(e) }); }
  }

  function cargarLogo(f: File | undefined) {
    if (!f) return;
    const r = new FileReader();
    r.onload = () => setValores((v) => ({ ...v, logo_url: String(r.result) }));
    r.readAsDataURL(f);
  }

  if (!params) return <Cargando />;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-brand-900">Parámetros institucionales del GAM</h1>
      {msg && <Alert tipo={msg.tipo}>{msg.texto}</Alert>}
      <Card>
        <CardHeader><CardTitle>Configuración</CardTitle></CardHeader>
        <CardBody className="space-y-4">
          {params.map((p) => (
            <div key={p.clave} className="grid items-end gap-2 sm:grid-cols-[1fr_auto]">
              {p.clave === "logo_url" ? (
                <Field label="Logotipo oficial (imagen)" hint={p.descripcion}>
                  <div className="flex items-center gap-3">
                    {valores.logo_url?.startsWith("data:") && <img src={valores.logo_url} alt="Logotipo" className="h-12 w-12 rounded border object-contain" />}
                    <input type="file" accept="image/png,image/jpeg" onChange={(e) => cargarLogo(e.target.files?.[0])} aria-label="Cargar logotipo" />
                  </div>
                </Field>
              ) : (
                <Field label={p.clave} hint={p.descripcion}><Input value={valores[p.clave] ?? ""} onChange={(e) => setValores({ ...valores, [p.clave]: e.target.value })} /></Field>
              )}
              <Button variant="outline" onClick={() => guardar(p.clave)}>Guardar</Button>
            </div>
          ))}
        </CardBody>
      </Card>
      <p className="text-xs text-slate-500">Los topes, plazos y mínimos de cotizaciones deben validarse con la normativa vigente de su entidad antes de operar.</p>
    </div>
  );
}
