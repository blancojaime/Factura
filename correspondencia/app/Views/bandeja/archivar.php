<form method="post" class="form card"><?= csrf_field() ?><input type="hidden" name="confirmar" value="1">
  <p><b>Hojas de ruta a archivar:</b></p><ul><?php foreach ($sel as $s): ?><li><?= e($s['nur']) ?><input type="hidden" name="ids[]" value="<?= (int)$s['id'] ?>"></li><?php endforeach; ?></ul>
  <?php if ($carpetas): ?><label>Carpeta existente<select name="carpeta_id"><option value="0">— Seleccione —</option><?php foreach ($carpetas as $c): ?><option value="<?= (int)$c['id'] ?>"><?= e($c['nombre']) ?></option><?php endforeach; ?></select></label><?php endif; ?>
  <label>…o cree una nueva carpeta<input name="nueva_carpeta" maxlength="100" placeholder="Ej. Correspondencia <?= gestion() ?>"></label>
  <label>Observación<textarea name="observacion" rows="3" maxlength="255"></textarea></label>
  <button class="btn primary">Archivar</button> <a class="btn" href="<?= url('bandeja/pendientes') ?>">Cancelar</a>
</form>
