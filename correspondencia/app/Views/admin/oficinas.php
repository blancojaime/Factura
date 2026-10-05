<p><a class="btn primary" href="<?= url('admin/oficina') ?>">+ Nueva oficina</a></p>
<table class="t"><thead><tr><th>Nombre</th><th>Sigla</th><th>Depende de</th><th>Usuarios</th><th>Estado</th><th></th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><?= e($r['nombre']) ?></td><td><?= e($r['sigla']) ?></td><td><?= e($r['padre']) ?></td><td><?= (int)$r['n'] ?></td><td><?= $r['activa'] ? 'Activa' : 'Inactiva' ?></td><td><a class="btn sm" href="<?= url('admin/oficina', ['id' => $r['id']]) ?>">Editar</a></td></tr><?php endforeach; ?></tbody></table>
