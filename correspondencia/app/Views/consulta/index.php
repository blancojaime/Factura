<main class="card consulta">
  <h1>Consulta de trámite</h1>
  <p class="muted">Ingrese el <b>número de trámite (NUR)</b> y el <b>código de control de la hoja de ruta</b> que figura en su comprobante de recepción.</p>
  <?php if ($error): ?><div class="flash error"><?= e($error) ?></div><?php endif; ?>
  <form method="get" class="form"><input type="hidden" name="r" value="consulta/index">
    <div class="cols"><label>NUR<input name="nur" value="<?= e($nur) ?>" placeholder="GAM/2026-00001" required></label>
    <label>Código de control<input name="codigo" value="<?= e($codigo) ?>" maxlength="10" required placeholder="6 caracteres"></label></div>
    <button class="btn primary">Consultar</button>
  </form>
  <?php if ($res): $h = $res['h']; ?>
    <hr>
    <div class="cs-ficha"><div><span>Trámite</span><b><?= e($h['nur']) ?></b></div><div><span>Código de control</span><b><?= e($h['codigo_consulta']) ?></b></div>
      <div><span>Registrado</span><b><?= e(fecha_corta($h['creado_en'])) ?></b></div><div><span>Tiempo transcurrido</span><b><?= (int)$res['total_dias'] ?> día(s)</b></div></div>
    <p><strong>Asunto:</strong> <?= e($h['referencia']) ?></p>
    <?php if ($res['origen']): ?><p><strong>Origen:</strong> <?= e($res['origen']['oficina']) ?> — <?= e($res['origen']['cargo']) ?></p><?php endif; ?>
    <div class="cs-estado <?= $res['estado'] === 'Concluido / archivado' ? 'fin' : 'curso' ?>"><span>Estado del trámite</span><b><?= e($res['estado']) ?></b></div>
    <h3>¿Dónde se encuentra ahora?</h3>
    <?php if ($res['actual']): foreach ($res['actual'] as $a): ?>
      <div class="cs-actual"><b><?= e($a['a_oficina']) ?></b><span><?= e($a['a_cargo']) ?><?= $a['tipo'] === 'copia' ? ' (copia informativa)' : '' ?></span>
        <small><?= $a['estado'] === 'pendiente' ? 'Recibido el ' . e(fecha_corta($a['fecha_recepcion'])) : 'Enviado el ' . e(fecha_corta($a['fecha_envio'])) . ' · aún no recibido' ?> · <?= (int)$a['dias'] ?> día(s) en este puesto</small></div>
    <?php endforeach; else: ?><div class="cs-actual"><b><?= $res['estado'] === 'Concluido / archivado' ? 'Trámite concluido y archivado' : 'Sin derivaciones registradas' ?></b></div><?php endif; ?>
    <h3>Trazabilidad completa</h3>
    <table class="t cs-linea"><thead><tr><th>#</th><th>Envío</th><th>De (oficina — cargo)</th><th>A (oficina — cargo)</th><th>Recepción</th><th>Días</th><th>Estado</th></tr></thead><tbody>
    <?php $estados = ['no_recibido' => 'Enviado, sin recibir', 'pendiente' => 'En atención', 'derivado' => 'Derivado a otra oficina', 'archivado' => 'Archivado', 'agrupado' => 'Agrupado'];
    foreach ($res['ders'] as $i => $m): ?><tr class="<?= $m['vigente'] ? 'vigente' : '' ?><?= $m['tipo'] === 'copia' ? ' copia' : '' ?>"><td><?= $i + 1 ?></td><td><?= e(fecha_corta($m['fecha_envio'])) ?></td>
      <td><b><?= e($m['de_oficina']) ?></b><br><small><?= e($m['de_cargo']) ?></small></td><td><b><?= e($m['a_oficina']) ?></b> <?= $m['tipo'] === 'copia' ? '<span class="tag copia">COPIA</span>' : '' ?><br><small><?= e($m['a_cargo']) ?></small></td>
      <td><?= $m['fecha_recepcion'] ? e(fecha_corta($m['fecha_recepcion'])) : '—' ?></td><td><?= (int)$m['dias'] ?></td><td><?= e($estados[$m['estado']] ?? $m['estado']) ?></td></tr><?php endforeach; ?>
    <?php if (!$res['ders']): ?><tr><td colspan="7" class="vacio">Aún no se registraron derivaciones.</td></tr><?php endif; ?>
    </tbody></table>
    <p class="muted">Por privacidad solo se muestran oficinas y cargos; no se publican nombres de personas ni el contenido de los documentos.</p>
    <p><button class="btn" onclick="window.print()">Imprimir esta consulta</button></p>
  <?php endif; ?>
  <p class="muted"><a href="<?= url('auth/login') ?>">Ingreso de funcionarios</a></p>
</main>
