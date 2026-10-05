<main class="card narrow login">
  <h1><?= e(App\Core\Config::get('entidad_sigla', 'Correspondencia')) ?></h1>
  <p class="muted">Sistema de Correspondencia Digital · <?= e(App\Core\Config::get('entidad', '')) ?></p>
  <?php if ($error): ?><div class="flash error"><?= e($error) ?></div><?php endif; ?>
  <form method="post" class="form"><?= csrf_field() ?>
    <label>Nombre de usuario<input name="login" value="<?= e($login) ?>" required autofocus autocomplete="username"></label>
    <label>Contraseña<input name="password" type="password" required autocomplete="current-password"></label>
    <button class="btn primary">Ingresar</button>
  </form>
  <p class="muted"><a href="<?= url('consulta/index') ?>">Consultar el estado de un trámite</a></p>
</main>
