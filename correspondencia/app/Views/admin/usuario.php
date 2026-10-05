<form method="post" class="form card narrow"><?= csrf_field() ?>
  <label>Usuario (login)<input name="login" value="<?= e($u['login']) ?>" <?= $u['id'] ? 'disabled' : 'required' ?> maxlength="60"></label>
  <label>Nombre completo<input name="nombre" value="<?= e($u['nombre']) ?>" required maxlength="120"></label>
  <label>Cargo<input name="cargo" value="<?= e($u['cargo']) ?>" maxlength="150"></label>
  <div class="cols"><label>Mosca (iniciales)<input name="mosca" value="<?= e($u['mosca']) ?>" maxlength="10"></label>
  <label>Género<select name="genero"><option value="M" <?= $u['genero'] === 'M' ? 'selected' : '' ?>>Hombre</option><option value="F" <?= $u['genero'] === 'F' ? 'selected' : '' ?>>Mujer</option></select></label></div>
  <label>Correo<input type="email" name="email" value="<?= e($u['email']) ?>"></label>
  <label>Oficina<select name="oficina_id" required><option value="">— Seleccione —</option><?php foreach ($oficinas as $o): ?><option value="<?= (int)$o['id'] ?>" <?= $u['oficina_id'] == $o['id'] ? 'selected' : '' ?>><?= e($o['nombre']) ?></option><?php endforeach; ?></select></label>
  <label>Jefe inmediato (para "usuarios dependientes")<select name="jefe_id"><option value="0">— Ninguno —</option><?php foreach ($jefes as $j): ?><option value="<?= (int)$j['id'] ?>" <?= $u['jefe_id'] == $j['id'] ? 'selected' : '' ?>><?= e($j['nombre'] . ' — ' . $j['cargo']) ?></option><?php endforeach; ?></select></label>
  <label>Rol<select name="rol"><?php foreach (['usuario' => 'Usuario', 'jefe' => 'Jefe / responsable de oficina', 'ventanilla' => 'Ventanilla (correspondencia externa)', 'admin' => 'Administrador'] as $k => $t): ?><option value="<?= $k ?>" <?= $u['rol'] === $k ? 'selected' : '' ?>><?= $t ?></option><?php endforeach; ?></select></label>
  <label>Contraseña <?= $u['id'] ? '(dejar vacío para no cambiar)' : '(mínimo 8 caracteres)' ?><input type="password" name="password" autocomplete="new-password" <?= $u['id'] ? '' : 'required' ?>></label>
  <label class="radio"><input type="checkbox" name="activo" value="1" <?= $u['activo'] ? 'checked' : '' ?>> Activo</label>
  <button class="btn primary">Guardar</button> <a class="btn" href="<?= url('admin/usuarios') ?>">Cancelar</a></form>
