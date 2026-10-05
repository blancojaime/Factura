<form method="post" class="form card narrow"><?= csrf_field() ?>
  <label>Usuario (no modificable)<input value="<?= e($u['login']) ?>" disabled></label>
  <label>Nombre completo<input name="nombre" value="<?= e($u['nombre']) ?>" required maxlength="120"></label>
  <label>Cargo<input name="cargo" value="<?= e($u['cargo']) ?>" maxlength="150"></label>
  <label>Mosca (iniciales)<input name="mosca" value="<?= e($u['mosca']) ?>" maxlength="10"></label>
  <label>Correo electrónico<input type="email" name="email" value="<?= e($u['email']) ?>"></label>
  <label>Género<select name="genero"><option value="M" <?= $u['genero'] === 'M' ? 'selected' : '' ?>>Hombre</option><option value="F" <?= $u['genero'] === 'F' ? 'selected' : '' ?>>Mujer</option></select></label>
  <button class="btn primary">Modificar datos</button></form>
