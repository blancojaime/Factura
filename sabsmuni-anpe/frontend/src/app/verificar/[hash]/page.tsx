'use client';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/lib/api';
import { etiqueta, fecha } from '@/lib/utils';

interface Res { valido: boolean; mensaje: string; tipoDocumento?: string; version?: number; proceso?: string; objeto?: string; generadoEn?: string; hashSha256?: string; paginas?: number }

/** Página pública a la que apunta el QR de cada documento. */
export default function Verificar() {
  const { hash } = useParams<{ hash: string }>();
  const [r, setR] = useState<Res | null>(null);
  useEffect(() => { api<Res>(`/verificar/${hash}`).then(setR).catch((e) => setR({ valido: false, mensaje: e.message })); }, [hash]);
  return (
    <main className="mx-auto flex min-h-screen max-w-xl items-center p-4">
      <Card className="w-full">
        <CardHeader><CardTitle className="flex items-center gap-2">{r?.valido ? <ShieldCheck className="h-6 w-6 text-success" /> : <ShieldAlert className="h-6 w-6 text-destructive" />}Verificación de documento</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          {!r && <p>Verificando…</p>}
          {r && <p className={r.valido ? 'font-medium text-success' : 'font-medium text-destructive'} data-testid="resultado-verificacion">{r.mensaje}</p>}
          {r?.proceso && <dl className="grid grid-cols-3 gap-1"><dt className="text-muted-foreground">Documento</dt><dd className="col-span-2">{etiqueta(r.tipoDocumento ?? '')} · v{r.version}</dd><dt className="text-muted-foreground">Proceso</dt><dd className="col-span-2">{r.proceso}</dd><dt className="text-muted-foreground">Objeto</dt><dd className="col-span-2">{r.objeto}</dd><dt className="text-muted-foreground">Generado</dt><dd className="col-span-2">{fecha(r.generadoEn)}</dd><dt className="text-muted-foreground">SHA-256</dt><dd className="col-span-2 break-all font-mono text-xs">{r.hashSha256}</dd></dl>}
        </CardContent>
      </Card>
    </main>
  );
}
