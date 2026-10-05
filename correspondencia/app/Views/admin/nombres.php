<?php if (!$rows): ?><p class="vacio">No hay usuarios pendientes de asignar nombre. ✔</p><?php else: ?>
<p class="muted">Escriba el nombre real de cada persona y pulse Guardar. Puede completar solo algunos y volver después; los que deje vacíos quedan «Por asignar».</p>
<form method="post"><?= csrf_field() ?>
<table class="t"><thead><tr><th>Oficina</th><th>Cargo</th><th>Usuario</th><th>Nombre completo</th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><?= e($r['oficina']) ?></td><td><?= e($r['cargo']) ?></td><td><code><?= e($r['login']) ?></code></td><td><input name="nombre[<?= (int)$r['id'] ?>]" maxlength="120" placeholder="Nombre y apellidos"></td></tr><?php endforeach; ?></tbody></table>
<button class="btn primary">Guardar nombres</button></form>
<?php endif; ?>
