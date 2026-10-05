<form method="post" class="form card"><?= csrf_field() ?><input type="hidden" name="confirmar" value="1">
  <p>Seleccione la hoja de ruta <b>principal</b>: será la que aparezca en Pendientes y se derive; las demás viajarán con ella.</p>
  <?php foreach ($sel as $s): ?><label class="radio"><input type="radio" name="principal" value="<?= (int)$s['id'] ?>" required> <?= e($s['nur']) ?> — <?= e($s['referencia']) ?><input type="hidden" name="ids[]" value="<?= (int)$s['id'] ?>"></label><?php endforeach; ?>
  <button class="btn primary">Agrupar</button> <a class="btn" href="<?= url('bandeja/pendientes') ?>">Cancelar</a>
</form>
