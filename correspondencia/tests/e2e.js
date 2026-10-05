// Prueba de extremo a extremo con Playwright. Uso: BASE=http://127.0.0.1:8080 node tests/e2e.js
const { chromium } = require(process.env.PW || 'playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:8080';
const SHOTS = process.env.SHOTS || '/tmp';
let fallos = 0;
const ok = (c, m) => { console.log((c ? '  OK   ' : '  FALLA ') + m); if (!c) fallos++; };

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const mk = async () => { const c = await browser.newContext({ viewport: { width: 1280, height: 900 } }); const p = await c.newPage(); p.setDefaultTimeout(8000);
    await p.route(/cdnjs\.cloudflare\.com/, r => r.abort()); p.on('pageerror', e => { console.log('  pageerror', e.message); }); p.on('dialog', d => d.accept()); return p; };
  const go = (p, path) => p.goto(BASE + '/index.php?r=' + path, { waitUntil: 'domcontentloaded' });
  const login = async (p, u, pw = 'Demo12345') => { await go(p, 'auth/login'); await p.fill('[name=login]', u); await p.fill('[name=password]', pw); await p.click('button.btn'); await p.waitForLoadState('domcontentloaded'); };

  console.log('== Login');
  const a = await mk();
  await login(a, 'alcalde', 'mala');
  ok((await a.textContent('.flash.error')).includes('incorrectos'), 'Contraseña errónea rechazada');
  await login(a, 'alcalde');
  ok((await a.textContent('h1')).includes('Inicio'), 'Ingreso correcto');
  await a.screenshot({ path: SHOTS + '/01-inicio.png' });

  console.log('== Crear documento y derivar');
  await go(a, 'documento/index');
  await a.click('a.tipo:has-text("Informe")');
  await a.selectOption('select[name=_dest]', { label: 'Carlos Choque — Director de Finanzas' });
  ok((await a.inputValue('[name=destinatario_nombre]')) === 'Carlos Choque', 'Selector rellena destinatario');
  await a.fill('[name=referencia]', 'Solicitud de presupuesto anual');
  await a.fill('#contenido', '<p>Se solicita el presupuesto <script>alert(1)</script></p>');
  await a.evaluate(() => { document.getElementById('contenido').style.display = 'block'; });
  await a.screenshot({ path: SHOTS + '/02-nuevo-doc.png' });
  await a.click('button.btn.primary');
  await a.waitForLoadState('domcontentloaded');
  const nur = (await a.textContent('main p b + *') , (await a.textContent('main > p')).match(/GAMP\/\d+-\d+/)[0]);
  ok(/GAMP\/\d{4}-00001/.test(nur), 'Documento creado con NUR ' + nur);
  ok((await a.textContent('main > p')).includes('INF/GAMP/ALC Nº 0001/'), 'CITE generado');
  // adjunto
  await a.click('.tabs a:has-text("Adjuntos")');
  require('fs').writeFileSync('/tmp/prueba.txt', 'hola');
  await a.setInputFiles('input[type=file]', '/tmp/prueba.txt');
  await a.click('button:has-text("Subir")');
  ok((await a.textContent('table.t')).includes('prueba.txt'), 'Adjunto subido');
  await a.setInputFiles('input[type=file]', { name: 'x.exe', mimeType: 'application/octet-stream', buffer: Buffer.from('MZ') });
  await a.click('button:has-text("Subir")');
  ok((await a.textContent('.flash.error')).includes('no permitido'), 'Archivo .exe rechazado');
  // derivar
  await go(a, 'hoja/lista');
  await a.click('a:has-text("Derivar")');
  await a.selectOption('select[name=destino]', { label: 'Carlos Choque — Director de Finanzas' });
  await a.fill('[name=proveido]', 'Remito para su atención');
  await a.check('[name=urgente]');
  await a.click('button[value=oficial]');
  ok((await a.textContent('.flash.ok')).includes('oficial'), 'Derivación oficial');
  ok(await a.locator('button[value=oficial]').count() === 0, 'Oficial no se repite');
  await a.selectOption('select[name=destino]', { label: 'Luis Rojas — Director de Obras Públicas' });
  await a.fill('[name=proveido]', 'Para su conocimiento');
  await a.click('button[value=copia]');
  await a.screenshot({ path: SHOTS + '/03-derivar.png', fullPage: true });
  await go(a, 'bandeja/enviados');
  ok((await a.locator('article.item').count()) === 2, 'Enviados muestra 2 derivaciones');
  await a.screenshot({ path: SHOTS + '/04-enviados.png' });

  console.log('== Recepción (finanzas)');
  const f = await mk();
  await login(f, 'finanzas');
  await go(f, 'bandeja/entrada');
  ok((await f.locator('article.item.urgente').count()) === 1, 'Entrada con ítem urgente');
  await f.screenshot({ path: SHOTS + '/05-entrada.png' });
  await f.click('button:has-text("Recepcionar") >> nth=0');
  await f.waitForLoadState('domcontentloaded');
  ok((await f.locator('article.item').count()) === 1 && /Pendientes/.test(await f.textContent('h1')), 'Recepcionada → Pendientes');
  await f.screenshot({ path: SHOTS + '/06-pendientes.png' });
  ok((await a.goto(BASE + '/index.php?r=bandeja/enviados'), (await a.locator('article.item').count()) === 1), 'Alcalde: oficial ya recibida sale de Enviados');
  // generar respuesta
  await f.click('a:has-text("Generar respuesta")');
  await f.click('a.tipo:has-text("Nota Interna")');
  ok((await f.inputValue('[name=nur]')).startsWith('GAMP/'), 'Respuesta reutiliza el NUR');
  await f.selectOption('select[name=_dest]', { label: 'Juan Mamani Quispe — Alcalde Municipal' });
  await f.fill('[name=referencia]', 'Respuesta presupuesto');
  await f.click('button.btn.primary');
  ok((await f.textContent('.flash.ok')).includes('creado'), 'Respuesta creada');
  // seguimiento y búsqueda
  await go(f, 'seguimiento/ver&id=1');
  ok((await f.locator('.paso').count()) === 2, 'Seguimiento con 2 pasos');
  await f.screenshot({ path: SHOTS + '/07-seguimiento.png', fullPage: true });
  await f.goto(BASE + '/index.php?r=busqueda/index&q=presupuesto');
  ok((await f.locator('table.t tbody tr').count()) >= 2, 'Búsqueda por referencia');
  // archivar
  await go(f, 'bandeja/pendientes');
  await f.check('.item input[type=checkbox]');
  await f.click('button:has-text("Archivar")');
  await f.fill('[name=nueva_carpeta]', 'Correspondencia 2026');
  await f.click('button.btn.primary');
  ok((await f.textContent('.carpeta')).includes('Correspondencia 2026'), 'Archivado en carpeta');

  console.log('== Aislamiento de acceso');
  const o = await mk();
  await login(o, 'secretaria');
  await go(o, 'seguimiento/ver&id=1');
  ok((await o.textContent('.flash.error').catch(() => '')).includes('No tiene acceso') || (await o.url()).includes('dashboard'), 'Usuario ajeno no ve la hoja ajena');
  await go(o, 'admin/usuarios');
  ok((await o.textContent('body')).includes('No tiene permiso'), 'Usuario común no accede a administración');
  const csrf = await o.request.post(BASE + '/index.php?r=bandeja/recibir', { form: { solo: '1' } });
  ok(csrf.status() === 419, 'POST sin token CSRF rechazado (419)');

  console.log('== Ventanilla y consulta pública');
  const v = await mk();
  await login(v, 'ventanilla');
  await go(v, 'ventanilla/nueva');
  await v.fill('[name=remitente]', 'Comunidad Originaria Tacopaya');
  await v.fill('[name=referencia]', 'Solicitud de camino vecinal');
  await v.fill('[name=fojas]', '3');
  await v.selectOption('select[name=destino]', { label: 'Luis Rojas — Director de Obras Públicas' });
  await v.click('button.btn.primary');
  await v.waitForLoadState('domcontentloaded');
  ok((await v.textContent('.codigo')).length === 6, 'Cargo de recepción con código');
  await v.screenshot({ path: SHOTS + '/08-cargo.png' });
  const txt = await v.textContent('.hojaruta');
  const nur2 = txt.match(/GAMP\/\d+-\d+/)[0]; const cod = (await v.textContent('.codigo')).trim();
  const pub = await mk();
  await pub.goto(`${BASE}/index.php?r=consulta/index&nur=${encodeURIComponent(nur2)}&codigo=${cod}`, { waitUntil: 'domcontentloaded' });
  ok((await pub.textContent('.estado')).includes('Obras Públicas'), 'Consulta pública muestra oficina actual');
  await pub.screenshot({ path: SHOTS + '/09-consulta.png' });
  await pub.goto(`${BASE}/index.php?r=consulta/index&nur=${encodeURIComponent(nur2)}&codigo=ZZZZZZ`, { waitUntil: 'domcontentloaded' });
  ok((await pub.textContent('.flash.error')).includes('No se encontró'), 'Código incorrecto rechazado');

  console.log('== Reportes y admin');
  const j = await mk();
  await login(j, 'finanzas');
  await go(j, 'reporte/oficina');
  ok((await j.textContent('table.t')).includes('Ana Condori'), 'Reporte de oficina lista dependientes');
  await j.goto(BASE + '/index.php?r=reporte/recibida&generar=1');
  ok((await j.textContent('main')).includes('registro(s)'), 'Reporte recibida');
  const adm = await mk();
  await login(adm, 'admin', 'Admin12345');
  await go(adm, 'admin/auditoria');
  ok((await adm.locator('table.t tbody tr').count()) > 5, 'Auditoría registra acciones');
  await adm.screenshot({ path: SHOTS + '/10-admin.png' });
  const print = await mk(); await login(print, 'alcalde'); await print.goto(BASE + '/index.php?r=documento/ver&id=1', { waitUntil: 'domcontentloaded' });
  ok((await print.textContent('.memo')).includes('Se solicita el presupuesto') && !(await print.innerHTML('.memo')).includes('<script'), 'Documento imprimible sin scripts');
  await print.screenshot({ path: SHOTS + '/11-memo.png' });

  await browser.close();
  console.log(fallos ? `\n${fallos} FALLO(S)` : '\nTODO OK');
  process.exit(fallos ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
