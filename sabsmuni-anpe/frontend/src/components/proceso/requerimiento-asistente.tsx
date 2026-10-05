'use client';
import { CheckCircle2, ChevronLeft, ChevronRight, Save, ShieldAlert, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input, Select, Textarea } from '@/components/ui/form';
import { Table, TD, TH, THead, TR } from '@/components/ui/table';
import { api } from '@/lib/api';
import { Hallazgo, Proceso } from '@/lib/types';
import { bs, cn, etiqueta } from '@/lib/utils';

interface Informe {
  valido: boolean; completitud: { completo: boolean; faltantes: string[] }; hallazgos: Hallazgo[]; requiereJustificacionChb: boolean; justificacionDocumentoId: string | null;
  chb: { itemId: string; numero: number; codigoUnspsc: string; validacion: { resultado: string; requiereExcepcion: boolean; requiereFichaChb: boolean; mensaje: string } }[];
}
const CHB_VARIANTE: Record<string, 'success' | 'warning' | 'destructive' | 'secondary'> = { CUBIERTO_POR_CHB: 'success', NO_APLICA: 'secondary', SIMILAR_EN_CHB: 'warning', SIN_PRODUCCION_NACIONAL: 'warning', INCOMPATIBLE_CON_CHB: 'warning' };
const VACIO = { codigoUnspsc: '', partidaGasto: '', descripcionTecnica: '', unidadMedida: 'pieza', cantidad: 1, precioUnitario: 0, incompatibilidadTecnica: '' };

/** Asistente guiado: ítems → redacción de ET/TdR sección por sección con análisis en vivo → validación CHB (D.S. 4505). */
export function RequerimientoAsistente({ p, editable, onCambio }: { p: Proceso; editable: boolean; onCambio: () => void }) {
  const secciones = p.secciones;
  const [paso, setPaso] = useState(0);
  const [textos, setTextos] = useState<Record<string, string>>(p.requerimiento ?? {});
  const [vivo, setVivo] = useState<Hallazgo[]>([]);
  const [informe, setInforme] = useState<Informe | null>(null);
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; t: string } | null>(null);
  const [item, setItem] = useState(VACIO);
  const [partidas, setPartidas] = useState<{ codigo: string; descripcion: string }[]>([]);
  const actual = secciones[paso];
  const temporizador = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => { api<typeof partidas>('/catalogos/partidas').then(setPartidas).catch(() => undefined); }, []);
  // Análisis en vivo con debounce de lo que se escribe
  useEffect(() => {
    clearTimeout(temporizador.current);
    const t = textos[actual?.clave] ?? '';
    if (!t.trim()) { setVivo([]); return; }
    temporizador.current = setTimeout(() => api<{ hallazgos: Hallazgo[] }>('/requerimiento/analizar', { body: { texto: t } }).then((r) => setVivo(r.hallazgos)).catch(() => undefined), 450);
    return () => clearTimeout(temporizador.current);
  }, [textos, actual?.clave]);

  const completadas = useMemo(() => secciones.filter((s) => (textos[s.clave] ?? '').trim().length >= 20).length, [secciones, textos]);
  const run = async (f: () => Promise<unknown>, ok?: string) => { setMsg(null); try { await f(); if (ok) setMsg({ tipo: 'ok', t: ok }); onCambio(); } catch (e) { setMsg({ tipo: 'error', t: (e as Error).message }); } };

  const guardar = () => run(() => api(`/procesos/${p.id}/requerimiento`, { method: 'PUT', body: { secciones: textos } }), 'Requerimiento guardado.');
  const validar = () => run(async () => { await api(`/procesos/${p.id}/requerimiento`, { method: 'PUT', body: { secciones: textos } }); setInforme(await api<Informe>(`/procesos/${p.id}/requerimiento/validar`, { method: 'POST' })); });
  const agregarItem = (e: React.FormEvent) => { e.preventDefault(); run(async () => { await api(`/procesos/${p.id}/items`, { body: { ...item, incompatibilidadTecnica: item.incompatibilidadTecnica || undefined } }); setItem(VACIO); }, 'Ítem agregado.'); };

  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <Card className="lg:col-span-5">
        <CardHeader><CardTitle>1 · Ítems requeridos</CardTitle><CardDescription>Código UNSPSC (8 dígitos) y partida de gasto (5 dígitos). El total define el precio referencial.</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Table>
            <THead><TR><TH>N°</TH><TH>UNSPSC</TH><TH>Partida</TH><TH>Descripción técnica</TH><TH>Unidad</TH><TH className="text-right">Cant.</TH><TH className="text-right">P. unit.</TH><TH className="text-right">Total</TH><TH>CHB</TH><TH /></TR></THead>
            <tbody>
              {p.items.map((i) => (
                <TR key={i.id}>
                  <TD>{i.numero}</TD><TD className="font-mono text-xs">{i.codigoUnspsc}</TD><TD>{i.partidaGasto}</TD><TD className="max-w-xs">{i.descripcionTecnica}</TD><TD>{i.unidadMedida}</TD>
                  <TD className="tabular text-right">{i.cantidad}</TD><TD className="tabular text-right">{bs(i.precioUnitario)}</TD><TD className="tabular text-right">{bs(i.precioTotal)}</TD>
                  <TD>{i.resultadoChb ? <Badge variant={CHB_VARIANTE[i.resultadoChb] ?? 'secondary'}>{etiqueta(i.resultadoChb)}</Badge> : <span className="text-xs text-muted-foreground">sin validar</span>}</TD>
                  <TD>{editable && <Button variant="ghost" size="icon" aria-label="Eliminar ítem" onClick={() => run(() => api(`/procesos/${p.id}/items/${i.id}`, { method: 'DELETE' }))}><Trash2 className="h-4 w-4" /></Button>}</TD>
                </TR>
              ))}
              <TR className="bg-muted/40 font-semibold"><TD colSpan={7} className="text-right">Precio referencial total</TD><TD className="tabular text-right" data-testid="total-items">{bs(p.precioReferencialTotal)}</TD><TD colSpan={2} /></TR>
            </tbody>
          </Table>
          {editable && (
            <form onSubmit={agregarItem} className="grid gap-2 rounded-md border bg-muted/30 p-3 md:grid-cols-6">
              <Field label="UNSPSC (8 díg.)"><Input required pattern="\d{8}" value={item.codigoUnspsc} onChange={(e) => setItem({ ...item, codigoUnspsc: e.target.value })} placeholder="30111505" /></Field>
              <Field label="Partida de gasto"><Input required pattern="\d{5}" list="partidas" value={item.partidaGasto} onChange={(e) => setItem({ ...item, partidaGasto: e.target.value })} placeholder="34200" /><datalist id="partidas">{partidas.map((x) => <option key={x.codigo} value={x.codigo}>{x.descripcion}</option>)}</datalist></Field>
              <Field label="Unidad"><Input required value={item.unidadMedida} onChange={(e) => setItem({ ...item, unidadMedida: e.target.value })} /></Field>
              <Field label="Cantidad"><Input required type="number" step="0.001" min="0.001" value={item.cantidad} onChange={(e) => setItem({ ...item, cantidad: Number(e.target.value) })} /></Field>
              <Field label="Precio unitario (Bs)"><Input required type="number" step="0.01" min="0.01" value={item.precioUnitario} onChange={(e) => setItem({ ...item, precioUnitario: Number(e.target.value) })} /></Field>
              <div className="flex items-end"><Button type="submit" className="w-full">Agregar ítem</Button></div>
              <Field label="Descripción técnica (sin marcas)" className="md:col-span-4"><Input required minLength={5} value={item.descripcionTecnica} onChange={(e) => setItem({ ...item, descripcionTecnica: e.target.value })} /></Field>
              <Field label="Incompatibilidad técnica con el CHB (opcional)" className="md:col-span-2"><Input value={item.incompatibilidadTecnica} onChange={(e) => setItem({ ...item, incompatibilidadTecnica: e.target.value })} placeholder="Solo si existe producto nacional pero no sirve" /></Field>
            </form>
          )}
        </CardContent>
      </Card>

      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle>2 · {p.tipoObjeto === 'SERVICIOS' ? 'Términos de Referencia' : 'Especificaciones Técnicas'}</CardTitle>
          <CardDescription>Sección {paso + 1} de {secciones.length} · {completadas} completadas</CardDescription>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-muted"><div className="h-full bg-primary transition-all" style={{ width: `${(completadas / secciones.length) * 100}%` }} /></div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-1">
            {secciones.map((s, i) => <button key={s.clave} onClick={() => setPaso(i)} className={cn('rounded-full border px-2.5 py-1 text-xs', i === paso ? 'border-primary bg-primary text-primary-foreground' : 'hover:bg-accent', (textos[s.clave] ?? '').trim().length >= 20 && i !== paso && 'border-success/50 text-success')}>{i + 1}. {s.titulo}</button>)}
          </div>
          {actual && (
            <Field label={`${actual.titulo} — ${actual.ayuda}`}>
              <Textarea disabled={!editable} className="min-h-[160px]" value={textos[actual.clave] ?? ''} onChange={(e) => setTextos({ ...textos, [actual.clave]: e.target.value })} aria-label={actual.titulo} data-testid="seccion-texto" />
            </Field>
          )}
          {vivo.map((h, i) => <Alert key={i} tipo={h.severidad === 'BLOQUEANTE' ? 'error' : 'warn'}><b>{h.severidad === 'BLOQUEANTE' ? 'Bloqueante' : 'Advertencia'}:</b> {h.sugerencia}</Alert>)}
          {editable && (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex gap-1"><Button variant="outline" size="sm" disabled={paso === 0} onClick={() => setPaso(paso - 1)}><ChevronLeft className="h-4 w-4" />Anterior</Button><Button variant="outline" size="sm" disabled={paso === secciones.length - 1} onClick={() => setPaso(paso + 1)}>Siguiente<ChevronRight className="h-4 w-4" /></Button></div>
              <div className="flex gap-2"><Button variant="secondary" onClick={guardar}><Save className="h-4 w-4" />Guardar</Button><Button onClick={validar} data-testid="btn-validar">Validar y cruzar con CHB</Button></div>
            </div>
          )}
          {msg && <Alert tipo={msg.tipo}>{msg.t}</Alert>}
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader><CardTitle>3 · Resultado de la validación</CardTitle><CardDescription>Marcas dirigidas (NB-SABS) y catálogo de manufactura nacional (D.S. 4505)</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          {!informe && <p className="text-muted-foreground">Presione «Validar y cruzar con CHB» para analizar el requerimiento completo.</p>}
          {informe && (
            <>
              <Alert tipo={informe.valido ? 'ok' : 'error'}>{informe.valido ? 'Requerimiento sin hallazgos bloqueantes y completo.' : 'El requerimiento no puede avanzar.'}</Alert>
              {informe.completitud.faltantes.length > 0 && <Alert tipo="warn">Secciones incompletas: {informe.completitud.faltantes.join(', ')}.</Alert>}
              {informe.hallazgos.map((h, i) => <Alert key={i} tipo={h.severidad === 'BLOQUEANTE' ? 'error' : 'warn'}><b>{h.origen}:</b> {h.sugerencia}</Alert>)}
              <h4 className="mt-1 font-medium">Cruce con catálogo CHB</h4>
              {informe.chb.map((c) => (
                <div key={c.itemId} className="rounded-md border p-2">
                  <div className="flex items-center justify-between"><span>Ítem {c.numero} · <span className="font-mono text-xs">{c.codigoUnspsc}</span></span><Badge variant={CHB_VARIANTE[c.validacion.resultado] ?? 'secondary'}>{etiqueta(c.validacion.resultado)}</Badge></div>
                  <p className="mt-1 text-xs text-muted-foreground">{c.validacion.mensaje}</p>
                  {c.validacion.requiereFichaChb && <p className="mt-1 flex items-center gap-1 text-xs text-success"><CheckCircle2 className="h-3 w-3" />Adjuntar ficha del producto nacional.</p>}
                  {c.validacion.requiereExcepcion && <p className="mt-1 flex items-center gap-1 text-xs text-warning-foreground"><ShieldAlert className="h-3 w-3" />Se habilita la vía D.S. 0181 con justificación.</p>}
                </div>
              ))}
              {informe.justificacionDocumentoId && <Alert tipo="info">Se emitió el <b>Formulario de Justificación de Insuficiencia Técnica</b>. <a className="underline" target="_blank" href={`/api/documentos/${informe.justificacionDocumentoId}/descargar`}>Abrir PDF</a></Alert>}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
