<?php if (!$cred): ?><p class="vacio">No hay una lista de claves pendiente.</p><?php else: ?>
<div class="flash warn"><b>Importante:</b> esta lista se muestra una sola vez. Imprímala o descárguela y entregue a cada persona su clave en privado. Al ingresar por primera vez el sistema le pedirá cambiarla.</div>
<p class="noprint"><button class="btn primary" data-print>Imprimir</button> <a class="btn" href="<?= url('admin/credenciales', ['csv' => 1]) ?>">Descargar en Excel (CSV)</a>
 <form method="post" action="<?= url('admin/credenciales_cerrar') ?>" style="display:inline"><?= csrf_field() ?><button class="btn" data-confirm="¿Ya guardó la lista? Se borrará del servidor.">Ya la guardé, borrar del servidor</button></form></p>
<table class="t"><thead><tr><th>Oficina</th><th>Cargo</th><th>Usuario</th><th>Clave temporal</th></tr></thead><tbody>
<?php foreach ($cred as $c): ?><tr><td><?= e($c['oficina']) ?></td><td><?= e($c['cargo']) ?></td><td><code><?= e($c['login']) ?></code></td><td><code><?= e($c['clave']) ?></code></td></tr><?php endforeach; ?></tbody></table>
<?php endif; ?>
