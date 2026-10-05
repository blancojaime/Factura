'use client';
import { Calculator, Trophy, Trash2, UserPlus } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input, Select } from '@/components/ui/form';
import { Table, TD, TH, THead, TR } from '@/components/ui/table';
import { api } from '@/lib/api';
import { Evaluacion, Proceso, Propuesta } from '@/lib/types';
import { bs, cn, etiqueta } from '@/lib/utils';

interface ListadoPropuestas { itemsV1: { codigo: string; descripcion: string }[]; propuestas: Propuesta[]; evaluacion: Evaluacion | null }
const VACIA = { nitProveedor: '', razonSocial: '', categoria: 'NACIONAL_GENERAL', montoOfertado: 0, montoSubasta: '', plazoDias: 10, puntajeTecnico: '' };
const MARGEN: Record<string, number> = { NACIONAL_GENERAL: 10, MYPE_APP_OECA: 18, EXTRANJERO: 0 };

/** Matriz comparativa: V-1 (Presentó / No presentó), subasta, margen de preferencia, precio de comparación y ranking. */
export function MatrizComparativa({ p, editable, puedeEvaluar, onCambio }: { p: Proceso; editable: boolean; puedeEvaluar: boolean; onCambio: () => void }) {
  const [data, setData] = useState<ListadoPropuestas | null>(null);
  const [form, setForm] = useState(VACIA);
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; t: string } | null>(null);
  const conSubasta = p.tipoObjeto !== 'BIENES';
  const cpc = p.metodoSeleccion === 'CALIDAD_PROPUESTA_COSTO';
  const cargar = () => api<ListadoPropuestas>(`/procesos/${p.id}/propuestas`).then(setData);
  useEffect(() => { cargar().catch((e) => setMsg({ tipo: 'error', t: e.message })); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [p.id, p.estadoFlujo]);
  const run = async (f: () => Promise<unknown>, ok?: string) => { setMsg(null); try { await f(); await cargar(); if (ok) setMsg({ tipo: 'ok', t: ok }); onCambio(); } catch (e) { setMsg({ tipo: 'error', t: (e as Error).message }); } };

  const agregar = (e: React.FormEvent) => { e.preventDefault(); run(async () => {
    await api(`/procesos/${p.id}/propuestas`, { body: { ...form, montoSubasta: form.montoSubasta === '' ? undefined : Number(form.montoSubasta), puntajeTecnico: form.puntajeTecnico === '' ? undefined : Number(form.puntajeTecnico) } }); setForm(VACIA);
  }, 'Propuesta registrada.'); };
  /** Actualización optimista: el check responde al instante y se revierte si el servidor rechaza. */
  const marcarV1 = async (pr: Propuesta, codigo: string, v: boolean) => {
    const v1 = { ...pr.v1, [codigo]: v };
    setData((d) => d && { ...d, propuestas: d.propuestas.map((x) => (x.id === pr.id ? { ...x, v1 } : x)) });
    await run(() => api(`/procesos/${p.id}/propuestas/${pr.id}/v1`, { method: 'PUT', body: { v1 } }));
  };
  const ev = data?.evaluacion ?? null;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader><CardTitle>Verificación de documentos · Formulario V-1</CardTitle><CardDescription>Criterio «Presentó / No presentó». Basta un «No presentó» para descalificar la propuesta.</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Table>
            <THead><TR><TH>#</TH><TH>Proponente</TH><TH>Categoría</TH><TH className="text-right">Oferta</TH>{conSubasta && <TH className="text-right">Subasta</TH>}<TH className="text-right">Plazo</TH>{cpc && <TH className="text-right">Pt. téc.</TH>}{data?.itemsV1.map((i) => <TH key={i.codigo} title={i.descripcion} className="text-center">{i.codigo}</TH>)}<TH>V-1</TH><TH /></TR></THead>
            <tbody>
              {data?.propuestas.map((pr) => (
                <TR key={pr.id}>
                  <TD>{pr.orden}</TD><TD><div className="font-medium">{pr.razonSocial}</div><div className="text-xs text-muted-foreground">NIT {pr.nitProveedor}</div></TD>
                  <TD>{etiqueta(pr.categoria)} <span className="text-xs text-muted-foreground">({MARGEN[pr.categoria]}%)</span></TD>
                  <TD className="tabular text-right">{bs(pr.montoOfertado)}</TD>{conSubasta && <TD className="tabular text-right">{pr.montoSubasta ? bs(pr.montoSubasta) : '—'}</TD>}<TD className="text-right">{pr.plazoDias} d</TD>{cpc && <TD className="text-right">{pr.puntajeTecnico ?? '—'}</TD>}
                  {data.itemsV1.map((i) => <TD key={i.codigo} className="text-center"><input type="checkbox" disabled={!editable} aria-label={`${i.codigo} ${pr.razonSocial}`} checked={pr.v1?.[i.codigo] === true} onChange={(e) => marcarV1(pr, i.codigo, e.target.checked)} className="h-4 w-4 accent-[hsl(var(--primary))]" /></TD>)}
                  <TD>{data.itemsV1.every((i) => pr.v1?.[i.codigo] === true) ? <Badge variant="success">Presentó</Badge> : <Badge variant="destructive">No presentó</Badge>}</TD>
                  <TD>{editable && <Button variant="ghost" size="icon" aria-label={`Eliminar ${pr.razonSocial}`} onClick={() => run(() => api(`/procesos/${p.id}/propuestas/${pr.id}`, { method: 'DELETE' }))}><Trash2 className="h-4 w-4" /></Button>}</TD>
                </TR>
              ))}
              {data?.propuestas.length === 0 && <TR><TD colSpan={12} className="py-6 text-center text-muted-foreground">Sin propuestas registradas.</TD></TR>}
            </tbody>
          </Table>
          {data && <p className="text-xs text-muted-foreground">{data.itemsV1.map((i) => `${i.codigo}: ${i.descripcion}`).join(' · ')}</p>}
          {editable && (
            <form onSubmit={agregar} className="grid gap-2 rounded-md border bg-muted/30 p-3 md:grid-cols-6">
              <Field label="NIT"><Input required pattern="\d{6,15}" value={form.nitProveedor} onChange={(e) => setForm({ ...form, nitProveedor: e.target.value })} /></Field>
              <Field label="Razón social" className="md:col-span-2"><Input required minLength={3} value={form.razonSocial} onChange={(e) => setForm({ ...form, razonSocial: e.target.value })} /></Field>
              <Field label="Categoría (margen)"><Select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}><option value="NACIONAL_GENERAL">Nacional · 10%</option><option value="MYPE_APP_OECA">MyPE/APP/OECA · 18%</option><option value="EXTRANJERO">Extranjero · 0%</option></Select></Field>
              <Field label="Monto ofertado (Bs)"><Input required type="number" step="0.01" min="0.01" value={form.montoOfertado || ''} onChange={(e) => setForm({ ...form, montoOfertado: Number(e.target.value) })} /></Field>
              {conSubasta && <Field label="Monto tras subasta (Bs)"><Input type="number" step="0.01" min="0.01" value={form.montoSubasta} onChange={(e) => setForm({ ...form, montoSubasta: e.target.value })} /></Field>}
              <Field label="Plazo (días)"><Input required type="number" min="1" value={form.plazoDias} onChange={(e) => setForm({ ...form, plazoDias: Number(e.target.value) })} /></Field>
              {cpc && <Field label="Puntaje técnico (0-100)"><Input type="number" min="0" max="100" step="0.01" value={form.puntajeTecnico} onChange={(e) => setForm({ ...form, puntajeTecnico: e.target.value })} /></Field>}
              <div className="flex items-end"><Button type="submit" className="w-full"><UserPlus className="h-4 w-4" />Registrar</Button></div>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <div><CardTitle>Cuadro comparativo de ofertas</CardTitle><CardDescription>{etiqueta(p.metodoSeleccion)} · precio de comparación = precio final × (1 − margen de preferencia)</CardDescription></div>
          {puedeEvaluar && <Button onClick={() => run(() => api(`/procesos/${p.id}/evaluacion`, { method: 'POST' }), 'Evaluación ejecutada.')} disabled={!data?.propuestas.length} data-testid="btn-evaluar"><Calculator className="h-4 w-4" />Ejecutar evaluación</Button>}
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {!ev && <p className="text-sm text-muted-foreground">Sin evaluación vigente. Se invalida automáticamente cuando cambia cualquier propuesta o V-1.</p>}
          {ev && (
            <>
              <Table>
                <THead><TR><TH>Pos.</TH><TH>Proponente</TH><TH className="text-right">Oferta</TH>{conSubasta && <TH className="text-right">Subasta</TH>}<TH className="text-right">Precio final</TH><TH className="text-right">Margen</TH><TH className="text-right">P. comparación</TH><TH className="text-right">Dif. vs ref.</TH><TH className="text-right">Plazo</TH>{cpc && <TH className="text-right">Total pts.</TH>}<TH>Resultado</TH></TR></THead>
                <tbody>
                  {ev.filas.map((f) => (
                    <TR key={f.propuestaId} className={cn(f.propuestaId === ev.recomendadaId && 'bg-success/10', f.estado !== 'CALIFICA' && 'text-muted-foreground')}>
                      <TD className="font-semibold">{f.posicion === 1 ? <Trophy className="h-4 w-4 text-warning" aria-label="Recomendada" /> : (f.posicion ?? '—')}</TD>
                      <TD>{f.razonSocial}</TD><TD className="tabular text-right">{bs(f.montoOfertado)}</TD>{conSubasta && <TD className="tabular text-right">{f.montoSubasta ? bs(f.montoSubasta) : '—'}</TD>}
                      <TD className="tabular text-right">{bs(f.precioFinal)}</TD><TD className="text-right">{f.margenPreferenciaPct}%</TD><TD className="tabular text-right font-semibold">{bs(f.precioComparacion)}</TD>
                      <TD className="tabular text-right">{f.diferenciaVsReferencialPct}%</TD><TD className="text-right">{f.plazoDias} d</TD>{cpc && <TD className="text-right">{f.puntajeTotal ?? '—'}</TD>}
                      <TD>{f.estado === 'CALIFICA' ? <Badge variant="success">Califica</Badge> : <div><Badge variant="destructive">No califica</Badge><div className="mt-1 max-w-[220px] text-[11px] leading-tight">{f.motivos.join(' · ')}</div></div>}</TD>
                    </TR>
                  ))}
                </tbody>
              </Table>
              {ev.desierto ? <Alert tipo="error"><b>Se recomienda declarar desierto.</b> {ev.motivoDesierto}</Alert> : <Alert tipo="ok"><b>Recomendación:</b> adjudicar a {ev.filas.find((f) => f.propuestaId === ev.recomendadaId)?.razonSocial} por {bs(ev.filas.find((f) => f.propuestaId === ev.recomendadaId)?.precioFinal)}.</Alert>}
              {ev.observaciones.map((o, i) => <Alert key={i} tipo="warn">{o}</Alert>)}
            </>
          )}
          {msg && <Alert tipo={msg.tipo}>{msg.t}</Alert>}
        </CardContent>
      </Card>
    </div>
  );
}
