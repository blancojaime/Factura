import { get, post } from '../../api';
import { useAuth } from '../../auth';
import { Badge, Card, DataTable, PageHead, useAction, useLoad, useUi } from '../../ui';

export default function AlmCierre() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data, reload } = useLoad<any[]>(() => get('/alm/cierre'));
  const [run, busy] = useAction();
  const crit = (data ?? []).filter((c) => c.critico && c.resultado === 'OBSERVADO').length;
  return (
    <>
      <PageHead title="Cierre de gestión y apertura de nueva gestión" sub="Inventario anual · corte de documentación · saldos de apertura"><button onClick={reload}>Verificar nuevamente</button></PageHead>
      <Card title="Verificaciones previas al cierre">
        <DataTable rows={data ?? []} cols={[{ key: 'n', header: 'N°', ctr: true }, { key: 'control', header: 'Control' }, { key: 'resultado', header: 'Resultado', render: (r) => <span><Badge v={r.resultado === 'OK' ? 'CUMPLE' : 'NO CUMPLE'} /> {r.critico && <small className="muted">crítico</small>}</span> }, { key: 'detalle', header: 'Detalle' }]} />
        {crit > 0 && <div className="alert critico" style={{ marginTop: 10 }}>Hay {crit} control(es) crítico(s) observado(s). Regularice antes de generar la nueva gestión.</div>}
      </Card>
      {puede('alm') && (
        <Card title="Generar nueva gestión">
          <p>Se trasladan los saldos de existencias de fin de gestión como <b>saldo inicial</b> (conservando lote, vencimiento y costo) y se reinicia la numeración de documentos. Realice una copia de seguridad antes de continuar.</p>
          <button className="primary" disabled={busy || crit > 0} onClick={async () => { if (await ui.confirm('¿Cerrar la gestión actual y abrir la siguiente? Esta operación no puede revertirse.')) run(async () => { const r = await post('/alm/cierre/nueva-gestion'); ui.ok(`Gestión ${r.gestion} abierta: ${r.lotes} lotes trasladados como saldo inicial.`); reload(); }); }}>Cerrar gestión y abrir nueva</button>
        </Card>
      )}
    </>
  );
}
