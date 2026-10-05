<form method="post" class="form card narrow"><?= csrf_field() ?>
  <label>Contraseña actual<input type="password" name="actual" required autocomplete="current-password"></label>
  <label>Nueva contraseña (mínimo 8 caracteres)<input type="password" name="nueva" required minlength="8" autocomplete="new-password"></label>
  <label>Repita la nueva contraseña<input type="password" name="repite" required minlength="8" autocomplete="new-password"></label>
  <button class="btn primary">Cambiar contraseña</button></form>
