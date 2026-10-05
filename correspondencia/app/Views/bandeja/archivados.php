<?php if (!$carpetas): ?><p class="vacio">Aún no tiene carpetas. Se crean al archivar correspondencia desde Pendientes.</p><?php endif; ?>
<div class="carpetas"><?php foreach ($carpetas as $f): ?>
  <a class="carpeta" href="<?= url('bandeja/archivados', ['carpeta' => $f['id']]) ?>">📁 <b><?= e($f['nombre']) ?></b><br><small><?= (int)$f['n'] ?> trámite(s) archivado(s)</small></a><?php endforeach; ?></div>
