import { useState } from 'react';
import { abrirDocumento, abrirReporte, get } from '../../api';
import { Card, DataTable, PageHead, SelectField, TextField, useLoad } from '../../ui';
import { optsAmb, optsAux, optsCta, optsEdif, useAfMeta } from './common';

export default function AfConsulta() {
  const { data: meta } = useAfMeta();
  const [q, setQ] = useState<Record<string, string>>({});
  const { data: lista } = useLoad<any[]>(() => get('/af/activos', { ...q, limite: 1000 }), [JSON.stringify(q)]);
  const [cod, setCod] = useState('');
  const { data: kx } = useLoad<any[]>(() => (cod ? get(`/af/activos/${encodeURIComponent(cod)}/kardex`) : Promise.resolve([])), [cod]);
  return (
    <>
      <PageHead title="Consulta de activos fijos y kardex" sub="Inventarios, informes y consultas (Procedimiento 5): cada viernes se remite a Contabilidad el informe de movimientos" />
      <Card title="Informes">
        <div className="row">
          <button onClick={() => abrirReporte('af-contabilidad', 'pdf', {})}>Movimientos a Contabilidad (PDF)</button>
          <button onClick={() => abrirReporte('af-resumen-cuentas', 'pdf', {})}>Resumen por cuentas</button>
          <button onClick={() => abrirReporte('af-incompletos', 'pdf', {})}>Registros incompletos</button>
          <button className="ok" onClick={() => abrirReporte('af-inventario-general', 'xlsx', {})}>Exportar inventario (Excel)</button>
          <span className="muted">Inventario por funcionario / ubicación: Reportes y documentos → Activos fijos.</span>
        </div>
      </Card>
      <Card>
        <div className="row">
          <TextField label="Código o descripción" value={q.texto} onChange={(v) => setQ({ ...q, texto: v })} />
          <SelectField label="Situación" value={q.situacion} onChange={(v) => setQ({ ...q, situacion: v })} options={['EN ALMACEN', 'ASIGNADO', 'BAJA']} />
          <SelectField label="Funcionario" value={q.funcionario} onChange={(v) => setQ({ ...q, funcionario: v })} options={(meta?.funcionarios ?? []).map((f) => f.nombre)} />
          <SelectField label="Edificio" value={q.cod_edif} onChange={(v) => setQ({ ...q, cod_edif: v, cod_amb: '' })} options={optsEdif(meta)} />
          <SelectField label="Ambiente" value={q.cod_amb} onChange={(v) => setQ({ ...q, cod_amb: v })} options={optsAmb(meta, q.cod_edif)} disabled={!q.cod_edif} />
          <SelectField label="Cuenta" value={q.id_cta} onChange={(v) => setQ({ ...q, id_cta: v, id_aux: '' })} options={optsCta(meta)} />
          <SelectField label="Auxiliar" value={q.id_aux} onChange={(v) => setQ({ ...q, id_aux: v })} options={optsAux(meta, q.id_cta)} disabled={!q.id_cta} />
        </div>
      </Card>
      <div className="split" style={{ gridTemplateColumns: '1.4fr minmax(0,1fr)' }}>
        <DataTable maxHeight="60vh" rows={lista ?? []} onRow={(r) => setCod(r.codigo)} selected={(r) => r.codigo === cod} cols={[{ key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' }, { key: 'funcionario', header: 'Funcionario' }, { key: 'valor', header: 'Valor Bs', money: true }, { key: 'situacion', header: 'Situación', badge: true }]} />
        <Card title={cod ? `Kardex ${cod}` : 'Kardex del activo'} right={cod ? <button className="sm" onClick={() => abrirDocumento('af-ficha', cod)}>Ficha PDF</button> : undefined}>
          {cod ? <DataTable rows={kx ?? []} cols={[{ key: 'fecha', header: 'Fecha', date: true }, { key: 'tipo', header: 'Movimiento' }, { key: 'documento', header: 'Documento' }, { key: 'destino', header: 'Destino' }]} /> : <div className="empty">Seleccione un activo.</div>}
        </Card>
      </div>
      <small className="muted">{lista?.length ?? 0} activo(s)</small>
    </>
  );
}
