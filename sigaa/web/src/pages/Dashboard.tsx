import { Link } from 'react-router-dom';
import { get, fmt2, fmtN } from '../api';
import { Card, Kpi, Loading, PageHead, useLoad, DataTable } from '../ui';

const MES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

export default function Dashboard() {
  const { data: d, loading, reload } = useLoad(() => get('/dashboard'));
  if (!d) return <Loading on={loading} />;
  const a = d.almacenes, c = d.combustible, f = d.activos;
  const max = Math.max(1, ...c.mensual.map((m: any) => m.gasolina + m.diesel));
  return (
    <>
      <PageHead title="Tablero general" sub={`Gestión ${d.gestion} · Resumen de los tres módulos`}><button onClick={reload}>Actualizar</button></PageHead>
      <Card title="Alertas que requieren atención">
        {d.alertas.length === 0 && <div className="alert ok">Sin alertas pendientes.</div>}
        {d.alertas.map((x: any, i: number) => (
          <div key={i} className={'alert ' + x.nivel}><b style={{ minWidth: 92 }}>{x.modulo === 'alm' ? 'ALMACENES' : x.modulo === 'com' ? 'COMBUSTIBLE' : 'ACTIVOS'}</b><span style={{ flex: 1 }}>{x.texto}</span>{x.ruta && <Link to={x.ruta}>Ir →</Link>}</div>
        ))}
      </Card>
      <h2>Almacenes</h2>
      <div className="kpis">
        <Kpi mod="alm" label="Ítems en catálogo" value={a.items} />
        <Kpi mod="alm" label="Valor existencias (Bs)" value={fmt2(a.valor_existencias)} />
        <Kpi mod="alm" tone={a.bajo_minimo ? 'warn' : undefined} label="Bajo stock mínimo" value={a.bajo_minimo} />
        <Kpi mod="alm" tone={a.por_vencer ? 'warn' : undefined} label="Lotes por vencer" value={a.por_vencer} />
        <Kpi mod="alm" tone={a.vencidos ? 'bad' : undefined} label="Lotes vencidos" value={a.vencidos} />
        <Kpi mod="alm" label="Pedidos pendientes" value={a.pedidos_pendientes} />
        <Kpi mod="alm" label="Ingresos sin confirmar" value={a.ingresos_sin_confirmar} />
        <Kpi mod="alm" label="Bajas en trámite" value={a.bajas_en_tramite} />
      </div>
      <h2>Combustible</h2>
      <div className="kpis">
        <Kpi mod="com" label="Monto emitido (Bs)" value={fmt2(c.monto_emitido)} />
        <Kpi mod="com" label="Litros emitidos" value={fmtN(c.litros_emitidos)} />
        <Kpi mod="com" label="Emisiones" value={c.emisiones} />
        <Kpi mod="com" label="Vales disponibles (Bs)" value={fmt2(c.vales_disponibles_bs)} />
        <Kpi mod="com" label="Saldo de contratos (Bs)" value={fmt2(c.saldo_contratos)} />
        <Kpi mod="com" tone={c.descargos_vencidos ? 'bad' : undefined} label="Descargos vencidos" value={c.descargos_vencidos} />
      </div>
      <div className="grid c2">
        <Card title="Emisión mensual de vales (Bs)">
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 130 }}>
            {c.mensual.map((m: any) => (
              <div key={m.mes} style={{ flex: 1, textAlign: 'center' }} title={`Gasolina ${fmt2(m.gasolina)} · Diésel ${fmt2(m.diesel)}`}>
                <div style={{ height: 100, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
                  <div style={{ height: (m.diesel / max) * 100, background: '#b7791f' }} />
                  <div style={{ height: (m.gasolina / max) * 100, background: '#2d5a94' }} />
                </div>
                <small className="muted">{MES[m.mes - 1]}</small>
              </div>
            ))}
          </div>
          <small className="muted"><span style={{ color: '#2d5a94' }}>■</span> Gasolina &nbsp; <span style={{ color: '#b7791f' }}>■</span> Diésel</small>
        </Card>
        <Card title="Ejecución por apertura programática">
          <DataTable rows={c.aperturas} cols={[{ key: 'apertura', header: 'Apertura' }, { key: 'presupuesto', header: 'Presup.', money: true }, { key: 'ejecutado', header: 'Ejecutado', money: true }, { key: 'porcentaje', header: '%', num: true }]} maxHeight={200} />
        </Card>
      </div>
      <h2>Activos fijos</h2>
      <div className="kpis">
        <Kpi mod="af" label="Total de activos" value={f.total} />
        <Kpi mod="af" label="En almacén" value={f.en_almacen} />
        <Kpi mod="af" label="Asignados" value={f.asignados} />
        <Kpi mod="af" label="Dados de baja" value={f.bajas} />
        <Kpi mod="af" label="Valor total (Bs)" value={fmt2(f.valor_total)} />
        <Kpi mod="af" label="Stickers pendientes" value={f.stickers_pendientes} />
        <Kpi mod="af" label="Sin fotografía" value={f.sin_fotografia} />
        <Kpi mod="af" label="Solicitudes pendientes" value={f.solicitudes_pendientes} />
      </div>
    </>
  );
}
