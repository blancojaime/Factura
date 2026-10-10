"use client";

import { Lightbulb, Pencil, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Textarea } from "@/components/ui";
import { api, mensajeError } from "@/lib/api";
import { bs, METODO_LABEL, MODALIDAD_LABEL, TIPO_OBJETO_LABEL } from "@/lib/format";
import { GUIA_ET } from "@/lib/guias";
import type { Catalogo, ConsultaCHB, Contratacion, Item, Partida, Regla, TipoObjeto } from "@/lib/tipos";
import { ErrorApi, useAccion } from "./comun";
import ItemsTabla from "./ItemsTabla";

interface ItemForm {
  id: string | null; codigo: string; partida_id: string; descripcion: string; unidad: string; cantidad: string;
  precio: string; fuera: boolean;
}
const VACIO: ItemForm = { id: null, codigo: "", partida_id: "", descripcion: "", unidad: "", cantidad: "1", precio: "", fuera: false };

/** Formulador asistido del C-1: datos, ET/TdR, items con consulta CHB y partida, vista previa de reglas y envio. */
export default function Formulador({ c, recargar }: { c: Contratacion; recargar: () => Promise<void> }) {
  const { ejecutar, cargando, error, ok, limpiar } = useAccion(recargar);
  const [partidas, setPartidas] = useState<Partida[]>([]);
  const [regla, setRegla] = useState<Regla | null>(null);
  const [form, setForm] = useState<ItemForm>(VACIO);
  const [sugerencias, setSugerencias] = useState<Catalogo[]>([]);
  const [chb, setChb] = useState<ConsultaCHB | null>(null);
  const [errItem, setErrItem] = useState<Parameters<typeof ErrorApi>[0]["error"]>(null);
  const guia = GUIA_ET[c.tipo_objeto];

  useEffect(() => {
    api.get<Partida[]>("/partidas").then(setPartidas).catch(() => undefined);
  }, []);

  // vista previa en vivo de las reglas de cuantia y formalizacion
  useEffect(() => {
    if (c.items.length === 0) { setRegla(null); return; }
    const qs = new URLSearchParams({ monto: c.monto_referencial_total, plazo: String(c.plazo_dias_calendario), tipo_objeto: c.tipo_objeto });
    api.get<Regla>(`/contrataciones/reglas/simular?${qs}`).then(setRegla).catch(() => setRegla(null));
  }, [c.items.length, c.monto_referencial_total, c.plazo_dias_calendario, c.tipo_objeto]);

  // busqueda en el catalogo CHB mientras se escribe
  useEffect(() => {
    const q = form.codigo.trim();
    if (q.length < 2 || q.length === 8) { setSugerencias([]); return; }
    const t = setTimeout(() => api.get<Catalogo[]>(`/catalogo-chb?q=${encodeURIComponent(q)}`).then(setSugerencias).catch(() => undefined), 250);
    return () => clearTimeout(t);
  }, [form.codigo]);

  // consulta puntual del codigo completo
  useEffect(() => {
    if (!/^\d{8}$/.test(form.codigo)) { setChb(null); return; }
    api.get<ConsultaCHB>(`/catalogo-chb/consulta/${form.codigo}`).then(setChb).catch(() => setChb(null));
  }, [form.codigo]);

  const partidaSel = useMemo(() => partidas.find((p) => p.id === form.partida_id), [partidas, form.partida_id]);
  const obligatorios = c.items.filter((i) => i.estado_chb === "COMPRA_CHB_OBLIGATORIA");

  function elegirSugerencia(s: Catalogo) {
    setForm((f) => ({ ...f, codigo: s.codigo_unspsc, descripcion: f.descripcion || s.descripcion_bien, unidad: f.unidad || s.unidad_medida,
      precio: f.precio || (s.precio_referencial_nacional ?? "") }));
    setSugerencias([]);
  }

  function editar(i: Item) {
    setForm({ id: i.id, codigo: i.codigo_unspsc, partida_id: i.partida_id ?? "", descripcion: i.descripcion_especifica,
      unidad: i.unidad_medida, cantidad: String(Number(i.cantidad)), precio: String(Number(i.precio_unitario_ref)), fuera: i.fuera_catalogo_chb });
    setErrItem(null);
    window.scrollTo({ top: document.getElementById("form-item")?.offsetTop ?? 0, behavior: "smooth" });
  }

  async function guardarItem(e: FormEvent) {
    e.preventDefault();
    setErrItem(null);
    const cuerpo = {
      codigo_unspsc: form.codigo.trim(), partida_id: form.partida_id, descripcion_especifica: form.descripcion.trim(),
      unidad_medida: form.unidad.trim(), cantidad: form.cantidad, precio_unitario_ref: form.precio, fuera_catalogo_chb: form.fuera,
    };
    const exito = await ejecutar("item", () => form.id ? api.put(`/contrataciones/${c.id}/items/${form.id}`, cuerpo) : api.post(`/contrataciones/${c.id}/items`, cuerpo));
    if (exito) { setForm(VACIO); setChb(null); }
  }

  async function guardarDatos(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await ejecutar("datos", () => api.patch(`/contrataciones/${c.id}`, {
      objeto_contratacion: String(f.get("objeto")).trim(), plazo_dias_calendario: Number(f.get("plazo")),
      unidad_solicitante: String(f.get("unidad")).trim(), lugar_entrega: String(f.get("lugar")).trim(),
      justificacion: String(f.get("justificacion")).trim(), especificaciones_tecnicas: String(f.get("et")).trim(),
      justificacion_excepcion_chb: String(f.get("exc") ?? c.justificacion_excepcion_chb ?? "").trim() || null,
      codigo_autorizacion_chb: String(f.get("autorizacion") ?? "").trim() || null,
    }), "Datos guardados");
  }

  return (
    <div className="space-y-5">
      <Alert tipo="info" titulo="Formulador asistido del Formulario C-1">
        Complete los datos, redacte las {guia.titulo.toLowerCase()}, agregue los ítems (consulta obligatoria al Catálogo CHB) y envíe la solicitud a Presupuesto.
      </Alert>

      <form onSubmit={guardarDatos} aria-label="Datos de la solicitud" key={c.updated_at}>
        <Card>
          <CardHeader><CardTitle>1. Datos y especificaciones</CardTitle><span className="text-xs text-slate-500">{TIPO_OBJETO_LABEL[c.tipo_objeto]}</span></CardHeader>
          <CardBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Objeto de la contratación" className="sm:col-span-2"><Input name="objeto" defaultValue={c.objeto_contratacion} required minLength={5} /></Field>
            <Field label="Plazo (días calendario)" hint="≤ 15 días: Orden · > 15 días: Contrato"><Input name="plazo" type="number" min={1} defaultValue={c.plazo_dias_calendario} required /></Field>
            <Field label="Unidad solicitante"><Input name="unidad" defaultValue={c.unidad_solicitante} required /></Field>
            <Field label="Lugar de entrega / ejecución"><Input name="lugar" defaultValue={c.lugar_entrega} required /></Field>
            <Field label="Justificación de la necesidad"><Textarea name="justificacion" defaultValue={c.justificacion} required /></Field>
            <div className="space-y-2 sm:col-span-2">
              <Alert tipo="info" titulo={guia.titulo}>
                <ul className="list-inside list-disc">{guia.puntos.map((p) => <li key={p}><Lightbulb className="mr-1 inline h-3 w-3" aria-hidden />{p}</li>)}</ul>
              </Alert>
              <Field label="Redacción de las ET / TdR"><Textarea name="et" defaultValue={c.especificaciones_tecnicas} required minLength={20} className="min-h-[140px]" /></Field>
            </div>
            {c.requiere_excepcion_chb && (
              <div className="space-y-3 rounded-md border border-amber-300 bg-amber-50 p-4 sm:col-span-2">
                <p className="text-sm font-semibold text-amber-900">Justificación de compra fuera del Catálogo CHB (D.S. 4505 / D.S. 0181)</p>
                <p className="text-xs text-amber-800">Se emitirá automáticamente el «Informe Técnico-Legal de Justificación» al enviar la solicitud.</p>
                <Field label="Justificación técnico-legal (mínimo 80 caracteres)">
                  <Textarea name="exc" defaultValue={c.justificacion_excepcion_chb ?? ""} className="min-h-[110px] bg-white" />
                </Field>
                <Field label="Código de autorización CHB (si corresponde)"><Input name="autorizacion" defaultValue={c.codigo_autorizacion_chb ?? ""} className="bg-white" /></Field>
              </div>
            )}
            <div className="flex items-center justify-end gap-3 sm:col-span-2">
              {ok && <span className="text-sm text-emerald-700">{ok}</span>}
              <Button type="submit" variant="outline" cargando={cargando === "datos"}>Guardar datos</Button>
            </div>
          </CardBody>
        </Card>
      </form>

      <Card>
        <CardHeader><CardTitle>2. Ítems</CardTitle><span className="text-xs text-slate-500">{c.items.length} ítem(s)</span></CardHeader>
        <CardBody className="space-y-4 p-0">
          <ItemsTabla items={c.items} total={c.monto_referencial_total} acciones={(i) => (
            <div className="flex gap-1">
              <button aria-label={`Editar ítem ${i.numero}`} className="rounded p-1 text-slate-600 hover:bg-slate-100" onClick={() => editar(i)}><Pencil className="h-4 w-4" /></button>
              <button aria-label={`Eliminar ítem ${i.numero}`} className="rounded p-1 text-red-600 hover:bg-red-50" onClick={() => ejecutar("del", () => api.del(`/contrataciones/${c.id}/items/${i.id}`))}><Trash2 className="h-4 w-4" /></button>
            </div>
          )} />
        </CardBody>
      </Card>

      <form id="form-item" onSubmit={guardarItem} aria-label="Agregar ítem">
        <Card>
          <CardHeader><CardTitle>{form.id ? "Editar ítem" : "Agregar ítem"}</CardTitle></CardHeader>
          <CardBody className="grid gap-4 sm:grid-cols-6">
            <div className="relative sm:col-span-2">
              <Field label={c.tipo_objeto === "BIEN" ? "Código UNSPSC / buscar en catálogo CHB" : "Código UNSPSC (opcional)"} hint="Escriba el código (8 dígitos) o parte del nombre">
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" aria-hidden />
                  <Input className="pl-9" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} inputMode="numeric" autoComplete="off" aria-label="Código UNSPSC" />
                </div>
              </Field>
              {sugerencias.length > 0 && (
                <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-md border border-slate-200 bg-white text-sm shadow-lg" role="listbox">
                  {sugerencias.map((s) => (
                    <li key={s.id}><button type="button" className="block w-full px-3 py-2 text-left hover:bg-brand-50" onClick={() => elegirSugerencia(s)}>
                      <span className="num font-medium">{s.codigo_unspsc}</span> — {s.descripcion_bien}</button></li>
                  ))}
                </ul>
              )}
            </div>
            <Field label="Partida presupuestaria" className="sm:col-span-4">
              <Select value={form.partida_id} onChange={(e) => setForm({ ...form, partida_id: e.target.value })} required>
                <option value="">Seleccione…</option>
                {partidas.map((p) => <option key={p.id} value={p.id}>{p.codigo_partida} · {p.descripcion} (saldo Bs {bs(p.saldo_disponible)})</option>)}
              </Select>
            </Field>

            {chb && (
              <div className="sm:col-span-6">
                {chb.en_catalogo ? (
                  <Alert tipo="warning" titulo={`Catálogo CHB: ${chb.descripcion_bien}`}>
                    <p>{chb.mensaje}</p>
                    {chb.precio_referencial_nacional && <p>Precio referencial nacional: Bs {bs(chb.precio_referencial_nacional)} por {chb.unidad_medida}.</p>}
                    <label className="mt-2 flex items-center gap-2 font-medium">
                      <input type="checkbox" checked={form.fuera} onChange={(e) => setForm({ ...form, fuera: e.target.checked })} />
                      Se compra fuera del catálogo por incompatibilidad (requiere justificación)
                    </label>
                  </Alert>
                ) : (
                  <Alert tipo="info">{chb.mensaje}</Alert>
                )}
              </div>
            )}

            <Field label="Descripción específica" className="sm:col-span-4"><Input value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} required minLength={3} /></Field>
            <Field label="Unidad" className="sm:col-span-2"><Input value={form.unidad} onChange={(e) => setForm({ ...form, unidad: e.target.value })} required /></Field>
            <Field label="Cantidad" className="sm:col-span-2"><Input type="number" min="0.001" step="0.001" value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} required /></Field>
            <Field label="Precio unitario referencial (Bs)" className="sm:col-span-2"><Input type="number" min="0.01" step="0.01" value={form.precio} onChange={(e) => setForm({ ...form, precio: e.target.value })} required /></Field>
            <div className="flex items-end justify-between gap-2 sm:col-span-2">
              <div className="num text-sm text-slate-600">Subtotal: <b>Bs {bs(Number(form.cantidad || 0) * Number(form.precio || 0))}</b>{partidaSel && <div className="text-xs">Saldo partida: Bs {bs(partidaSel.saldo_disponible)}</div>}</div>
              <div className="flex gap-2">
                {form.id && <Button variant="outline" onClick={() => { setForm(VACIO); setChb(null); }}>Cancelar</Button>}
                <Button type="submit" cargando={cargando === "item"}>{form.id ? "Actualizar" : "Agregar"}</Button>
              </div>
            </div>
            <div className="sm:col-span-6"><ErrorApi error={errItem ?? (cargando === null ? error : null)} /></div>
          </CardBody>
        </Card>
      </form>

      <Card>
        <CardHeader><CardTitle>3. Verificación normativa y envío</CardTitle></CardHeader>
        <CardBody className="space-y-3">
          {c.items.length === 0 && <Alert tipo="info">Agregue al menos un ítem para ver la cuantía, la modalidad y la formalización.</Alert>}
          {regla && (
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-slate-200 p-3"><div className="text-xs uppercase text-slate-500">Monto referencial</div><div className="num text-xl font-bold">Bs {bs(c.monto_referencial_total)}</div></div>
              <div className="rounded-md border border-slate-200 p-3"><div className="text-xs uppercase text-slate-500">Modalidad por cuantía</div><div className="text-sm font-medium">{regla.modalidad ? MODALIDAD_LABEL[regla.modalidad] : "—"}</div></div>
              <div className="rounded-md border border-slate-200 p-3"><div className="text-xs uppercase text-slate-500">Se formalizará con</div><div className="text-sm font-medium">{regla.metodo_formalizacion ? METODO_LABEL[regla.metodo_formalizacion] : "—"}</div></div>
            </div>
          )}
          {regla?.bloqueado && <Alert tipo="error" titulo="Cuantía no permitida">{regla.mensaje}</Alert>}
          {regla && !regla.bloqueado && <Alert tipo={regla.requiere_formulario_110 ? "warning" : "success"}>{regla.mensaje}</Alert>}
          {obligatorios.length > 0 && (
            <Alert tipo="error" titulo="Compra obligatoria en el Catálogo CHB">
              {obligatorios.map((i) => <p key={i.id}>Ítem {i.numero} ({i.codigo_unspsc}): adquiera por catálogo o edite el ítem y marque la excepción con su justificación.</p>)}
            </Alert>
          )}
          <ErrorApi error={cargando === null && !errItem ? error : null} />
          <div className="flex justify-end">
            <Button variant="success" size="lg" cargando={cargando === "solicitar"} disabled={c.items.length === 0}
              onClick={() => { limpiar(); void ejecutar("solicitar", () => api.post(`/contrataciones/${c.id}/solicitar`)); }}>
              Enviar solicitud a Presupuesto
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
