<?php
use App\Core\Auth;
$u = Auth::user();
$menu = $menu ?? '';
$nav = [
    'inicio' => ['Inicio', 'dashboard/index'], 'bandeja' => ['Bandeja', 'bandeja/entrada'], 'documentos' => ['Documentos', 'documento/index'],
    'hojas' => ['Hojas de Ruta', 'hoja/lista'], 'seguimiento' => ['Seguimiento', 'seguimiento/index'],
];
if (Auth::esJefe() || Auth::es('admin')) $nav['reportes'] = ['Reportes', 'reporte/recibida'];
if (Auth::es('admin', 'ventanilla')) $nav['ventanilla'] = ['Ventanilla', 'ventanilla/index'];
if (Auth::es('admin')) $nav['admin'] = ['Administración', 'admin/usuarios'];
$sub = [
    'bandeja' => [['Entrada', 'bandeja/entrada'], ['Pendientes', 'bandeja/pendientes'], ['Enviados', 'bandeja/enviados'], ['Archivados', 'bandeja/archivados'], ['Agrupados', 'bandeja/agrupados']],
    'documentos' => [['Crear nuevo documento', 'documento/index'], ['Documentos creados', 'documento/creados'], ['Archivos digitales', 'documento/archivos']],
    'hojas' => [['Lista de hojas de ruta', 'hoja/lista'], ['Imprimir hoja de ruta', 'hoja/imprimir']],
    'reportes' => [['Pendientes oficina', 'reporte/oficina'], ['Correspondencia recibida', 'reporte/recibida'], ['Correspondencia enviada', 'reporte/enviada'], ['Personalizado', 'reporte/personalizado']],
    'ventanilla' => [['Registros externos', 'ventanilla/index'], ['Registrar nueva', 'ventanilla/nueva']],
    'admin' => [['Usuarios', 'admin/usuarios'], ['Oficinas', 'admin/oficinas'], ['Importar cargos (Excel)', 'admin/importar'], ['Asignar nombres', 'admin/nombres'], ['Tipos de documento', 'admin/tipos'], ['Auditoría', 'admin/auditoria']],
    'usuario' => [['Cambiar contraseña', 'usuario/password'], ['Cambiar mis datos', 'usuario/datos'], ['Mi información', 'usuario/info']],
];
$actual = $_GET['r'] ?? '';
?><!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title><?= e($titulo ?? '') ?> · <?= e(App\Core\Config::get('entidad_sigla', 'Correspondencia')) ?></title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/quill/1.3.7/quill.snow.min.css">
<link rel="stylesheet" href="<?= asset('css/app.css') ?>"></head>
<body>
<header class="top">
  <div class="brand"><a href="<?= url('dashboard/index') ?>"><strong>Correspondencia</strong><small><?= e(App\Core\Config::get('entidad', '')) ?></small></a></div>
  <form class="search" action="<?= url() ?>" method="get"><input type="hidden" name="r" value="busqueda/index"><input name="q" placeholder="Buscar NUR, CITE o referencia" aria-label="Buscar"><button>Buscar</button></form>
  <div class="who"><a href="<?= url('usuario/info') ?>" title="Mi información"><?= e($u['nombre']) ?></a>
    <form method="post" action="<?= url('auth/salir') ?>"><?= csrf_field() ?><button class="link">Salir</button></form></div>
</header>
<nav class="main"><?php foreach ($nav as $k => [$t, $r]): ?><a href="<?= url($r) ?>" class="<?= $menu === $k ? 'on' : '' ?>"><?= e($t) ?></a><?php endforeach; ?></nav>
<div class="wrap<?= isset($sub[$menu]) ? ' con-sub' : '' ?>">
<?php if (isset($sub[$menu])): ?>
  <aside class="sub"><h4><?= e($nav[$menu][0] ?? 'Mi cuenta') ?></h4>
  <?php foreach ($sub[$menu] as [$t, $r]): ?><a href="<?= url($r) ?>" class="<?= $actual === $r ? 'on' : '' ?>"><?= e($t) ?><?php
      if ($menu === 'bandeja' && isset($c)) { $n = ['bandeja/entrada' => $c['no_recibido'], 'bandeja/pendientes' => $c['pendiente']][$r] ?? 0; if ($n) echo ' <span class="badge">' . (int)$n . '</span>'; } ?></a><?php endforeach; ?>
  <?= $submenu_extra ?? '' ?></aside>
<?php endif; ?>
<main>
<?php foreach (flash() ?? [] as [$tipo, $msg]): ?><div class="flash <?= e($tipo) ?>"><?= e($msg) ?></div><?php endforeach; ?>
<h1><?= e($titulo ?? '') ?></h1>
<?= $contenido ?>
</main></div>
<script>window.CSRF=<?= json_encode(App\Core\Csrf::token()) ?>;window.URL_HOJAS=<?= json_encode(url('documento/hojas')) ?>;</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/quill/1.3.7/quill.min.js" defer></script>
<script src="<?= asset('js/app.js') ?>" defer></script>
</body></html>
