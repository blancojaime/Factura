<p><a class="btn primary" href="<?= url('admin/tipo') ?>">+ Nuevo tipo</a></p>
<table class="t"><thead><tr><th>Nombre</th><th>Prefijo CITE</th><th>Habilitado en</th><th>Estado</th><th></th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><?= e($r['nombre']) ?></td><td><?= e($r['prefijo']) ?></td><td><?= $r['restringido'] ? (int)$r['restringido'] . ' oficina(s)' : 'Todas las oficinas' ?></td><td><?= $r['activo'] ? 'Activo' : 'Inactivo' ?></td><td><a class="btn sm" href="<?= url('admin/tipo', ['id' => $r['id']]) ?>">Editar</a></td></tr><?php endforeach; ?></tbody></table>
