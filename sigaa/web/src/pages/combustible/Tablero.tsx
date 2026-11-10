import { get, fmt2, fmtN } from '../../api';
import { Card, DataTable, Kpi, PageHead, useLoad } from '../../ui';

const MES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
export default function ComTablero() {
  const { data: t } = useLoad<any>(() => get('/com/tablero'));
  const { data: v } = useLoad<any>(() => get('/com/resumen-vales'));
  const { data: tu } = useLoad<any[]>(() => get('/com/turriles'));
  if (!t) return null;
  const max = Math.max(1, ...t.mensual.map((m: any) => m.gasolina + m.diesel));
  return (
    <>
      <PageHead title="Tablero de control de combustible" sub={`Gestión ${t.gestion} · Reglamento Interno de Administración del Uso de Combustible`} />
      <div className="kpis">
        <Kpi mod="com" label="Monto emitido (Bs)" value={fmt2(t.monto_emitido)} /><Kpi mod="com" label="Litros emitidos" value={fmtN(t.litros_emitidos)} /><Kpi mod="com" label="Emisiones" value={t.emisiones} />
        <Kpi mod="com" label="Vales disponibles (Bs)" value={fmt2(t.vales_disponibles_bs)} /><Kpi mod="com" label="Saldo de contratos (Bs)" value={fmt2(t.saldo_contratos)} /><Kpi mod="com" tone={t.descargos_vencidos ? 'bad' : undefined} label="Descargos vencidos" value={t.descargos_vencidos} />
      </div>
      {v?.alertas.map((a: string, i: number) => <div key={i} className="alert aviso">{a}</div>)}
      <div className="grid c2">
        <Card title="Emisión mensual (Bs)">
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 150 }}>
            {t.mensual.map((m: any) => (
              <div key={m.mes} style={{ flex: 1, textAlign: 'center' }} title={`Gasolina ${fmt2(m.gasolina)} · Diésel ${fmt2(m.diesel)}`}>
                <div style={{ height: 120, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}><div style={{ height: (m.diesel / max) * 120, background: '#b7791f' }} /><div style={{ height: (m.gasolina / max) * 120, background: '#2d5a94' }} /></div>
                <small className="muted">{MES[m.mes - 1]}</small>
              </div>))}
          </div>
          <small className="muted"><span style={{ color: '#2d5a94' }}>■</span> Gasolina &nbsp; <span style={{ color: '#b7791f' }}>■</span> Diésel</small>
        </Card>
        <Card title="Vehículos con mayor consumo"><DataTable rows={t.top_vehiculos} cols={[{ key: 'placa', header: 'Placa / puesto' }, { key: 'monto', header: 'Monto Bs', money: true }]} /></Card>
        <Card title="Ejecución por apertura programática"><DataTable rows={t.aperturas} cols={[{ key: 'apertura', header: 'Apertura' }, { key: 'descripcion', header: 'Descripción' }, { key: 'presupuesto', header: 'Presup.', money: true }, { key: 'ejecutado', header: 'Ejecutado', money: true }, { key: 'porcentaje', header: '%', num: true }]} /></Card>
        <Card title="Vales en almacén por corte">
          <DataTable rows={v?.lista ?? []} cols={[{ key: 'combustible', header: 'Combustible' }, { key: 'corte', header: 'Corte Bs', num: true }, { key: 'Disponible', header: 'Disponibles', num: true }, { key: 'Entregado', header: 'Entregados', num: true }, { key: 'Utilizado', header: 'Utilizados', num: true }]} />
        </Card>
        <Card title="Combustible en turriles"><DataTable rows={tu ?? []} cols={[{ key: 'codigo', header: 'Puesto' }, { key: 'nombre', header: 'Nombre' }, { key: 'combustible', header: 'Comb.' }, { key: 'capacidad_l', header: 'Capac. L', num: true }, { key: 'saldo', header: 'Saldo L', num: true }, { key: 'costo_prom', header: 'Bs/L', money: true }]} /></Card>
      </div>
    </>
  );
}
