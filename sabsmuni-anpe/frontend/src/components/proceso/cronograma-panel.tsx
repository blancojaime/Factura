'use client';
import { CalendarClock } from 'lucide-react';
import { useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/form';
import { Table, TD, TH, THead, TR } from '@/components/ui/table';
import { api } from '@/lib/api';
import { Proceso } from '@/lib/types';
import { fecha } from '@/lib/utils';

interface Resultado { cronograma: Record<string, string>; plazoMinimoDiasHabiles: number; diasHabilesPublicacionApertura: number }
const FILAS: [string, string][] = [['fechaPublicacion', 'Publicación del DBC'], ['fechaApertura', 'Presentación y apertura de propuestas'], ['fechaAdjudicacion', 'Adjudicación / declaratoria desierta'], ['fechaPresentacionDoc', 'Presentación de documentos para formalizar'], ['fechaContrato', 'Suscripción de contrato / orden']];

/** Art. 47 D.S. 0181: 4 d.h. hasta Bs 200.000 · 8 d.h. de Bs 200.001 a Bs 1.000.000; sin fines de semana ni feriados. */
export function CronogramaPanel({ p, editable, onCambio }: { p: Proceso; editable: boolean; onCambio: () => void }) {
  const [pub, setPub] = useState(p.cronograma?.fechaPublicacion?.slice(0, 10) ?? '');
  const [ape, setApe] = useState('');
  const [res, setRes] = useState<Resultado | null>(null);
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; t: string } | null>(null);
  const minimo = p.precioReferencialTotal <= 200_000 ? 4 : 8;
  const body = { fechaPublicacion: pub, fechaApertura: ape || undefined };
  const simular = async () => { setMsg(null); try { setRes(await api<Resultado>(`/procesos/${p.id}/cronograma/calcular`, { body })); } catch (e) { setRes(null); setMsg({ tipo: 'error', t: (e as Error).message }); } };
  const guardar = async () => { setMsg(null); try { setRes(await api<Resultado>(`/procesos/${p.id}/cronograma`, { method: 'PUT', body })); setMsg({ tipo: 'ok', t: 'Cronograma guardado.' }); onCambio(); } catch (e) { setMsg({ tipo: 'error', t: (e as Error).message }); } };
  const mostrar = res?.cronograma ?? (p.cronograma as Record<string, string> | null);
  return (
    <Card>
      <CardHeader><CardTitle>Cronograma de plazos</CardTitle><CardDescription>Precio referencial {p.precioReferencialTotal.toLocaleString('es-BO')} Bs → plazo mínimo de <b>{minimo} días hábiles</b> entre publicación y apertura (Art. 47 D.S. 0181).</CardDescription></CardHeader>
      <CardContent className="flex flex-col gap-3">
        {editable && (
          <div className="flex flex-wrap items-end gap-2">
            <Field label="Fecha de publicación (día hábil)"><Input type="date" value={pub} onChange={(e) => setPub(e.target.value)} data-testid="fecha-publicacion" /></Field>
            <Field label="Apertura (opcional; mínimo legal si se omite)"><Input type="date" value={ape} onChange={(e) => setApe(e.target.value)} /></Field>
            <Button variant="outline" onClick={simular} disabled={!pub}><CalendarClock className="h-4 w-4" />Simular</Button>
            <Button onClick={guardar} disabled={!pub} data-testid="btn-guardar-cronograma">Guardar cronograma</Button>
          </div>
        )}
        {mostrar && (
          <Table><THead><TR><TH>Actividad</TH><TH>Fecha</TH></TR></THead><tbody>{FILAS.map(([k, l]) => <TR key={k}><TD>{l}</TD><TD className="tabular font-medium">{fecha(mostrar[k])}</TD></TR>)}</tbody></Table>
        )}
        {res && <Alert tipo="ok">Plazo publicación → apertura: {res.diasHabilesPublicacionApertura} días hábiles (mínimo legal {res.plazoMinimoDiasHabiles}). Feriados nacionales y los cargados por el administrador fueron excluidos.</Alert>}
        {msg && <Alert tipo={msg.tipo}>{msg.t}</Alert>}
      </CardContent>
    </Card>
  );
}
