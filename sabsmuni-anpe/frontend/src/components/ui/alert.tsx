import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';
import * as React from 'react';
import { cn } from '@/lib/utils';

const estilos = { info: 'border-primary/30 bg-accent text-accent-foreground', ok: 'border-success/40 bg-success/10 text-success', warn: 'border-warning bg-warning/15 text-warning-foreground', error: 'border-destructive/40 bg-destructive/10 text-destructive' };
const iconos = { info: Info, ok: CheckCircle2, warn: AlertTriangle, error: XCircle };
export function Alert({ tipo = 'info', className, children, ...p }: { tipo?: keyof typeof estilos } & React.HTMLAttributes<HTMLDivElement>) {
  const I = iconos[tipo];
  return <div role={tipo === 'error' ? 'alert' : 'status'} className={cn('flex gap-2 rounded-md border px-3 py-2 text-sm', estilos[tipo], className)} {...p}><I className="mt-0.5 h-4 w-4 shrink-0" /><div className="min-w-0 flex-1">{children}</div></div>;
}
