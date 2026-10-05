// Recorre el camino de una persona nueva: instalar → importar Excel → asignar nombres → primer ingreso con clave temporal.
// Uso: BASE=http://127.0.0.1:8080 EXCEL=database/Cargos_y_Oficinas_GAM.xlsx node tests/e2e_instalacion.js
const { chromium } = require(process.env.PW || 'playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:8080', SHOTS = process.env.SHOTS || '/tmp';
const DBUSER = process.env.DBUSER || 'corr', DBPASS = process.env.DBPASS || 'corr123';
let fallos = 0; const ok = (c, m) => { console.log((c ? '  OK   ' : '  FALLA ') + m); if (!c) fallos++; };
(async () => {
  const b = await chromium.launch(); const c = await b.newContext({ viewport: { width: 1280, height: 900 } }); const p = await c.newPage(); p.setDefaultTimeout(10000);
  await p.route(/cdnjs/, r => r.abort()); p.on('dialog', d => d.accept());
  await p.goto(BASE + '/install.php', { waitUntil: 'domcontentloaded' });
  await p.fill('[name=host]', '127.0.0.1'); await p.fill('[name=dbuser]', DBUSER); await p.fill('[name=dbpass]', DBPASS);
  await p.fill('[name=entidad]', 'Gobierno Autónomo Municipal de Prueba'); await p.fill('[name=sigla]', 'GAMP');
  await p.fill('[name=adm_nombre]', 'Administrador'); await p.fill('[name=adm_login]', 'admin'); await p.fill('[name=adm_pass]', 'Admin12345');
  await p.screenshot({ path: SHOTS + '/20-instalador.png', fullPage: true });
  await p.click('button.btn.primary'); await p.waitForLoadState('domcontentloaded');
  ok(p.url().includes('index.php') || (await p.textContent('h1')).includes('GAMP'), 'Instalador creó la base y llevó al login');
  await p.fill('[name=login]', 'admin'); await p.fill('[name=password]', 'Admin12345'); await p.click('button.btn.primary'); await p.waitForLoadState('domcontentloaded');
  await p.goto(BASE + '/index.php?r=admin/importar', { waitUntil: 'domcontentloaded' });
  await p.setInputFiles('input[type=file]', process.env.EXCEL || 'database/Cargos_y_Oficinas_GAM.xlsx'); await p.click('button.btn.primary'); await p.waitForLoadState('domcontentloaded');
  ok((await p.textContent('main')).includes('46') && (await p.textContent('main')).includes('4 oficina(s) nueva(s)'), 'Vista previa: 4 oficinas y 46 usuarios');
  await p.screenshot({ path: SHOTS + '/21-importar-previa.png', fullPage: true });
  await p.click('button:has-text("Confirmar e importar")'); await p.waitForLoadState('domcontentloaded');
  ok((await p.locator('table.t tbody tr').count()) === 46, 'Lista de 46 claves temporales');
  const fila = await p.locator('table.t tbody tr', { hasText: 'ALCALDE (SA) MUNICIPAL' }).first().locator('code').allTextContents();
  await p.screenshot({ path: SHOTS + '/22-credenciales.png', fullPage: true });
  await p.click('button:has-text("Ya la guardé")'); await p.waitForLoadState('domcontentloaded');
  await p.fill('input[name^="nombre["] >> nth=0', 'Persona de Prueba'); await p.click('button.btn.primary'); await p.waitForLoadState('domcontentloaded');
  ok((await p.textContent('.flash.ok')).includes('1 nombre'), 'Asignación de nombre guardada');
  await p.screenshot({ path: SHOTS + '/23-nombres.png', fullPage: true });
  // Primer ingreso del alcalde
  const q = await (await b.newContext()).newPage(); q.setDefaultTimeout(10000); await q.route(/cdnjs/, r => r.abort());
  await q.goto(BASE + '/index.php?r=auth/login', { waitUntil: 'domcontentloaded' });
  await q.fill('[name=login]', fila[0]); await q.fill('[name=password]', fila[1]); await q.click('button.btn.primary'); await q.waitForLoadState('domcontentloaded');
  ok((await q.textContent('h1')).includes('Cambiar contraseña'), 'Primer ingreso obliga a cambiar la clave');
  await q.goto(BASE + '/index.php?r=bandeja/entrada', { waitUntil: 'domcontentloaded' });
  ok((await q.textContent('h1')).includes('Cambiar contraseña'), 'No puede saltarse el cambio');
  await q.fill('[name=actual]', fila[1]); await q.fill('[name=nueva]', 'NuevaClave2026'); await q.fill('[name=repite]', 'NuevaClave2026'); await q.click('button.btn.primary'); await q.waitForLoadState('domcontentloaded');
  ok((await q.textContent('h1')).includes('Inicio'), 'Tras cambiar la clave entra al sistema');
  await q.screenshot({ path: SHOTS + '/24-alcalde.png' });
  await b.close(); console.log(fallos ? `\n${fallos} FALLO(S)` : '\nTODO OK'); process.exit(fallos ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
