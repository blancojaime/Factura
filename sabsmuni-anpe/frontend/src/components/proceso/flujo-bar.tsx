'use client';
import { Check } from 'lucide-react';
import { useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/form';
import { api } from '@/lib/api';
import { Transicion } from '@/lib/types';
import { cn, etiqueta } from '@/lib/utils';

export const PASOS = ['BORRADOR', 'REQUERIMIENTO_VALIDADO', 'PRESUPUESTO_CERTIFICADO', 'DBC_ELABORADO', 'DBC_APROBADO', 'PUBLICADO', 'EVALUACION', 'RECOMENDACION_EMITIDA', 'ADJUDICADO', 'CONTRATO_FORMALIZADO', 'RECEPCION', 'LIQUIDADO'];
const variante = (e: string) => (e === 'LIQUIDADO' || e === 'ADJUDICADO' ? 'success' : e === 'DESIERTO' || e === 'CANCELADO' ? 'destructive' : e === 'BORRADOR' ? 'secondary' : 'default') as 'success' | 'destructive' | 'secondary' | 'default';
export const EstadoBadge = ({ estado }: { estado: string }) => <Badge variant={variante(estado)}>{etiqueta(estado)}</Badge>;

/** Línea de tiempo del flujo + botones de transición habilitados según rol y precondiciones. */
export function FlujoBar({ id, estado, transiciones, onCambio }: { id: string; estado: string; transiciones: Transicion[]; onCambio: () => void }) {
  const [error, setError] = useState('');
  const [obs, setObs] = useState('');
  const idx = PASOS.indexOf(estado);
  async function ir(hacia: string) {
    setError('');
    try { await api(`/procesos/${id}/transicion`, { body: { hacia, observacion: obs || undefined } }); setObs(''); onCambio(); } catch (e) { setError((e as Error).message); }
  }
  const requiereObs = (h: string) => h === 'DESIERTO' || h === 'CANCELADO';
  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card p-3">
      <ol className="flex flex-wrap gap-x-1 gap-y-2 text-xs">
        {PASOS.map((p, i) => (
          <li key={p} className={cn('flex items-center gap-1 rounded-full px-2 py-1', i < idx && 'bg-success/15 text-success', i === idx && 'bg-primary font-semibold text-primary-foreground', i > idx && 'bg-muted text-muted-foreground')}>
            {i < idx && <Check className="h-3 w-3" />}{etiqueta(p)}
          </li>
        ))}
        {['DESIERTO', 'CANCELADO'].includes(estado) && <li className="rounded-full bg-destructive px-2 py-1 font-semibold text-destructive-foreground">{etiqueta(estado)}</li>}
      </ol>
      <div className="flex flex-wrap items-start gap-2">
        {transiciones.map((t) => (
          <div key={t.hacia} className="flex flex-col gap-1">
            <Button size="sm" variant={t.hacia === 'CANCELADO' || t.hacia === 'DESIERTO' ? 'outline' : 'default'} disabled={!t.permitido} onClick={() => ir(t.hacia)} title={t.motivos.join(' · ')} data-testid={`paso-${t.hacia}`}>
              {t.hacia === 'CANCELADO' ? 'Cancelar proceso' : `→ ${etiqueta(t.hacia)}`}
            </Button>
            {!t.permitido && t.motivos[0] && !t.motivos[0].startsWith('Transición no permitida') && !t.motivos[0].startsWith('El rol') && <span className="max-w-[260px] text-[11px] leading-tight text-muted-foreground">{t.motivos.join(' · ')}</span>}
          </div>
        ))}
        {transiciones.some((t) => requiereObs(t.hacia) && t.permitido) && <Input className="h-8 max-w-sm" placeholder="Fundamento (obligatorio al declarar desierto / cancelar)" value={obs} onChange={(e) => setObs(e.target.value)} />}
      </div>
      {error && <Alert tipo="error">{error}</Alert>}
    </div>
  );
}
