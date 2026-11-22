// Escenario completo de la demo + capturas de las pantallas principales. Uso: ./reset.sh && node capturas.js
const C = require('./cap.js'); const { execSync } = require('child_process');
const { ses, go, shot, optLabel, fs, B } = C;
const sql = q => execSync(`mariadb -uroot correspondencia -e "${q}"`, { stdio: 'pipe' });
const claves = fs.readFileSync('/tmp/claves.csv', 'utf8');
const hojaDeLink = (p) => p.evaluate(() => new URL(document.querySelector('main > p a[href*="hoja%2Fderivar"]').href).searchParams.get('id'));
async function crearDoc(p, tipo, dest, ref, texto) {
  await go(p, 'documento/index'); await p.click(`a.tipo-card:has-text("${tipo}")`);
  await p.selectOption('select[name=_dest]', { label: await optLabel(p, 'select[name=_dest]', dest) });
  await p.fill('[name=referencia]', ref); await p.fill('#contenido', texto || `Por la presente se remite lo siguiente: ${ref}. Sin otro particular, saludo a usted atentamente.`);
}
async function derivar(p, hojaId, destino, tipo, prov, urgente) {
  await go(p, 'hoja/derivar&id=' + hojaId);
  await p.selectOption('select[name=destino]', { label: await optLabel(p, 'select[name=destino]', destino) });
  await p.fill('[name=proveido]', prov); if (urgente) await p.check('[name=urgente]');
  await p.click(`button[value=${tipo}]`); await p.waitForLoadState('domcontentloaded');
}
(async () => {
  await C.launch();
  // ---- Ingreso
  let p = await ses(B); await go(p, 'auth/login');
  await shot(p, '01-login', { alto: 700, marks: [['[name=login]', 1], ['[name=password]', 2], ['button.btn.primary', 3], ['a[href*="consulta"]', 4]] });
  await p.fill('[name=login]', 'u401'); await p.fill('[name=password]', 'mala-clave'); await p.click('button.btn.primary');
  await shot(p, '02-login-error', { alto: 700, marks: [['.flash.error', 1]] });
  const tmp = claves.split('\n').find(l => l.includes(';u443;')).split(';')[3].replace(/"/g, '').trim();
  const pt = await ses(B, 'u443', tmp);
  await shot(pt, '03-primer-ingreso', { alto: 700, marks: [['.flash.warn', 1], ['[name=actual]', 2], ['[name=nueva]', 3], ['[name=repite]', 4]] });
  // ---- Alcalde
  const a = await ses(B, 'u401');
  await shot(a, '04-inicio', { alto: 700, marks: [['.who', 7], ['nav.main', 1], ['.search', 2], ['.panel.p-verde', 3], ['.panel.p-azul', 4], ['.panel.p-morado', 5], ['.panel.p-naranja', 6]] });
  await go(a, 'documento/index'); await shot(a, '05-tipos-documento', { alto: 900, marks: [['.tipos-vivos', 1], ['.sub a.on', 2]] });
  await crearDoc(a, 'Informe', 'Beto Flores', 'Solicitud de presupuesto anual 2027', 'Beto, necesito el presupuesto para el próximo año. Gracias.');
  await a.screenshot({ path: C.IMG + '06-form-documento.jpg', type: 'jpeg', quality: 82, fullPage: true, clip: { x: 0, y: 0, width: 1200, height: 1150 } });
  await C.marcar(a, [['.tipo-banner', 1], ['select[name=_dest]', 2], ['[name=destinatario_nombre]', 3], ['[name=referencia]', 4], ['#contenido', 5], ['button.btn.primary', 6]]);
  await a.screenshot({ path: C.IMG + '06-form-documento.jpg', type: 'jpeg', quality: 82, fullPage: true, clip: { x: 0, y: 0, width: 1200, height: 1150 } });
  await a.evaluate(() => document.querySelectorAll('[data-marca]').forEach(e => e.remove()));
  await a.click('button.btn.primary'); await a.waitForLoadState('domcontentloaded');
  const nur1 = (await a.textContent('main > p')).match(/GAME\/\d+-\d+/)[0];
  await shot(a, '07-documento-creado', { alto: 800, marks: [['.tipo-banner', 1], ['main > p', 2], ['.tabs a', 3, 'Adjuntos'], ['main > p a', 4, 'Derivar']] });
  await a.click('.tabs a:has-text("Adjuntos")'); await a.setInputFiles('input[type=file]', C.dir + '/Presupuesto_2027.pdf'); await a.click('button:has-text("Subir")');
  await shot(a, '08-adjuntos', { alto: 800, marks: [['table.t', 1], ['input[type=file]', 2], ['button.btn.primary', 3]] });
  const hoja1 = await hojaDeLink(a);
  for (const [tipo, ref] of [['Nota Interna', 'Informe de ejecución de obras trimestre 3'], ['Memorándum', 'Convocatoria a reunión de coordinación'], ['Carta', 'Respuesta a solicitud de la comunidad Tacopaya']]) { await crearDoc(a, tipo, 'Beto Flores', ref); await a.click('button.btn.primary'); await a.waitForLoadState('domcontentloaded'); }
  const ids = await a.evaluate(async () => (await (await fetch(location.origin + location.pathname + '?r=documento/hojas&q=GAME')).json()).map(x => x.nur));
  const hojaIds = []; for (const nur of ids.slice().reverse()) hojaIds.push(sql(`SELECT id FROM hojas_ruta WHERE nur='${nur}'`).toString().split('\n')[1]);
  const [h1, hoja2, hoja3, hoja4] = hojaIds;
  await go(a, 'hoja/lista'); await shot(a, '09-hojas-lista', { alto: 700, marks: [['table.t thead', 1], ['a.btn', 2, 'Derivar'], ['a.btn', 3, 'Documento'], ['input[data-filtro]', 4]] });
  await go(a, 'hoja/derivar&id=' + hoja1);
  await a.selectOption('select[name=destino]', { label: await optLabel(a, 'select[name=destino]', 'Beto Flores') }); await a.fill('[name=proveido]', 'Remito para su atención y trámite'); await a.check('[name=urgente]');
  await shot(a, '10-derivar-form', { alto: 1000, marks: [['select[name=destino]', 1], ['select[name=accion]', 2], ['[name=proveido]', 3], ['[name=urgente]', 4], ['button[value=oficial]', 5], ['button[value=copia]', 6]] });
  await a.click('button[value=oficial]'); await a.waitForLoadState('domcontentloaded');
  for (const [dest, prov] of [['Luis Rojas', 'Para su conocimiento'], ['Elena Vargas', 'Copia informativa']]) { await a.selectOption('select[name=destino]', { label: await optLabel(a, 'select[name=destino]', dest) }); await a.fill('[name=proveido]', prov); await a.click('button[value=copia]'); await a.waitForLoadState('domcontentloaded'); }
  await shot(a, '11-derivado-hecho', { alto: 1100, marks: [['.flash.ok', 1], ['table.t', 2], ['table.t button', 3, 'Eliminar']] });
  for (const h of [hoja2, hoja3, hoja4]) await derivar(a, h, 'Beto Flores', 'oficial', 'Remito para su atención', false);
  await go(a, 'bandeja/enviados'); await shot(a, '12-enviados', { alto: 1000, marks: [['article.item', 1], ['button', 2, 'Cancelar derivación'], ['.cuaderno', 3], ['input[data-todos]', 4]] });
  // ---- Secretario
  const s = await ses(B, 'u402');
  await shot(s, '13-inicio-secretaria', { alto: 800, marks: [['.panel.p-verde', 1], ['canvas', 2]] });
  await go(s, 'bandeja/entrada'); await shot(s, '14-entrada', { alto: 1000, marks: [['input[data-filtro]', 1], ['.toolbar span', 2], ['article.item .tag.urg', 3], ['article.item button', 4, 'Recepcionar'], ['input[data-todos]', 5], ['form > p button', 6]] });
  await s.check('input[data-todos]'); await s.click('button:has-text("Recepcionar seleccionadas")'); await s.waitForLoadState('domcontentloaded');
  await shot(s, '70-recibido-ok', { alto: 520, marks: [['.flash.ok', 1]] });
  sql(`UPDATE derivaciones SET fecha_recepcion=NOW()-INTERVAL 9 DAY WHERE hoja_id=${hoja2} AND estado='pendiente'`); sql(`UPDATE derivaciones SET fecha_recepcion=NOW()-INTERVAL 4 DAY WHERE hoja_id=${hoja3} AND estado='pendiente'`);
  await go(s, 'bandeja/pendientes'); await shot(s, '15-pendientes', { alto: 1100, marks: [['.sem.rojo', 1], ['.sem.amarillo', 2], ['.sem.verde', 3], ['article.item a.btn', 4, 'Derivar'], ['article.item a.btn', 5, 'Generar respuesta'], ['.mostrar', 6], ['.acciones-lote', 7]] });
  await s.locator('article.item', { hasText: nur1 }).locator('a.btn', { hasText: 'Generar respuesta' }).click(); await s.waitForLoadState('domcontentloaded');
  await shot(s, '16-respuesta-tipo', { alto: 900, marks: [['.tipos-vivos', 1]] });
  await s.click('a.tipo-card:has-text("Nota Interna")');
  await s.selectOption('select[name=_dest]', { label: await optLabel(s, 'select[name=_dest]', 'Ana Mamani') }); await s.fill('[name=referencia]', 'Respuesta sobre el presupuesto'); await s.fill('#contenido', 'Ana, ya revisé el presupuesto y está conforme.');
  await shot(s, '17-respuesta-form', { alto: 1250, marks: [['[name=nur]', 1], ['[name=referencia]', 2]] });
  await s.click('button.btn.primary'); await s.waitForLoadState('domcontentloaded');
  const docResp = await s.evaluate(() => new URL(document.querySelector('main > p a[href*="documento%2Fver"]').href).searchParams.get('id'));
  await go(s, 'documento/ver&id=' + docResp); await shot(s, '18-documento-imprimible', { alto: 1000, marks: [['button[data-print]', 1], ['.memo header', 2], ['.memo .datos', 3], ['.memo .contenido', 4]] });
  await derivar(s, hoja1, 'Carla Choque', 'oficial', 'Para su revisión y archivo', false);
  await go(s, 'hoja/derivar&id=' + hoja1); await shot(s, '19-derivar-respuesta', { alto: 1000, marks: [['table.t', 1]] });
  await go(s, 'bandeja/pendientes');
  await s.locator('article.item', { hasText: 'Informe de ejecución' }).locator('input[type=checkbox]').check(); await s.locator('article.item', { hasText: 'Convocatoria' }).locator('input[type=checkbox]').check();
  await s.click('button:has-text("Agrupar")'); await s.waitForLoadState('domcontentloaded'); await shot(s, '20-agrupar', { alto: 700, marks: [['label.radio', 1], ['button.btn.primary', 2]] });
  await s.check('label.radio input >> nth=0'); await s.click('button.btn.primary'); await s.waitForLoadState('domcontentloaded');
  await shot(s, '21-agrupacion-detalle', { alto: 700, marks: [['button[data-print]', 1], ['.caratula table', 2]] });
  await go(s, 'bandeja/agrupados'); await shot(s, '22-agrupados', { alto: 600 });
  await go(s, 'bandeja/pendientes'); await s.locator('article.item', { hasText: 'Tacopaya' }).locator('input[type=checkbox]').check(); await s.click('button:has-text("Archivar")'); await s.waitForLoadState('domcontentloaded');
  await s.fill('[name=nueva_carpeta]', 'Correspondencia 2026'); await s.fill('[name=observacion]', 'Atendida y concluida.');
  await shot(s, '23-archivar', { alto: 800, marks: [['[name=nueva_carpeta]', 1], ['[name=observacion]', 2], ['button.btn.primary', 3]] });
  await s.click('button.btn.primary'); await s.waitForLoadState('domcontentloaded'); await shot(s, '24-archivados', { alto: 600, marks: [['.carpeta', 1]] });
  await s.click('a.carpeta'); await s.waitForLoadState('domcontentloaded'); await shot(s, '25-archivados-carpeta', { alto: 600, marks: [['button', 1, 'Desarchivar']] });
  await go(s, 'bandeja/enviados'); await shot(s, '26-enviados-secretaria', { alto: 900, marks: [['.cuaderno', 1]] });
  await s.check('article.item input[type=checkbox]'); await s.selectOption('select[name=pos]', '3');
  const [pop] = await Promise.all([s.context().waitForEvent('page'), s.click('button:has-text("Generar PDF")')]); await pop.waitForLoadState('domcontentloaded'); await pop.waitForTimeout(300); await pop.setViewportSize({ width: 1200, height: 800 });
  await shot(pop, '27-cuaderno', { alto: 1100, marks: [['.hoja-a4 .slot:nth-child(3)', 1]] }); await pop.close();
  await go(s, 'seguimiento/ver&id=' + hoja1); await shot(s, '29-seguimiento', { alto: 1100, marks: [['.card', 1], ['.paso.actual', 2], ['.paso', 3]] });
  await go(s, 'seguimiento/index'); await shot(s, '30-seguimiento-lista', { alto: 700 });
  await s.goto(B + '/index.php?r=busqueda/index&q=presupuesto', { waitUntil: 'domcontentloaded' }); await shot(s, '31-busqueda', { alto: 800, marks: [['input[name=q]', 1], ['.chips', 2], ['table.t', 3]] });
  await go(s, 'reporte/oficina'); await shot(s, '32-reporte-oficina', { alto: 900, marks: [['canvas', 1], ['table.t', 2]] });
  await s.goto(B + '/index.php?r=reporte/recibida&generar=1', { waitUntil: 'domcontentloaded' }); await shot(s, '33-reporte-recibida', { alto: 900, marks: [['select[name=quien]', 1], ['[name=desde]', 2], ['button', 3, 'CSV'], ['table.t', 4]] });
  await go(s, 'reporte/personalizado'); await shot(s, '34-reporte-personalizado', { alto: 600, marks: [['select[name=estado]', 1]] });
  await go(s, 'usuario/password'); await shot(s, '35-cambiar-clave', { alto: 600 }); await go(s, 'usuario/datos'); await shot(s, '36-cambiar-datos', { alto: 750 }); await go(s, 'usuario/info'); await shot(s, '37-info-usuario', { alto: 500 });
  await go(s, 'dashboard/index'); await shot(s, '38-inicio-con-dependientes', { alto: 800, marks: [['.deps', 1]] });
  // ---- Cancelar envío (Ana)
  await crearDoc(a, 'Carta', 'Elena Vargas', 'Invitación al desfile del aniversario'); await a.click('button.btn.primary'); await a.waitForLoadState('domcontentloaded');
  await a.click('main > p a:has-text("Derivar")'); await a.waitForLoadState('domcontentloaded'); await a.selectOption('select[name=destino]', { label: await optLabel(a, 'select[name=destino]', 'Luis Rojas') }); await a.fill('[name=proveido]', 'Por favor revisar'); await a.click('button[value=oficial]'); await a.waitForLoadState('domcontentloaded');
  await go(a, 'bandeja/enviados'); await a.locator('article.item', { hasText: 'desfile' }).locator('button', { hasText: 'Cancelar derivación' }).click(); await a.waitForLoadState('domcontentloaded');
  await shot(a, '71-cancelado-ok', { alto: 560, marks: [['.flash.ok', 1]] }); await go(a, 'bandeja/pendientes'); await shot(a, '72-volvio-pendientes', { alto: 700, marks: [['article.item', 1]] });
  fs.writeFileSync(C.dir + '/datos.json', JSON.stringify({ nur1, hoja1, hoja2, hoja3, hoja4 }));
  await C.close(); console.log('FIN capturas.js');
})().catch(e => { console.error(e); process.exit(1); });
