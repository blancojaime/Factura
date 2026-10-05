'use client';
import { Download, FileCheck2, FileText, PackageCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/form';
import { Table, TD, TH, THead, TR } from '@/components/ui/table';
import { api } from '@/lib/api';
import { Documento, Proceso } from '@/lib/types';
import { bs, etiqueta, fecha } from '@/lib/utils';

interface Simulacion { tipo: string; monto: number; plazoDias: number; garantia: { porcentaje: number; monto: number; modalidades: string[] } }

export function ContratoPanel({ p, puedeGenerar, puedeRecibir, onCambio }: { p: Proceso; puedeGenerar: boolean; puedeRecibir: boolean; onCambio: () => void }) {
  const [sim, setSim] = useState<Simulacion | null>(null);
  const [f, setF] = useState({ fechaFirma: '', plazoDias: '', garantiaInstrumento: 'Boleta de Garantía', polizaNumero: '', polizaEntidad: '', polizaVigenciaHasta: '' });
  const [rec, setRec] = useState({ fechaRecepcion: '', observacion: '' });
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; t: string } | null>(null);
  const adjudicado = !!p.propuestaAdjudicadaId;
  useEffect(() => { if (adjudicado) api<Simulacion>(`/procesos/${p.id}/contrato/simular${f.plazoDias ? `?plazoDias=${f.plazoDias}` : ''}`).then(setSim).catch(() => setSim(null)); }, [p.id, adjudicado, f.plazoDias]);
  const run = async (fn: () => Promise<unknown>, ok: string) => { setMsg(null); try { await fn(); setMsg({ tipo: 'ok', t: ok }); onCambio(); } catch (e) { setMsg({ tipo: 'error', t: (e as Error).message }); } };
  const c = p.contrato as { tipo: string; numero: string; monto: number; garantiaPorcentaje: number; garantiaMonto: number; fechaFirma: string; fechaRecepcion: string | null } | null;
  return (
    <Card>
      <CardHeader><CardTitle>Contrato u orden y garantía de cumplimiento</CardTitle><CardDescription>Plazo ≤ 15 días calendario → Orden de Compra/Servicio (bienes/servicios) · Garantía 7% (3,5% MyPE/APP/OECA)</CardDescription></CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!adjudicado && <Alert tipo="info">Disponible cuando el RPA adjudique el proceso.</Alert>}
        {sim && (
          <div className="grid gap-2 rounded-md border bg-muted/30 p-3 text-sm sm:grid-cols-4">
            <div><div className="text-xs text-muted-foreground">Instrumento</div><b>{etiqueta(sim.tipo)}</b></div><div><div className="text-xs text-muted-foreground">Monto adjudicado</div><b className="tabular">{bs(sim.monto)}</b></div>
            <div><div className="text-xs text-muted-foreground">Garantía ({sim.garantia.porcentaje}%)</div><b className="tabular" data-testid="garantia-monto">{bs(sim.garantia.monto)}</b></div><div><div className="text-xs text-muted-foreground">Plazo</div><b>{sim.plazoDias} días calendario</b></div>
          </div>
        )}
        {adjudicado && puedeGenerar && !c && (
          <div className="grid gap-2 rounded-md border p-3 md:grid-cols-3">
            <Field label="Fecha de firma (día hábil)"><Input type="date" value={f.fechaFirma} onChange={(e) => setF({ ...f, fechaFirma: e.target.value })} data-testid="fecha-firma" /></Field>
            <Field label="Plazo (días calendario)"><Input type="number" min={1} placeholder="Según propuesta" value={f.plazoDias} onChange={(e) => setF({ ...f, plazoDias: e.target.value })} /></Field>
            <Field label="Instrumento de garantía"><Input value={f.garantiaInstrumento} onChange={(e) => setF({ ...f, garantiaInstrumento: e.target.value })} /></Field>
            <Field label="N° boleta / póliza"><Input value={f.polizaNumero} onChange={(e) => setF({ ...f, polizaNumero: e.target.value })} /></Field>
            <Field label="Entidad emisora"><Input value={f.polizaEntidad} onChange={(e) => setF({ ...f, polizaEntidad: e.target.value })} /></Field>
            <Field label="Vigencia hasta"><Input type="date" value={f.polizaVigenciaHasta} onChange={(e) => setF({ ...f, polizaVigenciaHasta: e.target.value })} /></Field>
            <div className="md:col-span-3"><Button disabled={!f.fechaFirma} onClick={() => run(() => api(`/procesos/${p.id}/contrato`, { body: { fechaFirma: f.fechaFirma, plazoDias: f.plazoDias ? Number(f.plazoDias) : undefined, garantiaInstrumento: f.garantiaInstrumento || undefined, polizaNumero: f.polizaNumero || undefined, polizaEntidad: f.polizaEntidad || undefined, polizaVigenciaHasta: f.polizaVigenciaHasta || undefined } }), 'Instrumento generado.')} data-testid="btn-generar-contrato"><FileCheck2 className="h-4 w-4" />Generar contrato / orden</Button></div>
          </div>
        )}
        {c && <Alert tipo="ok">{etiqueta(c.tipo)} <b>{c.numero}</b> firmado el {fecha(c.fechaFirma)} por {bs(c.monto)} · garantía {c.garantiaPorcentaje}% = {bs(c.garantiaMonto)}.</Alert>}
        {c && puedeRecibir && !c.fechaRecepcion && p.estadoFlujo === 'CONTRATO_FORMALIZADO' && (
          <div className="flex flex-wrap items-end gap-2 rounded-md border p-3">
            <Field label="Fecha de recepción"><Input type="date" value={rec.fechaRecepcion} onChange={(e) => setRec({ ...rec, fechaRecepcion: e.target.value })} /></Field>
            <Field label="Observaciones" className="min-w-[240px] flex-1"><Input value={rec.observacion} onChange={(e) => setRec({ ...rec, observacion: e.target.value })} /></Field>
            <Button disabled={!rec.fechaRecepcion} onClick={() => run(() => api(`/procesos/${p.id}/recepcion`, { body: { fechaRecepcion: rec.fechaRecepcion, observacion: rec.observacion || undefined } }), 'Acta de recepción generada.')}>Registrar recepción y generar acta</Button>
          </div>
        )}
        {msg && <Alert tipo={msg.tipo}>{msg.t}</Alert>}
      </CardContent>
    </Card>
  );
}

export function ExpedientePanel({ p, puedeCompilar, refresco }: { p: Proceso; puedeCompilar: boolean; refresco: number }) {
  const [docs, setDocs] = useState<Documento[]>([]);
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; t: string } | null>(null);
  const [tipoSubida, setTipoSubida] = useState('OTRO');
  const cargar = () => api<Documento[]>(`/procesos/${p.id}/documentos`).then(setDocs);
  useEffect(() => { cargar().catch(() => undefined); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [p.id, refresco]);
  const compilar = async () => { setMsg(null); try { const r = await api<{ hashExpediente: string; folios: number; documentos: number }>(`/procesos/${p.id}/expediente`, { method: 'POST' }); setMsg({ tipo: 'ok', t: `Expediente compilado: ${r.documentos} documentos, ${r.folios} folios. Sello ${r.hashExpediente.slice(0, 16)}…` }); await cargar(); } catch (e) { setMsg({ tipo: 'error', t: (e as Error).message }); } };
  const subir = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    const form = new FormData(); form.append('tipo', tipoSubida); form.append('archivo', file);
    setMsg(null); try { await api(`/procesos/${p.id}/documentos/subir`, { form }); await cargar(); setMsg({ tipo: 'ok', t: 'Documento adjuntado con hash SHA-256.' }); } catch (er) { setMsg({ tipo: 'error', t: (er as Error).message }); } finally { e.target.value = ''; }
  };
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-2">
        <div><CardTitle>Carpeta digital de auditoría</CardTitle><CardDescription>Cada documento es inmutable y versionado; el hash SHA-256 y el QR permiten verificar autenticidad.</CardDescription></div>
        {puedeCompilar && <Button onClick={compilar} data-testid="btn-expediente"><PackageCheck className="h-4 w-4" />Compilar expediente único</Button>}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Table>
          <THead><TR><TH>Documento</TH><TH>Versión</TH><TH>Págs.</TH><TH>Origen</TH><TH>SHA-256</TH><TH>Fecha</TH><TH /></TR></THead>
          <tbody>
            {docs.map((d) => (
              <TR key={d.id}>
                <TD className="font-medium"><FileText className="mr-1 inline h-4 w-4 text-muted-foreground" />{etiqueta(d.tipoDocumento)}</TD><TD>v{d.version}</TD><TD>{d.paginas ?? '—'}</TD>
                <TD>{d.generado ? <Badge variant="secondary">Generado</Badge> : <Badge variant="outline">Adjunto</Badge>}</TD><TD className="font-mono text-[11px]" title={d.hashSha256}>{d.hashSha256.slice(0, 20)}…</TD><TD>{fecha(d.creadoEn)}</TD>
                <TD><Button asChild variant="ghost" size="icon" aria-label="Descargar"><a href={`/api/documentos/${d.id}/descargar`} target="_blank" rel="noreferrer"><Download className="h-4 w-4" /></a></Button></TD>
              </TR>
            ))}
            {docs.length === 0 && <TR><TD colSpan={7} className="py-6 text-center text-muted-foreground">Aún no hay documentos. Se emiten automáticamente al avanzar el flujo.</TD></TR>}
          </tbody>
        </Table>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Adjuntar PDF externo:</span>
          <select className="h-8 rounded-md border bg-card px-2 text-sm" value={tipoSubida} onChange={(e) => setTipoSubida(e.target.value)}><option value="OTRO">Otro</option><option value="DEVENGADO_C31">Devengado C-31</option><option value="ACTA_RECEPCION">Acta de recepción firmada</option><option value="CONTRATO">Contrato firmado</option></select>
          <input type="file" accept="application/pdf" onChange={subir} className="text-xs" />
        </div>
        {msg && <Alert tipo={msg.tipo}>{msg.t}</Alert>}
      </CardContent>
    </Card>
  );
}
