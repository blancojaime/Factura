<form method="get" class="form card"><input type="hidden" name="r" value="<?= e($accion) ?>"><input type="hidden" name="generar" value="1">
  <div class="cols">
    <label><?= $lado === 'a' ? 'Recibida por' : 'Enviada por' ?><select name="quien"><option value="0">Todos</option><?php foreach ($alcance as $a): ?><option value="<?= (int)$a['id'] ?>" <?= $quien == $a['id'] ? 'selected' : '' ?>><?= e($a['nombre']) ?></option><?php endforeach; ?></select></label>
    <?php if ($conEstado): ?><label>Estado<select name="estado"><?php foreach ($estados as $k => $t): ?><option value="<?= e($k) ?>" <?= $estado === (string)$k ? 'selected' : '' ?>><?= e($t) ?></option><?php endforeach; ?></select></label><?php endif; ?>
    <label>Desde<input type="date" name="desde" value="<?= e($desde) ?>"></label><label>Hasta<input type="date" name="hasta" value="<?= e($hasta) ?>"></label></div>
  <button class="btn primary">Generar reporte</button>
  <?php if ($rows !== null): ?><button class="btn" name="csv" value="1">Exportar CSV (Excel)</button><button class="btn" type="button" data-print>Imprimir</button><?php endif; ?></form>
<?php if ($rows !== null): ?>
<p class="muted"><?= count($rows) ?> registro(s) del <?= e($desde) ?> al <?= e($hasta) ?>.</p>
<table class="t"><thead><tr><th>#</th><th>NUR</th><th>Documento</th><th>Referencia</th><th>Derivado por</th><th>Derivado a</th><th>Proveído</th><th>Estado</th><th>Emisión</th><th>Recepción</th></tr></thead><tbody>
<?php foreach ($rows as $i => $r): ?><tr><td><?= $i + 1 ?></td><td><?= e($r['nur']) ?></td><td><?= e($r['cites']) ?></td><td><?= e($r['referencia']) ?></td><td><?= e($r['de_nombre']) ?></td><td><?= e($r['a_nombre']) ?><?= $r['tipo'] === 'copia' ? ' [copia]' : '' ?></td><td><?= e($r['proveido']) ?></td><td><?= e($estados[$r['estado']] ?? $r['estado']) ?></td><td><?= e(fecha_corta($r['fecha_envio'])) ?></td><td><?= e(fecha_corta($r['fecha_recepcion'])) ?></td></tr><?php endforeach; ?>
<?php if (!$rows): ?><tr><td colspan="10" class="vacio">Sin resultados.</td></tr><?php endif; ?></tbody></table><?php endif; ?>
