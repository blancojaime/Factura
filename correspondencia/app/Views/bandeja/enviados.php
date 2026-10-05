<p class="muted">Correspondencia enviada por usted que el destinatario aún no ha recepcionado.</p>
<form method="post"><?= csrf_field() ?>
<div class="toolbar"><label>Filtrar: <input type="search" data-filtro=".item"></label>
  <label><input type="checkbox" data-todos=".item input[type=checkbox]"> Seleccionar todo</label></div>
<?php if (!$items): ?><p class="vacio">No hay correspondencia enviada pendiente de recepción.</p><?php endif; ?>
<?php foreach ($items as $d) { $modo = 'enviados'; include __DIR__ . '/_item.php'; } ?>
<?php if ($items): ?><div class="cuaderno"><b>Imprimir cuaderno de derivaciones</b> — posición inicial en la hoja:
  <select name="pos"><?php for ($i = 1; $i <= 6; $i++): ?><option><?= $i ?></option><?php endfor; ?></select>
  <button class="btn" formaction="<?= url('bandeja/cuaderno') ?>" formtarget="_blank">Generar PDF / imprimir</button></div><?php endif; ?>
</form>
