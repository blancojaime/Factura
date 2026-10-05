<main class="card narrow">
  <h1>Consulta de trámite</h1>
  <p class="muted">Ingrese el número de hoja de ruta (NUR) y el código que figura en su comprobante de recepción.</p>
  <?php if ($error): ?><div class="flash error"><?= e($error) ?></div><?php endif; ?>
  <form method="get" class="form"><input type="hidden" name="r" value="consulta/index">
    <label>NUR<input name="nur" value="<?= e($nur) ?>" placeholder="GAM/2026-00001" required></label>
    <label>Código<input name="codigo" value="<?= e($codigo) ?>" maxlength="10" required></label>
    <button class="btn primary">Consultar</button>
  </form>
  <?php if ($res): $h = $res['h']; ?>
    <hr><h3><?= e($h['nur']) ?></h3>
    <p><strong>Asunto:</strong> <?= e($h['referencia']) ?><br><strong>Registrado:</strong> <?= e(fecha_corta($h['creado_en'])) ?></p>
    <p class="estado"><strong>Situación:</strong>
      <?= $res['enCurso'] ? 'En trámite en: ' . e(implode(', ', $res['enCurso'])) : ($res['archivado'] ? 'Trámite concluido / archivado' : 'Registrado, pendiente de derivación') ?></p>
    <table class="t"><thead><tr><th>Fecha</th><th>De</th><th>A</th><th>Estado</th></tr></thead><tbody>
    <?php foreach ($res['mov'] as $m): ?><tr><td><?= e(fecha_corta($m['fecha_envio'])) ?></td><td><?= e($m['de_oficina']) ?></td><td><?= e($m['a_oficina']) ?></td><td><?= $m['fecha_recepcion'] ? 'Recibido' : 'Enviado' ?></td></tr><?php endforeach; ?>
    </tbody></table>
  <?php endif; ?>
  <p class="muted"><a href="<?= url('auth/login') ?>">Ingreso de funcionarios</a></p>
</main>
