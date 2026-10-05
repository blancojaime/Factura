<div class="chips"><a class="<?= !$tipo ? 'on' : '' ?>" href="<?= url('documento/creados') ?>">Todos</a><?php foreach ($conteo as $c): ?><a class="<?= $tipo == $c['id'] ? 'on' : '' ?>" href="<?= url('documento/creados', ['tipo' => $c['id']]) ?>"><?= e($c['nombre']) ?>: <?= (int)$c['n'] ?></a><?php endforeach; ?></div>
<label>Filtrar: <input type="search" data-filtro="tbody tr"></label>
<table class="t"><thead><tr><th>CITE</th><th>Tipo</th><th>Referencia</th><th>Destinatario</th><th>Fecha</th><th>Hoja de ruta</th></tr></thead><tbody>
<?php foreach ($docs as $d): ?><tr><td><a href="<?= url('documento/editar', ['id' => $d['id']]) ?>"><?= e($d['cite']) ?></a></td><td><?= e($d['tipo']) ?></td><td><?= e($d['referencia']) ?></td><td><?= e($d['destinatario_nombre']) ?><br><small><?= e($d['destinatario_cargo']) ?></small></td><td><?= e(fecha_corta($d['creado_en'])) ?></td>
  <td><a href="<?= url('hoja/derivar', ['id' => $d['hoja_id']]) ?>"><?= e($d['nur']) ?></a></td></tr><?php endforeach; ?>
<?php if (!$docs): ?><tr><td colspan="6" class="vacio">Aún no ha creado documentos.</td></tr><?php endif; ?></tbody></table>
