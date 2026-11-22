const C = require('./cap.js'); const { execSync } = require('child_process');
const { ses, go, shot, optLabel, fs, B } = C;
const sql = q => execSync(`mariadb -uroot correspondencia -e "${q}"`).toString();
(async () => {
  await C.launch();
  const v = await ses(B, 'u435');
  await go(v, 'ventanilla/index'); await shot(v, '40-ventanilla-lista-vacia', { alto: 600, marks: [['.vent-head', 1], ['a.vent-nuevo', 2]] });
  await go(v, 'ventanilla/nueva');
  await v.fill('[name=remitente]', 'Juan Pérez Mamani'); await v.fill('[name=institucion]', 'Comunidad Campesina Tacopaya'); await v.fill('[name=celular]', '71234567');
  await v.fill('[name=documento]', 'Nota CCT-014/2026'); await v.fill('[name=fojas]', '3'); await v.fill('[name=anexos]', '1 planilla');
  await v.fill('[name=referencia]', 'Solicitud de mantenimiento del camino vecinal');
  await v.selectOption('select[name=destino]', { label: await optLabel(v, 'select[name=destino]', 'Ana Mamani') });
  await v.fill('[name=proveido]', 'Para su consideración y trámite');
  await shot(v, '41-ventanilla-nueva', { alto: 1500, marks: [['.vent-sec.s1', 1], ['.vent-sec.s2', 2], ['.vent-sec.s3', 3], ['.vent-sec.s4', 4], ['button.btn.primary', 5]] });
  await v.click('button.btn.primary'); await v.waitForLoadState('domcontentloaded');
  await shot(v, '42-ventanilla-registrada', { alto: 700, marks: [['.flash.ok', 1]] });
  await go(v, 'ventanilla/index'); await shot(v, '43-ventanilla-lista', { alto: 600, marks: [['a.sello', 1], ['code', 2]] });
  const id = sql("SELECT id FROM hojas_ruta WHERE ext_remitente LIKE 'Juan%' ORDER BY id DESC LIMIT 1").split('\n')[1];
  const nur = sql(`SELECT nur FROM hojas_ruta WHERE id=${id}`).split('\n')[1], cod = sql(`SELECT codigo_consulta FROM hojas_ruta WHERE id=${id}`).split('\n')[1];
  await go(v, 'ventanilla/cargo&id=' + id); await shot(v, '44-cargo', { alto: 1000, marks: [['a[href*="sello"]', 1], ['.rc-codigo', 2], ['[data-qr]', 3]] });
  await go(v, 'ventanilla/sello&id=' + id); await v.waitForTimeout(500);
  await shot(v, '45-sello-form', { alto: 1100, marks: [['fieldset', 1], ['select[name=tam]', 2], ['input[name=dx]', 3], ['button.primary', 4], ['.sello-hoja', 5]] });
  for (const [pos, n] of [['sd', 'sup-der'], ['md', 'media-der'], ['id', 'inf-der']]) {
    await v.goto(`${B}/index.php?r=ventanilla/sello&id=${id}&f=1&pos[]=${pos}&tam=m`, { waitUntil: 'domcontentloaded' }); await v.waitForTimeout(500);
    await C.pdf(v, `/tmp/sello_${n}.pdf`);
    execSync(`pdftoppm -r 70 -png -singlefile /tmp/sello_${n}.pdf /tmp/sello_${n}`);
  }
  await v.goto(`${B}/index.php?r=ventanilla/sello&id=${id}&f=1&pos[]=sd&pos[]=id&tam=m`, { waitUntil: 'domcontentloaded' }); await v.waitForTimeout(500);
  await C.pdf(v, '/tmp/sello_dos.pdf'); execSync('pdftoppm -r 70 -png -singlefile /tmp/sello_dos.pdf /tmp/sello_dos');
  // Mock "copia de la nota" con sello superpuesto: composición HTML con el PDF rasterizado de fondo
  const nota = (b64) => `<body style="margin:0;background:#ddd;display:flex;gap:14px;padding:14px;font-family:serif">${['sup-der','media-der','inf-der'].map((n,i)=>`<div style="position:relative;width:360px;height:466px;background:#fff;box-shadow:0 2px 8px #0006;overflow:hidden">
   <div style="padding:34px 100px 34px 30px;font-size:8.5px;line-height:1.5;color:#333"><p style="text-align:right">Tacopaya, 12 de mayo de 2026</p><p><b>Señora Alcaldesa Municipal<br>Presente.-</b></p><p><b>Ref.: Solicitud de mantenimiento del camino vecinal</b></p>${'<p>De mi mayor consideración: por medio de la presente, la comunidad solicita atender el mantenimiento del camino vecinal que une las comunidades, por el estado en que se encuentra tras las lluvias de la gestión.</p>'.repeat(3)}<p style="margin-top:50px;text-align:center">Juan Pérez Mamani<br>Representante</p></div>
   <img src="file:///tmp/sello_${n}.png" style="position:absolute;inset:0;width:100%;height:100%;mix-blend-mode:multiply"></div>`).join('')}</body>`;
  fs.writeFileSync('/tmp/nota.html', '<meta charset=utf-8>'+nota()); const m = await C.ses(B); await m.goto('file:///tmp/nota.html'); await m.setViewportSize({ width: 1200, height: 500 });
  await m.screenshot({ path: C.IMG + '46-sello-tres-posiciones.jpg', type: 'jpeg', quality: 85 }); console.log('  img 46');
  // impresión: PNG de la hoja del sello
  fs.copyFileSync('/tmp/sello_sup-der.png', C.IMG + '47-sello-impreso.png');
  // QR decodificado
  try { const out = execSync('zbarimg -q --raw /tmp/sello_sup-der.png 2>&1 || true').toString(); fs.writeFileSync(C.dir + '/qr_sello.txt', out); console.log(out.slice(0, 300)); } catch (e) {}
  // ---- Derivar y avanzar para trazabilidad
  const a = await ses(B, 'u402'); await go(a, 'bandeja/entrada');
  const r = await ses(B, 'u401'); await go(r, 'bandeja/entrada'); await r.locator('article.item', { hasText: 'camino vecinal' }).locator('button', { hasText: 'Recepcionar' }).click(); await r.waitForLoadState('domcontentloaded');
  await go(r, 'hoja/derivar&id=' + id); await r.selectOption('select[name=destino]', { label: await optLabel(r, 'select[name=destino]', 'Elena Vargas') }); await r.fill('[name=proveido]', 'Atender con prioridad'); await r.click('button[value=oficial]'); await r.waitForLoadState('domcontentloaded');
  // ---- Hoja de ruta con código de control
  await go(r, 'hoja/imprimir&id=' + id); await r.waitForTimeout(600); await shot(r, '48-hoja-ruta-control', { alto: 760, marks: [['.hr-titulo em', 1], ['[data-qr]', 2]] });
  // ---- Consulta pública
  const pub = await ses(B); await go(pub, 'consulta/index'); await shot(pub, '50-consulta-form', { alto: 600, marks: [['[name=nur]', 1], ['[name=codigo]', 2], ['button.primary', 3]] });
  await pub.fill('[name=nur]', nur); await pub.fill('[name=codigo]', 'ZZZZZZ'); await pub.click('button.primary'); await pub.waitForLoadState('domcontentloaded'); await shot(pub, '51-consulta-error', { alto: 600, marks: [['.flash', 1]] });
  await pub.fill('[name=nur]', nur); await pub.fill('[name=codigo]', cod); await pub.click('button.primary'); await pub.waitForLoadState('domcontentloaded');
  await shot(pub, '52-consulta-resultado', { alto: 1300, marks: [['.cs-estado', 1], ['.cs-actual', 2], ['.cs-linea', 3]] });
  fs.writeFileSync(C.dir + '/datos12.json', JSON.stringify({ id, nur, cod }));
  await C.close(); console.log('FIN v12', nur, cod);
})().catch(e => { console.error(e); process.exit(1); });
