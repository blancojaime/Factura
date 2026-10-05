<p class="muted">Correspondencia derivada por usted.</p>
<label>Filtrar: <input type="search" data-filtro="tbody tr"></label>
<table class="t"><thead><tr><th>Hoja de ruta</th><th>Derivado a</th><th>Proveído</th><th>Fecha</th><th>Estado</th><th></th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><a href="<?= url('seguimiento/ver', ['id' => $r['hoja_id']]) ?>"><?= e($r['nur']) ?></a></td><td><b><?= e($r['a_nombre']) ?></b><br><small><?= e($r['a_cargo']) ?></small></td><td><?= e($r['proveido']) ?></td><td><?= e(fecha_corta($r['fecha_envio'])) ?></td>
  <td><?= ['no_recibido' => 'No recibido', 'pendiente' => 'Pendiente', 'derivado' => 'Derivado', 'archivado' => 'Archivado', 'agrupado' => 'Agrupado'][$r['estado']] ?? $r['estado'] ?></td>
  <td><a class="btn sm" href="<?= url('seguimiento/ver', ['id' => $r['hoja_id']]) ?>">Ver</a></td></tr><?php endforeach; ?>
<?php if (!$rows): ?><tr><td colspan="6" class="vacio">No ha derivado correspondencia.</td></tr><?php endif; ?></tbody></table>
