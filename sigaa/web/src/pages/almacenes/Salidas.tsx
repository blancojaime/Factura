import { useState } from 'react';
import { abrirDocumento, fmt2, get, hoy, post } from '../../api';
import { useAuth } from '../../auth';
import { AreaField, Badge, Card, DataTable, DateField, ItemsGrid, PageHead, SelectField, TextField, useAction, useLoad, useUi } from '../../ui';
import { codeOf, nroUrl, useAlmMeta, useItems } from './common';

const vacio = () => ({ nro: '', fecha_pedido: hoy(), cod_bod: '', unidad: '', solicitante: '', cargo: '', superior: '', proyecto: '', nota_interna: '', justificacion: '', observ: '', excepcion: '', estado: '', total: 0 });
const linea = () => ({ item: '', cant_pedida: '', obs: '', saldo_actual: '', cant_entregada: '', precio_prom: '', total: '' });

export default function AlmSalidas() {
  const { puede } = useAuth();
  const ui = useUi();
  const { data: meta } = useAlmMeta();
  const [est, setEst] = useState('');
  const { data: lista, reload } = useLoad<any[]>(() => get('/alm/salidas', { estado: est }), [est]);
  const { data: funcs } = useLoad<any[]>(() => get('/maestros/funcionarios'));
  const { data: unids } = useLoad<any[]>(() => get('/maestros/unidades'));
  const { data: proys } = useLoad<any[]>(() => get('/maestros/proyectos'));
  const [h, setH] = useState<any>(vacio());
  const [items, setItems] = useState<any[]>([linea()]);
  const [run, busy] = useAction();
  const { Lista, listId, porCodigo } = useItems(h.cod_bod);
  const abierto = !h.nro || ['PEDIDO', 'APROBADO'].includes(h.estado);
  const editable = puede('alm') && abierto;

  const cargar = (nro: string) => run(async () => {
    const d = await get(`/alm/salidas/${nroUrl(nro)}`);
    setH({ ...vacio(), ...d });
    setItems(d.items.map((x: any) => ({ item: `${x.cod_item} - ${x.descripcion}`, cant_pedida: x.cant_pedida, obs: x.obs ?? '', saldo_actual: x.saldo_actual, cant_entregada: x.cant_entregada, precio_prom: x.precio_prom, total: x.total })));
  });
  const payload = () => ({ ...h, items: items.filter((i) => i.item).map((i) => ({ cod_item: codeOf(i.item), cant_pedida: Number(i.cant_pedida), obs: i.obs })) });
  const guardar = () => run(async () => {
    const r = await post('/alm/salidas', payload());
    await cargar(r.nro); await reload();
    ui.ok(`Pedido ${r.nro} guardado. Siguiente paso: Vo.Bo. del inmediato superior; luego aprobar y entregar.`);
  });
  const accion = (ruta: string, msg: string, motivoTxt?: string) => async () => {
    let body: any = {};
    if (motivoTxt) { const m = await ui.prompt(motivoTxt); if (!m) return; body = { motivo: m }; }
    else if (!(await ui.confirm(msg))) return;
    run(async () => {
      if (ruta === 'aprobar-entregar' || ruta === 'entregar') await post('/alm/salidas', payload()).catch(() => null);
      const r = await post(`/alm/salidas/${nroUrl(h.nro)}/${ruta}`, body);
      await cargar(h.nro); await reload();
      if (r?.sinExistencia?.length) ui.error('Ítems SIN EXISTENCIA (no entregados):\n' + r.sinExistencia.join('\n') + '\nEmita la Certificación de Inexistencia.');
      else ui.ok(ruta === 'entregar' || ruta === 'aprobar-entregar' ? `Entrega registrada por Bs ${fmt2(r.total)}. Las existencias se descargaron por PEPS.` : 'Operación realizada.');
    });
  };
  const jerarquia = (funcs ?? []).map((f) => f.nombre);
  const elegirSolicitante = (nombre: string) => {
    const f = (funcs ?? []).find((x) => x.nombre === nombre);
    setH({ ...h, solicitante: nombre, cargo: f?.cargo ?? h.cargo, unidad: h.unidad || f?.unidad || '' });
  };
  return (
    <>
      <PageHead title="Pedido y vale de salida de materiales y suministros" sub="Solicitud · Aprobación del inmediato superior · Entrega con descarga PEPS (nunca de lotes vencidos)">
        {puede('alm') && <button className="primary" onClick={() => { setH(vacio()); setItems([linea()]); }}>Nuevo pedido</button>}
      </PageHead>
      <div className="split" style={{ gridTemplateColumns: 'minmax(260px,320px) minmax(0,1fr)' }}>
        <Card title="Pedidos" right={<select style={{ width: 130 }} value={est} onChange={(e) => setEst(e.target.value)}><option value="">Todos</option>{['PEDIDO', 'APROBADO', 'ENTREGADO', 'RECHAZADO', 'ANULADO'].map((x) => <option key={x}>{x}</option>)}</select>}>
          <DataTable maxHeight="70vh" rows={lista ?? []} onRow={(r) => cargar(r.nro)} selected={(r) => r.nro === h.nro} cols={[{ key: 'nro', header: 'Vale' }, { key: 'fecha_pedido', header: 'Fecha', date: true }, { key: 'solicitante', header: 'Solicitante' }, { key: 'estado', header: 'Estado', badge: true }]} />
        </Card>
        <div>
          <Card title={h.nro || 'Nuevo pedido'} right={<Badge v={h.estado} />}>
            <div className="grid">
              <DateField label="Fecha del pedido" req value={h.fecha_pedido} onChange={(v) => setH({ ...h, fecha_pedido: v })} disabled={!editable} hint={`Pedidos del día ${meta?.config.DiaPedidoIni} al ${meta?.config.DiaPedidoFin} de cada mes`} />
              <SelectField label="Bodega" req value={h.cod_bod} onChange={(v) => setH({ ...h, cod_bod: v })} disabled={!editable} options={(meta?.bodegas ?? []).map((b) => ({ value: b.cod, label: b.nombre }))} />
              <SelectField label="Solicitante (funcionario)" req value={h.solicitante} onChange={elegirSolicitante} disabled={!editable} options={jerarquia} />
              <TextField label="Cargo del solicitante" value={h.cargo} onChange={(v) => setH({ ...h, cargo: v })} disabled={!editable} />
              <SelectField label="Unidad solicitante" req value={h.unidad} onChange={(v) => setH({ ...h, unidad: v })} disabled={!editable} options={(unids ?? []).map((u) => u.nombre)} />
              <SelectField label="Inmediato superior (Vo.Bo.)" req value={h.superior} onChange={(v) => setH({ ...h, superior: v })} disabled={!editable} options={jerarquia} />
              <SelectField label="Proyecto / destino" value={h.proyecto} onChange={(v) => setH({ ...h, proyecto: v })} disabled={!editable} options={(proys ?? []).map((p) => p.nombre)} />
              <TextField label="Nº nota interna (cantidades elevadas)" value={h.nota_interna} onChange={(v) => setH({ ...h, nota_interna: v })} disabled={!editable} />
              <AreaField className="span2" label="Justificación del pedido" req value={h.justificacion} onChange={(v) => setH({ ...h, justificacion: v })} disabled={!editable} />
              <TextField className="span2" label="Excepción de plazo/límite autorizada por" value={h.excepcion} onChange={(v) => setH({ ...h, excepcion: v })} disabled={!editable} hint="Solo si el pedido incumple el plazo del mes o el máximo de pedidos" />
              <TextField className="span2" label="Observaciones" value={h.observ} onChange={(v) => setH({ ...h, observ: v })} disabled={!editable} />
            </div>
          </Card>
          <Card title="Materiales" right={h.estado === 'ENTREGADO' ? <b>Total entregado: Bs {fmt2(h.total)}</b> : undefined}>
            <Lista />
            <ItemsGrid disabled={!editable} rows={items} onChange={setItems} vacio={linea} cols={[
              { key: 'item', header: 'Ítem del catálogo (código - descripción)', list: listId, width: '38%' },
              { key: 'obs', header: 'Observación' },
              { key: 'saldo_actual', header: 'Saldo', type: 'readonly', num: true },
              { key: 'cant_pedida', header: 'Cant. pedida', type: 'number', num: true, width: 100 },
              ...(h.estado === 'ENTREGADO' ? [{ key: 'cant_entregada' as const, header: 'Entregada', type: 'readonly' as const, num: true }, { key: 'precio_prom' as const, header: 'P.U. prom.', type: 'readonly' as const, money: true }, { key: 'total' as const, header: 'Importe', type: 'readonly' as const, money: true }] : []),
            ]} />
            {items.filter((i) => i.item).map((i) => porCodigo.get(codeOf(i.item))).filter(Boolean).some((c: any) => c.perecible === 'SI') && <small className="muted">Se entregan primero los lotes de vencimiento más próximo (FEFO); los lotes vencidos nunca se entregan.</small>}
          </Card>
          <div className="row">
            {editable && <button className="primary" disabled={busy} onClick={guardar}>Guardar pedido</button>}
            {puede('alm') && h.estado === 'PEDIDO' && <button disabled={busy} onClick={accion('aprobar', `¿Confirma que el inmediato superior ${h.superior} aprobó el pedido ${h.nro} (firma y sello del Vo.Bo.)?`)}>Aprobar</button>}
            {puede('alm') && h.estado === 'APROBADO' && <button className="ok" disabled={busy} onClick={accion('entregar', `¿Entregar los materiales del pedido ${h.nro}? Se descargarán las existencias por PEPS.`)}>Entregar</button>}
            {puede('alm') && h.estado === 'PEDIDO' && <button disabled={busy} onClick={accion('aprobar-entregar', `Aprueba y entrega en un solo paso.\n¿El inmediato superior ya firmó el Vo.Bo. del pedido ${h.nro}?`)}>Aprobar y entregar</button>}
            {puede('alm') && ['PEDIDO', 'APROBADO'].includes(h.estado) && <button className="danger" disabled={busy} onClick={accion('rechazar', '', 'Motivo del rechazo:')}>Rechazar</button>}
            {puede('alm') && ['PEDIDO', 'APROBADO', 'ENTREGADO'].includes(h.estado) && <button className="danger" disabled={busy} onClick={accion('anular', '', h.estado === 'ENTREGADO' ? 'El vale ya fue ENTREGADO: anularlo devuelve las existencias al almacén (solo para corregir errores de registro). Motivo:' : 'Motivo de la anulación:')}>Anular</button>}
            {h.nro && <button onClick={() => abrirDocumento('alm-vale', h.nro)}>Imprimir vale</button>}
            {h.nro && <button onClick={() => abrirDocumento('alm-cert-inexistencia', h.nro)}>Certificación de inexistencia</button>}
          </div>
        </div>
      </div>
    </>
  );
}
