import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, today, txt } from '../../core/util.js';
import { siguienteNro, gestion, nom } from '../../core/services.js';
import { bitacoraUsuario, requerirBodega } from './helpers.js';
import { altaLote, anularMovimientos } from './stock.js';

export interface IngresoItem {
  cod_item: string;
  cantidad: number;
  precio_unit: number;
  vencimiento?: string | null;
  lote?: string;
  marca?: string;
}
export interface IngresoInput {
  nro?: string;
  fecha: string;
  cod_bod: string;
  tipo: string;
  proveedor?: string;
  nro_oc?: string;
  plazo_entrega?: string;
  factura?: string;
  fecha_factura?: string;
  unidad?: string;
  preventivo?: string;
  nro_pse?: string;
  proyecto?: string;
  fuente?: string;
  partida?: string;
  comision?: string;
  obs_plazo?: string;
  items: IngresoItem[];
  docs?: { documento: string; estado?: string }[];
}

export const esCompra = (tipo: string) => tipo.startsWith('COMPRA');
const esCajaOReembolso = (tipo: string) => tipo.startsWith('CAJA ') || tipo.startsWith('REEMBOLSO');

/** Documentación de respaldo exigida por tipo de ingreso (art. 13-IV · Manual 11.2). Los obligatorios llevan "  (*)". */
export async function docsRequeridos(db: Db, tipo: string) {
  const rows = await db('alm_docreq').where({ tipo }).orderBy('orden');
  return rows.map((r: any, i: number) => ({ orden: i + 1, documento: r.documento + (r.obligatorio === 'SI' ? '  (*)' : ''), estado: '' }));
}

export async function nuevoIngreso(db: Db): Promise<string> {
  return siguienteNro(db, 'CGI');
}

export async function guardarIngreso(db: Db, u: Usuario, d: IngresoInput) {
  const e = new Errores();
  e.add(!isDate(d.fecha), 'Registre la fecha de recepción.');
  e.add(isDate(d.fecha) && d.fecha > today(), 'La fecha de recepción no puede ser posterior a hoy.');
  e.add(!txt(d.tipo), 'Seleccione el tipo de ingreso.');
  e.throwIfAny('Ingreso incompleto:');
  const bod = await requerirBodega(db, d.cod_bod);
  const tipo = txt(d.tipo);
  if (esCompra(tipo)) {
    if (!txt(d.nro_oc)) fail('Registre el Nº de Orden de Compra o Contrato.');
    if (!txt(d.proveedor)) fail('Seleccione el proveedor.');
  }
  if (esCompra(tipo) || esCajaOReembolso(tipo)) {
    if (!txt(d.factura)) fail('Registre el Nº de factura o nota de remisión (el ingreso sin respaldo está prohibido, art. 8-l).');
    if (!txt(d.unidad)) fail('Seleccione la unidad solicitante.');
  }
  if (txt(d.plazo_entrega)) {
    if (!isDate(d.plazo_entrega)) fail('El plazo de entrega no es una fecha válida.');
    if (d.fecha > d.plazo_entrega!.slice(0, 10) && !txt(d.obs_plazo))
      fail(`La recepción es posterior al plazo de entrega (${d.plazo_entrega}). Registre en Observaciones la justificación o autorización (art. 31-f: prohibido recibir fuera de plazo).`);
  }
  return db.transaction(async (trx) => {
    const filas: any[] = [];
    let total = 0;
    const vistos = new Set<string>();
    let j = 0;
    for (const it of d.items || []) {
      if (!txt(it.cod_item) && !num(it.cantidad) && !num(it.precio_unit)) continue;
      j++;
      const cod = txt(it.cod_item);
      const cat = await trx('alm_catalogo').where({ codigo: cod }).first();
      if (!cod) fail(`Ítem ${j}: seleccione el ítem del catálogo.`);
      if (!cat) fail(`Ítem ${j}: el código ${cod} no existe en el catálogo.`);
      if (cat.estado === 'INACTIVO') fail(`Ítem ${j}: el ítem ${cod} está INACTIVO.`);
      if (cat.cod_bod !== bod) fail(`Ítem ${j}: ${cod} pertenece a la bodega ${cat.cod_bod}, no a la bodega seleccionada.`);
      if (vistos.has(cod + '|' + txt(it.lote))) fail(`Ítem ${j}: ${cod} está repetido; use otra línea solo si cambia el lote.`);
      vistos.add(cod + '|' + txt(it.lote));
      const cant = num(it.cantidad);
      const pu = num(it.precio_unit);
      if (!(cant > 0)) fail(`Ítem ${j}: registre una cantidad mayor a cero.`);
      if (!(pu > 0)) fail(`Ítem ${j}: el precio unitario debe ser mayor a cero.`);
      let venc: string | null = null;
      if (txt(it.vencimiento)) {
        if (!isDate(it.vencimiento)) fail(`Ítem ${j}: la fecha de vencimiento no es válida.`);
        venc = String(it.vencimiento).slice(0, 10);
      }
      if (cat.perecible === 'SI' && !venc) fail(`Ítem ${j}: ${cod} es perecible; registre la fecha de vencimiento.`);
      if (venc && venc < d.fecha) fail(`Ítem ${j}: el bien ya está vencido al momento de la recepción; no puede ingresar a almacén.`);
      const tot = round(cant * pu, 2);
      total += tot;
      filas.push({ item: j, cod_item: cod, descripcion: cat.descripcion, unidad: cat.unidad, marca: txt(it.marca), cantidad: cant, precio_unit: pu, total: tot, vencimiento: venc, lote: txt(it.lote) });
    }
    if (!filas.length) fail('Registre al menos un ítem en el detalle.');

    let nro = txt(d.nro);
    const prov = txt(d.proveedor);
    const provRow = prov ? await trx('core_proveedores').where({ razon_social: prov }).first('nit') : null;
    const cab = {
      fecha: d.fecha,
      cod_bod: bod,
      tipo,
      proveedor: prov,
      nit: txt(provRow?.nit),
      nro_oc: txt(d.nro_oc),
      plazo_entrega: txt(d.plazo_entrega).slice(0, 10) || null,
      factura: txt(d.factura),
      fecha_factura: txt(d.fecha_factura).slice(0, 10) || null,
      unidad: txt(d.unidad),
      preventivo: txt(d.preventivo),
      nro_pse: txt(d.nro_pse),
      proyecto: txt(d.proyecto),
      fuente: txt(d.fuente),
      partida: txt(d.partida),
      comision: txt(d.comision),
      obs_plazo: txt(d.obs_plazo),
      total,
    };
    if (nro) {
      const ex = await trx('alm_ingresos').where({ nro }).first();
      if (ex && ex.estado !== 'REGISTRADO') fail(`El ingreso ${nro} está ${ex.estado} y no puede modificarse.`);
      if (ex) {
        await trx('alm_ingresos').where({ nro }).update(cab);
        await trx('alm_ingresos_det').where({ nro }).delete();
        await trx('alm_ingresos_doc').where({ nro }).delete();
      } else await trx('alm_ingresos').insert({ nro, ...cab, estado: 'REGISTRADO', fecha_reg: nowIso(), usuario: u.usuario });
    } else {
      nro = await siguienteNro(trx, 'CGI');
      await trx('alm_ingresos').insert({ nro, ...cab, estado: 'REGISTRADO', fecha_reg: nowIso(), usuario: u.usuario });
    }
    for (const f of filas) await trx('alm_ingresos_det').insert({ nro, ...f });
    let docs = d.docs;
    if (!docs || !docs.length) docs = await docsRequeridos(trx, tipo);
    let k = 0;
    for (const doc of docs) if (txt(doc.documento)) await trx('alm_ingresos_doc').insert({ nro, orden: ++k, documento: doc.documento, estado: txt(doc.estado) });
    await bitacoraUsuario(trx, u, 'REGISTRO DE CGI', nro, `${tipo} - ${bod} - Bs ${total.toFixed(2)}`);
    return { nro, total, items: filas.length };
  });
}

export async function confirmarIngreso(db: Db, u: Usuario, nro: string) {
  return db.transaction(async (trx) => {
    const h = await trx('alm_ingresos').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el ingreso ${nro}.`);
    if (h.estado !== 'REGISTRADO') fail(`El ingreso está ${h.estado}.`);
    const docs = await trx('alm_ingresos_doc').where({ nro }).orderBy('orden');
    if (!docs.length) fail('No hay lista de documentos de respaldo. Cargue la lista, marque lo recibido y guarde.');
    const falt = docs.filter((x: any) => String(x.documento).endsWith('  (*)') && txt(x.estado).toUpperCase() !== 'SI').map((x: any) => '  - ' + String(x.documento).slice(0, -5));
    if (falt.length) fail('Faltan documentos de respaldo obligatorios:\n' + falt.join('\n') + '\nMarque SI en la lista, guarde e intente nuevamente.');
    const det = await trx('alm_ingresos_det').where({ nro }).orderBy('item');
    for (const x of det) {
      const cat = await trx('alm_catalogo').where({ codigo: x.cod_item }).first();
      if (cat?.perecible === 'SI' && !x.vencimiento) fail(`El ítem ${x.cod_item} es perecible y no tiene fecha de vencimiento.`);
      if (num(x.precio_unit) <= 0) fail(`El ítem ${x.cod_item} no tiene precio unitario.`);
    }
    for (const x of det) {
      await altaLote(trx, u.usuario, {
        bod: h.cod_bod,
        cod: x.cod_item,
        docOrigen: nro,
        fechaIng: h.fecha,
        venc: x.vencimiento,
        cant: num(x.cantidad),
        pu: num(x.precio_unit),
        tipoMov: 'INGRESO',
        refer: (txt(h.proveedor) + (txt(h.factura) ? ' Fact. ' + txt(h.factura) : '')).slice(0, 80),
        nroLote: x.lote,
      });
      await trx('alm_catalogo').where({ codigo: x.cod_item }).update({ precio_ref: x.precio_unit });
    }
    await trx('alm_ingresos').where({ nro }).update({ estado: 'INGRESADO' });
    await bitacoraUsuario(trx, u, 'CONFIRMACIÓN DE INGRESO', nro, `Bs ${num(h.total).toFixed(2)}`);
    return { nro, estado: 'INGRESADO', total: num(h.total) };
  });
}

export async function anularIngreso(db: Db, u: Usuario, nro: string, motivo: string) {
  if (!txt(motivo)) fail('La anulación requiere un motivo.');
  return db.transaction(async (trx) => {
    const h = await trx('alm_ingresos').where({ nro }).first();
    if (!h) throw new NotFound(`No existe el ingreso ${nro}.`);
    if (h.estado === 'ANULADO') fail('El ingreso ya está anulado.');
    if (h.estado === 'INGRESADO') await anularMovimientos(trx, nro);
    await trx('alm_ingresos').where({ nro }).update({ estado: 'ANULADO', motivo_anulacion: motivo });
    await bitacoraUsuario(trx, u, 'ANULACIÓN DE INGRESO', nro, motivo);
    return { nro, estado: 'ANULADO' };
  });
}

export async function obtenerIngreso(db: Db, nro: string) {
  const h = await db('alm_ingresos as i').leftJoin('alm_bodegas as b', 'b.cod', 'i.cod_bod').where('i.nro', nro).select('i.*', 'b.nombre as bodega').first();
  if (!h) throw new NotFound(`No existe el ingreso ${nro}.`);
  return { ...h, items: await db('alm_ingresos_det').where({ nro }).orderBy('item'), docs: await db('alm_ingresos_doc').where({ nro }).orderBy('orden') };
}

export async function listarIngresos(db: Db, f: { estado?: string; bod?: string; desde?: string; hasta?: string } = {}) {
  const q = db('alm_ingresos as i').leftJoin('alm_bodegas as b', 'b.cod', 'i.cod_bod').select('i.*', 'b.nombre as bodega').orderBy('i.nro', 'desc');
  if (f.estado) q.where('i.estado', f.estado);
  if (f.bod) q.where('i.cod_bod', f.bod);
  if (f.desde) q.where('i.fecha', '>=', f.desde);
  if (f.hasta) q.where('i.fecha', '<=', f.hasta);
  return q;
}
void gestion;
void nom;
