<p><a href="<?= url('bandeja/archivados') ?>">← Carpetas</a></p>
<label>Filtrar: <input type="search" data-filtro="tbody tr"></label>
<table class="t"><thead><tr><th>Hoja de ruta</th><th>Documento</th><th>Referencia</th><th>Observaciones</th><th>Fecha</th><th></th></tr></thead><tbody>
<?php foreach ($items as $i): ?><tr><td><a href="<?= url('seguimiento/ver', ['id' => $i['hoja_id']]) ?>"><?= e($i['nur']) ?></a></td><td><?= e($i['cites']) ?></td><td><?= e($i['referencia']) ?></td><td><?= e($i['observacion']) ?></td><td><?= e(fecha_corta($i['fecha'])) ?></td>
  <td><form method="post" action="<?= url('bandeja/desarchivar') ?>"><?= csrf_field() ?><input type="hidden" name="id" value="<?= (int)$i['id'] ?>"><button class="btn sm">Desarchivar</button></form></td></tr><?php endforeach; ?>
<?php if (!$items): ?><tr><td colspan="6" class="vacio">Carpeta vacía.</td></tr><?php endif; ?></tbody></table>
