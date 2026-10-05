<p class="muted">Hojas de ruta que usted ha recepcionado. Seleccione varias para agrupar o archivar.</p>
<form method="post" id="fpend"><?= csrf_field() ?>
<?php include __DIR__ . '/_toolbar.php'; ?>
<p class="mostrar">Mostrar: <?php foreach (['todo' => 'Oficial y copia', 'oficial' => 'Oficial', 'copia' => 'Copia'] as $k => $t): ?>
  <a href="<?= url('bandeja/pendientes', ['mostrar' => $k, 'orden' => $orden]) ?>" class="<?= $mostrar === $k ? 'on' : '' ?>"><?= $t ?></a><?php endforeach; ?></p>
<?php if (!$items): ?><p class="vacio">No tiene correspondencia pendiente.</p><?php endif; ?>
<?php foreach ($items as $d) { $modo = 'pendientes'; include __DIR__ . '/_item.php'; } ?>
<?php if ($items): ?><p class="acciones-lote">Con las seleccionadas:
  <button class="btn" formaction="<?= url('bandeja/agrupar') ?>">Agrupar</button>
  <button class="btn" formaction="<?= url('bandeja/archivar') ?>">Archivar</button></p><?php endif; ?>
</form>
