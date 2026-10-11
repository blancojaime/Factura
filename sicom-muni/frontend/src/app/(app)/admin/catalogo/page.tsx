"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorApi } from "@/components/contratacion/comun";
import ImportarExcel from "@/components/ImportarExcel";
import { Badge, Button, Card, CardHeader, CardTitle, Dialog, Field, Input, Tabla, Td, Th } from "@/components/ui";
import { api, ApiError, mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { bs, fecha } from "@/lib/format";
import type { Catalogo } from "@/lib/tipos";

export default function CatalogoPage() {
  const [q, setQ] = useState("");
  const [lista, setLista] = useState<Catalogo[]>([]);
  const { user } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [importar, setImportar] = useState(false);
  const [err, setErr] = useState<ApiError | string | null>(null);

  const cargar = useCallback(() => api.get<Catalogo[]>(`/catalogo-chb?q=${encodeURIComponent(q)}`).then(setLista).catch((e) => setErr(mensajeError(e))), [q]);
  useEffect(() => { const t = setTimeout(() => void cargar(), 250); return () => clearTimeout(t); }, [cargar]);

  async function crear(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setErr(null);
    try {
      await api.post("/catalogo-chb", { codigo_unspsc: String(f.get("codigo")), descripcion_bien: String(f.get("desc")), unidad_medida: String(f.get("unidad")),
        precio_referencial_nacional: f.get("precio") ? String(f.get("precio")) : null });
      setAbierto(false);
      await cargar();
    } catch (x) { setErr(x instanceof ApiError ? x : mensajeError(x)); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-2xl font-bold text-brand-900">Catálogo Compro Hecho en Bolivia</h1><div className="flex gap-2">
        <Button variant="outline" onClick={() => setImportar(true)}>Importar desde Excel</Button>
        {user?.rol === "ROL_ADMIN" && <Button onClick={() => { setErr(null); setAbierto(true); }}>Agregar bien</Button>}</div></div>
      <Input placeholder="Buscar por código o descripción…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar en el catálogo" />
      <Card>
        <CardHeader><CardTitle>Bienes del catálogo (D.S. 4505)</CardTitle></CardHeader>
        <Tabla aria-label="Catálogo CHB">
          <thead><tr><Th>UNSPSC</Th><Th>Descripción</Th><Th>Unidad</Th><Th className="text-right">Precio ref. nacional (Bs)</Th><Th>Fecha de registro</Th><Th>Estado</Th></tr></thead>
          <tbody>{lista.map((c) => (
            <tr key={c.id}><Td className="num font-medium">{c.codigo_unspsc}</Td><Td>{c.descripcion_bien}</Td><Td>{c.unidad_medida}</Td><Td className="num text-right">{bs(c.precio_referencial_nacional)}</Td><Td>{fecha(c.fecha_registro)}</Td>
              <Td><Badge className={c.activo ? "bg-emerald-100 text-emerald-800 ring-emerald-300" : "bg-slate-100 text-slate-600 ring-slate-300"}>{c.activo ? "Activo" : "Inactivo"}</Badge></Td></tr>
          ))}</tbody>
        </Tabla>
      </Card>
      <ImportarExcel abierto={importar} onCerrar={() => setImportar(false)} titulo="Importar catálogo Compro Hecho en Bolivia" ruta="/catalogo-chb/importar"
        plantilla="chb" columnas={["Código UNSPSC", "Descripción código", "Precio", "(opcional) Unidad"]}
        nota="Cada importación reemplaza los datos de los códigos que ya existen (nuevo precio y descripción) y registra la fecha de importación. Los códigos que no vienen en el archivo se conservan."
        onHecho={() => void cargar()} />
      <Dialog abierto={abierto} onCerrar={() => setAbierto(false)} titulo="Agregar bien al catálogo">
        <form onSubmit={crear} className="space-y-3">
          <Field label="Código UNSPSC (8 dígitos)"><Input name="codigo" pattern="[0-9]{8}" required /></Field>
          <Field label="Descripción"><Input name="desc" required minLength={3} /></Field>
          <Field label="Unidad de medida"><Input name="unidad" /></Field>
          <Field label="Precio referencial nacional (Bs)"><Input name="precio" type="number" step="0.01" min={0} /></Field>
          <ErrorApi error={err} />
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setAbierto(false)}>Cancelar</Button><Button type="submit">Guardar</Button></div>
        </form>
      </Dialog>
    </div>
  );
}
