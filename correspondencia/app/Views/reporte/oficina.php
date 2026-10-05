<?php if ($oficinas): ?><form method="get" class="toolbar"><input type="hidden" name="r" value="reporte/oficina"><label>Oficina <select name="oficina" onchange="this.form.submit()"><?php foreach ($oficinas as $o): ?><option value="<?= (int)$o['id'] ?>" <?= $o['id'] == $oficina['id'] ? 'selected' : '' ?>><?= e($o['nombre']) ?></option><?php endforeach; ?></select></label></form><?php endif; ?>
<p class="noprint"><button class="btn" data-print>Imprimir</button></p>
<h3><?= e($oficina['nombre']) ?></h3>
<canvas data-chart='<?= e(json_encode($grafico)) ?>' height="110"></canvas>
<table class="t"><thead><tr><th>Funcionario</th><th>Pendientes oficiales</th><th>Copias pendientes</th><th>Sin recibir</th><th>Archivados</th></tr></thead><tbody>
<?php foreach ($filas as $f): ?><tr><td><b><?= e($f['nombre']) ?></b><br><small><?= e($f['cargo']) ?></small></td><td><?= (int)$f['oficial'] ?></td><td><?= (int)$f['copia'] ?></td><td><?= (int)$f['no_recibido'] ?></td><td><?= (int)$f['archivado'] ?></td></tr><?php endforeach; ?></tbody></table>
