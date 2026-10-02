import { useEffect, useState } from 'react';
import { abrirReporte, fmt2, get, hoy, put } from '../../api';
import { useAuth } from '../../auth';
import { Card, ItemsGrid, PageHead, useAction } from '../../ui';
import { DateField } from '../../ui';
import { useComMeta } from './common';

const lin = () => ({ placa: '', obra: '', apertura: '', dias: '', km_horas: '', responsable: '', observaciones: '', litros_estimados: '' });
export default function ComCronograma() {
  const { puede } = useAuth();
  const { data: meta } = useComMeta();
  const [mes, setMes] = useState(hoy().slice(0, 7) + '-01');
  const [filas, setFilas] = useState<any[]>([lin()]);
  const [run, busy] = useAction();
  const cargar = () => get('/com/cronograma', { mes }).then((r: any[]) => setFilas(r.length ? r.map((x) => ({ ...x, dias: x.dias ?? '', litros_estimados: x.litros_estimados ?? '' })) : [lin()]));
  useEffect(() => { cargar(); }, [mes]); // eslint-disable-line
  const operativos = (meta?.vehiculos ?? []).map((v) => ({ value: v.placa, label: `${v.placa} - ${v.tipo}` }));
  return (
    <>
      <PageHead title="Cronograma mensual de uso de maquinaria y vehículos operativos" sub="Programe km u horas por vehículo y obra; el sistema estima los litros con el rendimiento de referencia" />
      <Card>
        <div className="row"><DateField label="Mes" value={mes} onChange={(v) => setMes(v.slice(0, 7) + '-01')} /><button onClick={() => abrirReporte('com-cronograma', 'pdf', { mes })}>PDF</button><button onClick={() => abrirReporte('com-cronograma', 'xlsx', { mes })}>Excel</button></div>
      </Card>
      <Card title="Programación">
        <ItemsGrid rows={filas} onChange={setFilas} vacio={lin} cols={[
          { key: 'placa', header: 'Vehículo', type: 'select', options: operativos, width: 200 }, { key: 'obra', header: 'Obra / actividad' }, { key: 'apertura', header: 'Apertura', type: 'select', options: (meta?.aperturas ?? []).map((a) => a.apertura), width: 120 },
          { key: 'dias', header: 'Días', type: 'number', num: true, width: 70 }, { key: 'km_horas', header: 'Km u horas', type: 'number', num: true, width: 100 }, { key: 'litros_estimados', header: 'Litros est.', type: 'readonly', num: true }, { key: 'responsable', header: 'Responsable' },
        ]} />
        {puede('com') && <div style={{ marginTop: 10 }}><button className="primary" disabled={busy} onClick={() => run(async () => { await put('/com/cronograma', { mes, filas: filas.filter((f) => f.placa).map((f) => ({ ...f, dias: f.dias === '' ? undefined : Number(f.dias), km_horas: Number(f.km_horas) })) }); await cargar(); }, 'Cronograma guardado (litros recalculados).')}>Guardar cronograma</button></div>}
        <small className="muted">Total estimado: {fmt2(filas.reduce((t, f) => t + (Number(f.litros_estimados) || 0), 0))} L</small>
      </Card>
    </>
  );
}
