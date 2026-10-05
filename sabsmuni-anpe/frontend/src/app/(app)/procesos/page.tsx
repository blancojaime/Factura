'use client';
import { Plus } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { EstadoBadge } from '@/components/proceso/flujo-bar';
import { useSession } from '@/components/session';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input, Select, Textarea } from '@/components/ui/form';
import { Table, TD, TH, THead, TR } from '@/components/ui/table';
import { api } from '@/lib/api';
import { bs, etiqueta, fecha } from '@/lib/utils';

interface Fila { id: string; codigo: string; objetoContratacion: string; tipoObjeto: string; precioReferencialTotal: number; estadoFlujo: string; creadoEn: string; solicitante: { nombre: string } }

export default function Procesos() {
  const { rol } = useSession();
  const router = useRouter();
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [nuevo, setNuevo] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ objetoContratacion: '', tipoObjeto: 'BIENES', metodoSeleccion: 'PRECIO_EVALUADO_MAS_BAJO', plazoEjecucionDias: 15 });

  useEffect(() => { api<Fila[]>('/procesos').then(setFilas).catch((e) => setError(e.message)); }, []);
  async function crear(e: React.FormEvent) {
    e.preventDefault(); setError('');
    try { const p = await api<{ id: string }>('/procesos', { body: form }); router.push(`/procesos/${p.id}`); } catch (err) { setError((err as Error).message); }
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-semibold">Procesos de contratación ANPE</h1><p className="text-sm text-muted-foreground">Cuantías de Bs 50.001 a Bs 1.000.000 · Bienes, Servicios Generales y Obras</p></div>
        {rol === 'UNIDAD_SOLICITANTE' && <Button onClick={() => setNuevo(!nuevo)}><Plus className="h-4 w-4" />Nueva solicitud</Button>}
      </div>
      {error && <Alert tipo="error">{error}</Alert>}
      {nuevo && (
        <Card>
          <CardHeader><CardTitle>Nueva solicitud de contratación</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={crear} className="grid gap-3 md:grid-cols-4">
              <Field label="Objeto de contratación" className="md:col-span-4"><Textarea required minLength={10} className="min-h-[70px]" value={form.objetoContratacion} onChange={(e) => setForm({ ...form, objetoContratacion: e.target.value })} placeholder="Ej.: Adquisición de lote de cemento para pavimento" /></Field>
              <Field label="Tipo de objeto"><Select value={form.tipoObjeto} onChange={(e) => setForm({ ...form, tipoObjeto: e.target.value })}><option value="BIENES">Bienes</option><option value="SERVICIOS">Servicios generales</option><option value="OBRAS">Obras</option></Select></Field>
              <Field label="Método de selección"><Select value={form.metodoSeleccion} onChange={(e) => setForm({ ...form, metodoSeleccion: e.target.value })}><option value="PRECIO_EVALUADO_MAS_BAJO">Precio evaluado más bajo</option><option value="CALIDAD_PROPUESTA_COSTO">Calidad, propuesta técnica y costo</option></Select></Field>
              <Field label="Plazo de entrega/ejecución (días calendario)"><Input type="number" min={1} value={form.plazoEjecucionDias} onChange={(e) => setForm({ ...form, plazoEjecucionDias: Number(e.target.value) })} /></Field>
              <div className="flex items-end"><Button type="submit" className="w-full">Crear borrador</Button></div>
            </form>
          </CardContent>
        </Card>
      )}
      <Table>
        <THead><TR><TH>Código</TH><TH>Objeto</TH><TH>Tipo</TH><TH className="text-right">Precio referencial</TH><TH>Estado</TH><TH>Creado</TH></TR></THead>
        <tbody>
          {filas?.map((p) => (
            <TR key={p.id}>
              <TD className="whitespace-nowrap font-medium"><Link className="text-primary underline-offset-2 hover:underline" href={`/procesos/${p.id}`}>{p.codigo}</Link></TD>
              <TD className="max-w-md">{p.objetoContratacion}</TD><TD>{etiqueta(p.tipoObjeto)}</TD>
              <TD className="tabular text-right">{bs(p.precioReferencialTotal)}</TD><TD><EstadoBadge estado={p.estadoFlujo} /></TD><TD>{fecha(p.creadoEn)}</TD>
            </TR>
          ))}
          {filas?.length === 0 && <TR><TD colSpan={6} className="py-8 text-center text-muted-foreground">Aún no hay procesos.</TD></TR>}
          {!filas && <TR><TD colSpan={6} className="py-8 text-center text-muted-foreground">Cargando…</TD></TR>}
        </tbody>
      </Table>
    </div>
  );
}
