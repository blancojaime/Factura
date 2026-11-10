import { useState } from 'react';
import { get, post, fmt2, fmtN } from '../../api';
import { useAuth } from '../../auth';
import { Badge, Card, DataTable, Field, Modal, NumField, PageHead, SelectField, TextField, useAction, useLoad } from '../../ui';
import { useAlmMeta } from './common';

export default function AlmCatalogo() {
  const { puede } = useAuth();
  const { data: meta } = useAlmMeta();
  const [f, setF] = useState<{ bod?: string; q?: string; estado?: string }>({});
  const { data: items, reload } = useLoad<any[]>(() => get('/alm/catalogo', f), [JSON.stringify(f)]);
  const [m, setM] = useState<any>(null);
  const [run, busy] = useAction();
  const subs = (meta?.subgrupos ?? []).map((s) => ({ value: `${s.grupo}-${s.subgrupo}`, label: `${s.grupo}-${s.subgrupo} - ${s.nombre}` }));
  const guardar = () => run(async () => {
    const [grupo, subgrupo] = String(m.sub || '').split('-').map(Number);
    await post('/alm/catalogo', { ...m, grupo, subgrupo });
    setM(null); reload();
  }, 'Ítem guardado.');
  return (
    <>
      <PageHead title="Catálogo general de materiales y suministros" sub="Codificación: Grupo - Subgrupo - Nº correlativo (ej. 1-2-0000003)">
        {puede('alm') && <button className="primary" onClick={() => setM({ sub: '', unidad: '', perecible: 'NO', peligroso: 'NO', estado: 'ACTIVO', stock_min: 0, stock_max: 0, precio_ref: 0 })}>+ Nuevo ítem</button>}
      </PageHead>
      <Card>
        <div className="row">
          <SelectField label="Bodega" value={f.bod} onChange={(v) => setF({ ...f, bod: v })} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
          <SelectField label="Estado" value={f.estado} onChange={(v) => setF({ ...f, estado: v })} options={['ACTIVO', 'INACTIVO']} />
          <TextField label="Buscar (código o descripción)" value={f.q} onChange={(v) => setF({ ...f, q: v })} />
        </div>
      </Card>
      <DataTable
        rows={items ?? []}
        onRow={(r) => puede('alm') && setM({ ...r, sub: `${r.grupo}-${r.subgrupo}` })}
        cols={[
          { key: 'codigo', header: 'Código' }, { key: 'descripcion', header: 'Descripción' }, { key: 'unidad', header: 'Unidad' }, { key: 'bodega', header: 'Bodega' },
          { key: 'existencia', header: 'Existencia', num: true }, { key: 'stock_min', header: 'Mín.', num: true }, { key: 'stock_max', header: 'Máx.', num: true },
          { key: 'precio_ref', header: 'P. ref. Bs', money: true }, { key: 'perecible', header: 'Perec.', ctr: true }, { key: 'estado', header: 'Estado', badge: true },
          { key: 'alerta', header: '', render: (r) => (Number(r.stock_min) > 0 && Number(r.existencia) <= Number(r.stock_min) ? <Badge v="PENDIENTE" /> : null) },
        ]}
      />
      <small className="muted">{items?.length ?? 0} ítem(s)</small>
      {m && (
        <Modal title={m.codigo ? `Ítem ${m.codigo}` : 'Nuevo ítem'} onClose={() => setM(null)} footer={<><button onClick={() => setM(null)}>Cancelar</button><button className="primary" disabled={busy} onClick={guardar}>Guardar</button></>}>
          <div className="grid c2">
            <SelectField label="Subgrupo (grupo-subgrupo)" req disabled={!!m.codigo} value={m.sub} onChange={(v) => setM({ ...m, sub: v })} options={subs} />
            <SelectField label="Bodega" req value={m.cod_bod} onChange={(v) => setM({ ...m, cod_bod: v })} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
            <TextField className="span2" label="Descripción específica" req value={m.descripcion} onChange={(v) => setM({ ...m, descripcion: v })} />
            <SelectField label="Unidad de medida" req value={m.unidad} onChange={(v) => setM({ ...m, unidad: v })} options={meta?.unidades_medida ?? []} />
            <SelectField label="Partida presupuestaria" value={m.partida} onChange={(v) => setM({ ...m, partida: v })} options={(meta?.partidas ?? []).map((p) => ({ value: p.partida, label: `${p.partida} - ${p.descripcion}` }))} />
            <NumField label="Stock mínimo" value={m.stock_min} onChange={(v) => setM({ ...m, stock_min: v })} />
            <NumField label="Stock máximo" value={m.stock_max} onChange={(v) => setM({ ...m, stock_max: v })} />
            <NumField label="Precio referencial (Bs)" value={m.precio_ref} onChange={(v) => setM({ ...m, precio_ref: v })} />
            <TextField label="Ubicación física (estante/pasillo)" value={m.ubicacion} onChange={(v) => setM({ ...m, ubicacion: v })} />
            <SelectField label="¿Perecible? (tiene vencimiento)" blank={false} value={m.perecible} onChange={(v) => setM({ ...m, perecible: v })} options={['NO', 'SI']} />
            <SelectField label="¿Sustancia peligrosa?" blank={false} value={m.peligroso} onChange={(v) => setM({ ...m, peligroso: v })} options={['NO', 'SI']} />
            <SelectField label="Estado" blank={false} value={m.estado} onChange={(v) => setM({ ...m, estado: v })} options={['ACTIVO', 'INACTIVO']} />
            {m.codigo && <Field label="Existencia actual (todas las bodegas)"><input readOnly value={fmtN(m.existencia)} /></Field>}
          </div>
          <small className="muted">El código se genera automáticamente. Valor referencial actual: Bs {fmt2(m.precio_ref)}.</small>
        </Modal>
      )}
    </>
  );
}
