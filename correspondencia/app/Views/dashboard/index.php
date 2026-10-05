<div class="grid4">
  <section class="panel p-verde"><h3>Bandeja</h3>
    <a class="row" href="<?= url('bandeja/entrada') ?>"><b>Entrada</b><span>Tiene <?= (int)$c['no_recibido'] ?> trámite(s) que le fueron derivados</span></a>
    <a class="row" href="<?= url('bandeja/pendientes') ?>"><b>Pendientes</b><span>Tiene <?= (int)$c['pendiente'] ?> correspondencia(s) pendiente(s)</span></a>
    <a class="row" href="<?= url('bandeja/archivados') ?>"><b>Archivados</b><span>Tiene <?= (int)$c['archivado'] ?> archivado(s)</span></a>
    <a class="row" href="<?= url('bandeja/agrupados') ?>"><b>Agrupados</b><span>Tiene <?= (int)$c['grupos'] ?> agrupado(s)</span></a>
  </section>
  <section class="panel p-azul"><h3>Documentos</h3>
    <?php foreach ($docs as $d): ?><a class="row" href="<?= url('documento/creados') ?>"><b><?= e($d['nombre']) ?></b><span><?= (int)$d['n'] ?> documento(s)</span></a><?php endforeach; ?>
    <a class="row" href="<?= url('documento/index') ?>"><b>+ Crear nuevo documento</b></a>
  </section>
  <section class="panel p-morado"><h3>Estadísticas</h3><p class="muted">Pendientes y archivados por usuario de su oficina</p>
    <canvas data-chart='<?= e(json_encode($grafico)) ?>' height="200"></canvas>
  </section>
  <section class="panel p-naranja"><h3>Usuario</h3>
    <a class="row" href="<?= url('usuario/password') ?>"><b>Cambiar contraseña</b><span>Cambie su contraseña</span></a>
    <a class="row" href="<?= url('usuario/datos') ?>"><b>Cambiar datos</b><span>Nombre, cargo o e-mail</span></a>
  </section>
</div>
<?php if ($dependientes): ?><h2>Usuarios dependientes</h2><div class="deps">
  <?php foreach ($dependientes as $d): ?><div class="dep"><b><?= e($d['nombre']) ?></b><br><?= e($d['cargo']) ?><br>Pendientes: <b><?= (int)$d['pendientes'] ?></b></div><?php endforeach; ?></div><?php endif; ?>
