<form method="post" class="form card narrow"><?= csrf_field() ?>
  <label>Nombre<input name="nombre" value="<?= e($t['nombre']) ?>" required maxlength="80"></label>
  <label>Prefijo del CITE<input name="prefijo" value="<?= e($t['prefijo']) ?>" required maxlength="10"></label>
  <label class="radio"><input type="checkbox" name="activo" value="1" <?= $t['activo'] ? 'checked' : '' ?>> Activo</label>
  <fieldset><legend>Oficinas habilitadas (ninguna marcada = todas)</legend><?php foreach ($oficinas as $o): ?><label class="radio"><input type="checkbox" name="oficinas[]" value="<?= (int)$o['id'] ?>" <?= in_array((int)$o['id'], $sel, true) ? 'checked' : '' ?>> <?= e($o['nombre']) ?></label><?php endforeach; ?></fieldset>
  <button class="btn primary">Guardar</button> <a class="btn" href="<?= url('admin/tipos') ?>">Cancelar</a></form>
