'use client';
import { Check, ClipboardCopy, Plus, Save, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/form';
import { Table, TD, TH, THead, TR } from '@/components/ui/table';
import { api } from '@/lib/api';
import { Proceso } from '@/lib/types';
import { bs, cn } from '@/lib/utils';

interface Linea { da: string; ue: string; programa: string; proyecto: string; actividadObra: string; fuente: string; organismo: string; partida: string; importe: number }
interface Captura { defaults: { da: string; ue: string }; lineas: (Linea & { c31?: string | null })[]; glosa: string; bloque: string; validacion: { valido: boolean; errores: string[]; totalCertificado: number; totalItems: number; porPartida: { partida: string; items: number; certificado: number; diferencia: number }[] } }
const CAMPOS: { k: keyof Linea; l: string; w: string }[] = [{ k: 'da', l: 'DA', w: 'w-16' }, { k: 'ue', l: 'UE', w: 'w-16' }, { k: 'programa', l: 'Prog.', w: 'w-16' }, { k: 'proyecto', l: 'Proy.', w: 'w-20' }, { k: 'actividadObra', l: 'Act./Obra', w: 'w-20' }, { k: 'fuente', l: 'Fte.', w: 'w-16' }, { k: 'organismo', l: 'Org.', w: 'w-20' }, { k: 'partida', l: 'Partida', w: 'w-24' }];
const centavos = (n: number) => Math.round(n * 100);

async function copiar(texto: string) {
  try { await navigator.clipboard.writeText(texto); return true; } catch {
    const t = document.createElement('textarea'); t.value = texto; document.body.appendChild(t); t.select();
    const ok = document.execCommand('copy'); t.remove(); return ok;
  }
}
function BotonCopiar({ texto, etiqueta, className }: { texto: string; etiqueta?: string; className?: string }) {
  const [ok, setOk] = useState(false);
  return <Button type="button" variant="outline" size={etiqueta ? 'sm' : 'icon'} className={className} aria-label={`Copiar ${etiqueta ?? texto}`} onClick={async () => { setOk(await copiar(texto)); setTimeout(() => setOk(false), 1500); }}>{ok ? <Check className="h-3.5 w-3.5 text-success" /> : <ClipboardCopy className="h-3.5 w-3.5" />}{etiqueta}</Button>;
}

/** Pestaña "Captura SIGEP": espejo del C-31 con validación aritmética en vivo y copia por campo o por bloque. */
export function SigepCaptura({ p, editable, onCambio }: { p: Proceso; editable: boolean; onCambio: () => void }) {
  const [cap, setCap] = useState<Captura | null>(null);
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [c31, setC31] = useState('');
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; t: string } | null>(null);
  const cargar = () => api<Captura>(`/procesos/${p.id}/sigep`).then((c) => {
    setCap(c);
    setLineas(c.lineas.length ? c.lineas.map(({ c31: _x, ...l }) => l) : [{ da: c.defaults.da, ue: c.defaults.ue, programa: '', proyecto: '', actividadObra: '', fuente: '', organismo: '', partida: p.items[0]?.partidaGasto ?? '', importe: p.precioReferencialTotal }]);
    setC31(c.lineas.find((l) => l.c31)?.c31 ?? '');
  });
  useEffect(() => { cargar().catch((e) => setMsg({ tipo: 'error', t: e.message })); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [p.id, p.estadoFlujo]);

  // Validación aritmética en vivo (misma regla que el servidor): total y por partida, en centavos exactos
  const vivo = useMemo(() => {
    const total = lineas.reduce((a, l) => a + centavos(l.importe || 0), 0);
    const partidas = [...new Set([...p.items.map((i) => i.partidaGasto), ...lineas.map((l) => l.partida)])].filter(Boolean).sort();
    const filas = partidas.map((pt) => ({ pt, items: p.items.filter((i) => i.partidaGasto === pt).reduce((a, i) => a + centavos(i.precioTotal), 0), cert: lineas.filter((l) => l.partida === pt).reduce((a, l) => a + centavos(l.importe || 0), 0) }));
    const formatoOk = lineas.every((l) => /^\d{5}$/.test(l.partida));
    return { total, filas, cuadra: total === centavos(p.precioReferencialTotal) && filas.every((f) => f.items === f.cert) && formatoOk };
  }, [lineas, p.items, p.precioReferencialTotal]);

  const cambiar = (i: number, k: keyof Linea, v: string) => setLineas(lineas.map((l, j) => (j === i ? { ...l, [k]: k === 'importe' ? Number(v) : v } : l)));
  async function guardar() {
    setMsg(null);
    try { await api(`/procesos/${p.id}/presupuesto`, { method: 'PUT', body: { lineas, c31PreventivoNumero: c31 || undefined } }); await cargar(); setMsg({ tipo: 'ok', t: 'Certificación guardada y validada contra los ítems.' }); onCambio(); } catch (e) { setMsg({ tipo: 'error', t: (e as Error).message }); }
  }
  const l0 = lineas[0];
  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader><CardTitle>Certificación presupuestaria · Preventivo C-31</CardTitle><CardDescription>Estructura programática y partida. Los importes deben cuadrar con los ítems, por partida y en total.</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Table>
            <THead><TR>{CAMPOS.map((c) => <TH key={c.k}>{c.l}</TH>)}<TH className="text-right">Importe (Bs)</TH><TH /></TR></THead>
            <tbody>
              {lineas.map((l, i) => (
                <TR key={i}>
                  {CAMPOS.map((c) => <TD key={c.k}><Input disabled={!editable} aria-label={`${c.l} línea ${i + 1}`} className={cn('h-8 px-2', c.w)} value={l[c.k] as string} onChange={(e) => cambiar(i, c.k, e.target.value)} /></TD>)}
                  <TD><Input disabled={!editable} aria-label={`Importe línea ${i + 1}`} className="tabular h-8 w-32 px-2 text-right" type="number" step="0.01" value={l.importe} onChange={(e) => cambiar(i, 'importe', e.target.value)} /></TD>
                  <TD>{editable && lineas.length > 1 && <Button variant="ghost" size="icon" aria-label="Quitar línea" onClick={() => setLineas(lineas.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button>}</TD>
                </TR>
              ))}
              <TR className="bg-muted/40 font-semibold"><TD colSpan={8} className="text-right">Total certificado</TD><TD className="tabular text-right" data-testid="total-certificado">{bs(vivo.total / 100)}</TD><TD /></TR>
            </tbody>
          </Table>
          {editable && (
            <div className="flex flex-wrap items-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setLineas([...lineas, { da: cap?.defaults.da ?? '', ue: cap?.defaults.ue ?? '', programa: l0?.programa ?? '', proyecto: l0?.proyecto ?? '', actividadObra: l0?.actividadObra ?? '', fuente: l0?.fuente ?? '', organismo: l0?.organismo ?? '', partida: '', importe: 0 }])}><Plus className="h-4 w-4" />Línea</Button>
              <Field label="N° Preventivo C-31 (SIGEP)"><Input className="w-44" value={c31} onChange={(e) => setC31(e.target.value)} placeholder="Se completa tras registrar" /></Field>
              <Button onClick={guardar} data-testid="btn-guardar-c31"><Save className="h-4 w-4" />Guardar certificación</Button>
            </div>
          )}
          <Alert tipo={vivo.cuadra ? 'ok' : 'warn'} data-testid="estado-cuadre">
            {vivo.cuadra ? 'Los importes cuadran con los ítems en total y por partida.' : 'Los importes aún no cuadran con los ítems (revise total, partidas de 5 dígitos y formato).'}
            <ul className="mt-1 text-xs">{vivo.filas.map((f) => <li key={f.pt} className={f.items === f.cert ? '' : 'font-semibold'}>Partida {f.pt}: ítems {bs(f.items / 100)} · certificado {bs(f.cert / 100)}</li>)}</ul>
          </Alert>
          {cap && !cap.validacion.valido && cap.lineas.length > 0 && <Alert tipo="error"><b>Validación del servidor:</b><ul className="list-disc pl-4 text-xs">{cap.validacion.errores.map((e, i) => <li key={i}>{e}</li>)}</ul></Alert>}
          {msg && <Alert tipo={msg.tipo}>{msg.t}</Alert>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Captura SIGEP · interfaz espejo</CardTitle><CardDescription>Copie campo por campo o todo el bloque para transcribirlo al comprobante C-31.</CardDescription></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col gap-3">
          {l0 && (
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-sm">
              {CAMPOS.map((c) => <div key={c.k} className="flex items-center justify-between gap-2 rounded border bg-muted/30 px-2 py-1"><dt className="text-xs text-muted-foreground">{c.l}</dt><dd className="flex items-center gap-1 font-mono">{l0[c.k] as string || '—'}<BotonCopiar texto={String(l0[c.k] ?? '')} /></dd></div>)}
              <div className="col-span-2 flex items-center justify-between rounded border bg-muted/30 px-2 py-1"><dt className="text-xs text-muted-foreground">Importe</dt><dd className="flex items-center gap-1 font-mono">{vivo.total / 100}<BotonCopiar texto={(vivo.total / 100).toFixed(2)} /></dd></div>
            </dl>
          )}
          <div className="rounded border bg-muted/30 p-2"><div className="mb-1 flex items-center justify-between"><span className="text-xs text-muted-foreground">Glosa estandarizada</span>{cap && <BotonCopiar texto={cap.glosa} />}</div><p className="break-words font-mono text-xs">{cap?.glosa}</p></div>
          </div>
          <div className="flex flex-col gap-3">
          <Button disabled={!cap?.bloque || !cap.validacion.valido} onClick={async () => { await copiar(cap!.bloque); setMsg({ tipo: 'ok', t: 'Bloque copiado al portapapeles.' }); }} data-testid="btn-copiar-bloque"><ClipboardCopy className="h-4 w-4" />Copiar bloque para SIGEP</Button>
          {cap && !cap.validacion.valido && <p className="text-xs text-muted-foreground">El bloque se habilita cuando la certificación guardada cuadra aritméticamente.</p>}
          {cap?.bloque && <pre className="max-h-56 overflow-auto rounded border bg-muted/40 p-2 text-[11px] leading-snug">{cap.bloque}</pre>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
