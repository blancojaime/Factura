<p><a class="btn primary" href="<?= url('admin/usuario') ?>">+ Nuevo usuario</a></p>
<label>Filtrar: <input type="search" data-filtro="tbody tr"></label>
<table class="t"><thead><tr><th>Usuario</th><th>Nombre / Cargo</th><th>Oficina</th><th>Jefe</th><th>Rol</th><th>Estado</th><th></th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><?= e($r['login']) ?></td><td><b><?= e($r['nombre']) ?></b><br><small><?= e($r['cargo']) ?></small></td><td><?= e($r['oficina']) ?></td><td><?= e($r['jefe']) ?></td><td><?= e($r['rol']) ?></td><td><?= $r['activo'] ? 'Activo' : 'Inactivo' ?></td><td><a class="btn sm" href="<?= url('admin/usuario', ['id' => $r['id']]) ?>">Editar</a></td></tr><?php endforeach; ?></tbody></table>
