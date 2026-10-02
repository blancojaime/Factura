import { useState } from 'react';
import { abrirDocumento, get, hoy, post, fmt2 } from '../../api';
import { useAuth } from '../../auth';
import { Card, DataTable, DateField, PageHead, SelectField, TextField, useAction, useUi } from '../../ui';
import { optsAmb, optsEdif, useAfMeta } from './common';

export default function AfMovimientos() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useAfMeta();
  const [f, setF] = useState<any>({ tipo: 'DEVOLUCIÓN', fecha: hoy(), origen: '', destino: '', cod_edif: '', cod_amb: '', estado: '', motivo: '' });
  const [lista, setLista] = useState<any[]>([]);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [texto, setTexto] = useState('');
  const [run, busy] = useAction();
  const funcs = (meta?.funcionarios ?? []).map((x) => x.nombre);
  const cargar = () => run(async () => {
    const r = f.tipo === 'BAJA' ? await get('/af/activos', { texto, limite: 300 }).then((x: any[]) => x.filter((a) => a.situacion !== 'BAJA')) : await get(`/af/funcionarios/${encodeURIComponent(f.origen)}/activos`);
    setLista(r); setSel(new Set());
    if (!r.length) ui.error(`No se encontraron activos ${f.tipo === 'BAJA' ? 'para dar de baja' : 'asignados a ' + f.origen}.`);
  });
  const toggle = (c: string) => { const n = new Set(sel); n.has(c) ? n.delete(c) : n.add(c); setSel(n); };
  const info: Record<string, string> = { DEVOLUCIÓN: 'El activo vuelve a almacén.', TRANSFERENCIA: 'Cambia el funcionario responsable y, opcionalmente, la ubicación.', BAJA: 'Baja definitiva del activo (obsolescencia, siniestro, robo, deterioro...). Requiere la resolución correspondiente.' };
  const total = lista.filter((a) => sel.has(a.codigo)).reduce((t, a) => t + Number(a.valor), 0);
  return (
    <>
      <PageHead title="Devolución · Transferencia · Baja" sub="Movimientos posteriores a la asignación: cada operación genera su acta y actualiza el kardex del activo" />
      <Card title="1. Tipo de movimiento">
        <div className="grid">
          <SelectField label="Tipo" blank={false} req value={f.tipo} onChange={(v) => { setF({ ...f, tipo: v }); setLista([]); }} options={['DEVOLUCIÓN', 'TRANSFERENCIA', 'BAJA']} hint={info[f.tipo]} />
          <DateField label="Fecha" req value={f.fecha} onChange={(v) => setF({ ...f, fecha: v })} />
          {f.tipo !== 'BAJA' && <SelectField label={f.tipo === 'DEVOLUCIÓN' ? 'Funcionario que devuelve' : 'Funcionario ORIGEN'} req value={f.origen} onChange={(v) => setF({ ...f, origen: v })} options={funcs} />}
          {f.tipo === 'TRANSFERENCIA' && <SelectField label="Funcionario DESTINO" req value={f.destino} onChange={(v) => setF({ ...f, destino: v })} options={funcs} />}
          {f.tipo !== 'BAJA' && <><SelectField label="Edificio destino (opcional)" value={f.cod_edif} onChange={(v) => setF({ ...f, cod_edif: v, cod_amb: '' })} options={optsEdif(meta)} /><SelectField label="Ambiente destino" value={f.cod_amb} onChange={(v) => setF({ ...f, cod_amb: v })} options={optsAmb(meta, f.cod_edif)} disabled={!f.cod_edif} /></>}
          <SelectField label="Nuevo estado físico (opcional)" value={f.estado} onChange={(v) => setF({ ...f, estado: v })} options={(meta?.estados ?? []).map((e) => e.estado)} />
          <TextField className="span2" label={f.tipo === 'BAJA' ? 'Motivo de la baja' : 'Motivo / observaciones'} req={f.tipo === 'BAJA'} value={f.motivo} onChange={(v) => setF({ ...f, motivo: v })} />
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          {f.tipo === 'BAJA' && <TextField label="Buscar activo (código o descripción)" value={texto} onChange={setTexto} />}
          <button className="primary" disabled={busy} onClick={cargar}>Cargar activos</button>
        </div>
      </Card>
      {lista.length > 0 && (
        <Card title={`2. Marque los activos a procesar (${sel.size} · Bs ${fmt2(total)})`} right={<span className="row"><button className="sm" onClick={() => setSel(new Set(lista.map((a) => a.codigo)))}>Marcar todo</button><button className="sm" onClick={() => setSel(new Set())}>Desmarcar</button></span>}>
          <DataTable maxHeight="45vh" rows={lista} onRow={(r) => toggle(r.codigo)} cols={[{ key: 's', header: '', render: (r) => <input type="checkbox" readOnly checked={sel.has(r.codigo)} /> }, { key: 'codigo', header: 'Código' }, { key: 'auxiliar', header: 'Auxiliar' }, { key: 'descripcion', header: 'Descripción' }, { key: 'funcionario', header: 'Funcionario' }, { key: 'estado', header: 'Estado' }, { key: 'valor', header: 'Valor Bs', money: true }]} />
          {puede('af') && <div style={{ marginTop: 10 }}><button className={f.tipo === 'BAJA' ? 'danger' : 'ok'} disabled={busy || !sel.size} onClick={async () => {
            if (f.tipo === 'BAJA' && !(await ui.confirm(`¿Dar de BAJA ${sel.size} activo(s) por Bs ${fmt2(total)}? No puede revertirse.`))) return;
            run(async () => { const r = await post('/af/movimientos', { ...f, cod_edif: f.cod_edif === '' ? null : Number(f.cod_edif), cod_amb: f.cod_amb === '' ? null : Number(f.cod_amb), estado: f.estado || undefined, codigos: [...sel] }); ui.ok(`${f.tipo} registrada: acta ${r.nro} (${r.cantidad} activos).`); setLista([]); setSel(new Set()); abrirDocumento('af-movimiento', r.nro); });
          }}>Procesar {f.tipo.toLowerCase()} e imprimir acta</button></div>}
        </Card>
      )}
    </>
  );
}
