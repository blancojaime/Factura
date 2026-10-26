<form method="post" enctype="multipart/form-data" class="form card narrow"><?= csrf_field() ?>
  <p class="muted">Estos datos se imprimen en la <b>hoja de ruta</b>, la <b>etiqueta</b> y el <b>cargo de recepción</b>.</p>
  <label>Nombre oficial de la entidad<input name="nombre" value="<?= e($nombre) ?>" required maxlength="150"></label>
  <label>Entidad superior o línea adicional (opcional)<input name="superior" value="<?= e($superior) ?>" maxlength="150" placeholder="Ej. Estado Plurinacional de Bolivia"></label>
  <label>Logo (PNG o JPG, máx. 1 MB; fondo blanco o transparente)<input type="file" name="logo" accept="image/png,image/jpeg"></label>
  <?php if ($logo): ?><p>Logo actual:<br><img src="<?= e($logo) ?>" alt="Logo" style="max-height:90px;border:1px solid #d5dce6;padding:6px;background:#fff"></p>
  <label class="radio"><input type="checkbox" name="quitar_logo" value="1"> Quitar el logo actual</label><?php endif; ?>
  <button class="btn primary">Guardar</button></form>
