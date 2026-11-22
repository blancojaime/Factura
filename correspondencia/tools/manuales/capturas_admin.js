const C = require('./cap.js'); const { ses, go, shot, B } = C;
(async () => {
  await C.launch(); const a = await ses(B, 'admin', 'Admin12345');
  await shot(a, '60-admin-inicio', { alto: 700, marks: [['nav.main', 1], ['.who', 2]] });
  for (const [r, n, alto] of [['admin/importar', '61-admin-importar', 800], ['admin/credenciales', '62-admin-credenciales', 700], ['admin/nombres', '63-admin-nombres', 800], ['admin/usuarios', '64-admin-usuarios', 800], ['admin/oficinas', '65-admin-oficinas', 800], ['admin/tipos', '66-admin-tipos', 800], ['admin/auditoria', '67-admin-auditoria', 800], ['admin/entidad', '68-admin-entidad', 800]]) {
    await go(a, r); await shot(a, n, { alto }); }
  await C.close();
})();
