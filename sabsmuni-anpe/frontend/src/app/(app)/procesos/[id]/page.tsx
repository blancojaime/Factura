'use client';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { ContratoPanel, ExpedientePanel } from '@/components/proceso/contrato-expediente';
import { CronogramaPanel } from '@/components/proceso/cronograma-panel';
import { EstadoBadge, FlujoBar } from '@/components/proceso/flujo-bar';
import { MatrizComparativa } from '@/components/proceso/matriz-comparativa';
import { RequerimientoAsistente } from '@/components/proceso/requerimiento-asistente';
import { SigepCaptura } from '@/components/proceso/sigep-captura';
import { useSession } from '@/components/session';
import { Alert } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/lib/api';
import { Proceso } from '@/lib/types';
import { bs, etiqueta } from '@/lib/utils';

export default function DetalleProceso() {
  const { id } = useParams<{ id: string }>();
  const { rol } = useSession();
  const [p, setP] = useState<Proceso | null>(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const cargar = useCallback(() => api<Proceso>(`/procesos/${id}`).then((x) => { setP(x); setVersion((v) => v + 1); }).catch((e) => setError(e.message)), [id]);
  useEffect(() => { cargar(); }, [cargar]);
  if (error) return <Alert tipo="error">{error}</Alert>;
  if (!p) return <p className="text-sm text-muted-foreground">Cargando proceso…</p>;

  const e = p.estadoFlujo;
  const US = rol === 'UNIDAD_SOLICITANTE', RP = rol === 'RESPONSABLE_PRESUPUESTO', RC = rol === 'RESPONSABLE_CONTRATACIONES', RPA = rol === 'AUTORIDAD_RPA';
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground"><span className="font-mono" data-testid="codigo-proceso">{p.codigo}</span><span>·</span><span>CUCE {p.cuceProvisorio}</span><EstadoBadge estado={e} /></div>
          <h1 className="text-xl font-semibold">{p.objetoContratacion}</h1>
          <p className="text-sm text-muted-foreground">{etiqueta(p.tipoObjeto)} · {etiqueta(p.metodoSeleccion)} · Precio referencial <b className="tabular text-foreground">{bs(p.precioReferencialTotal)}</b></p>
        </div>
      </div>
      <FlujoBar id={p.id} estado={e} transiciones={p.transiciones} onCambio={cargar} />
      {p.resolucionObs && <Alert tipo="info"><b>Resolución:</b> {p.resolucionObs}</Alert>}
      <Tabs defaultValue="requerimiento">
        <TabsList>
          <TabsTrigger value="requerimiento">1 · Requerimiento y CHB</TabsTrigger>
          <TabsTrigger value="sigep">2 · Captura SIGEP</TabsTrigger>
          <TabsTrigger value="cronograma">3 · Cronograma y DBC</TabsTrigger>
          <TabsTrigger value="evaluacion">4 · Evaluación</TabsTrigger>
          <TabsTrigger value="contrato">5 · Contrato</TabsTrigger>
          <TabsTrigger value="expediente">6 · Expediente</TabsTrigger>
        </TabsList>
        <TabsContent value="requerimiento"><RequerimientoAsistente p={p} editable={US && e === 'BORRADOR'} onCambio={cargar} /></TabsContent>
        <TabsContent value="sigep"><SigepCaptura p={p} editable={RP && e === 'REQUERIMIENTO_VALIDADO'} onCambio={cargar} /></TabsContent>
        <TabsContent value="cronograma"><CronogramaPanel p={p} editable={RC && ['PRESUPUESTO_CERTIFICADO', 'DBC_ELABORADO'].includes(e)} onCambio={cargar} /></TabsContent>
        <TabsContent value="evaluacion"><MatrizComparativa p={p} editable={RC && ['PUBLICADO', 'EVALUACION'].includes(e)} puedeEvaluar={RC && e === 'EVALUACION'} onCambio={cargar} /></TabsContent>
        <TabsContent value="contrato"><ContratoPanel p={p} puedeGenerar={(RC || RPA) && e === 'ADJUDICADO'} puedeRecibir={RC} onCambio={cargar} /></TabsContent>
        <TabsContent value="expediente"><ExpedientePanel p={p} puedeCompilar={RC || RPA} refresco={version} /></TabsContent>
      </Tabs>
    </div>
  );
}
