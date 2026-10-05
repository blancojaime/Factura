<p class="muted">Correspondencia derivada a usted, pendiente de recepción.</p>
<form method="post" action="<?= url('bandeja/recibir') ?>"><?= csrf_field() ?>
<?php include __DIR__ . '/_toolbar.php'; ?>
<?php if (!$items): ?><p class="vacio">No tiene correspondencia por recepcionar.</p><?php endif; ?>
<?php foreach ($items as $d) { $modo = 'entrada'; include __DIR__ . '/_item.php'; } ?>
<?php if ($items): ?><p><button class="btn primary" data-confirm="¿Recepcionar las hojas de ruta seleccionadas?">Recepcionar seleccionadas</button></p><?php endif; ?>
</form>
