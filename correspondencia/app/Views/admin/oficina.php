<form method="post" class="form card narrow"><?= csrf_field() ?>
  <label>Nombre<input name="nombre" value="<?= e($o['nombre']) ?>" required maxlength="150"></label>
  <label>Sigla (se usa en el CITE)<input name="sigla" value="<?= e($o['sigla']) ?>" required maxlength="20"></label>
  <label>Depende de<select name="padre_id"><option value="0">— Ninguna —</option><?php foreach ($padres as $p): ?><option value="<?= (int)$p['id'] ?>" <?= $o['padre_id'] == $p['id'] ? 'selected' : '' ?>><?= e($p['nombre']) ?></option><?php endforeach; ?></select></label>
  <label class="radio"><input type="checkbox" name="activa" value="1" <?= $o['activa'] ? 'checked' : '' ?>> Activa</label>
  <button class="btn primary">Guardar</button> <a class="btn" href="<?= url('admin/oficinas') ?>">Cancelar</a></form>
