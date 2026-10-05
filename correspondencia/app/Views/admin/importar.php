<?php if (!$plan): ?>
<div class="card">
  <p>Suba el archivo Excel con las columnas <b>Ítem</b>, <b>UNIDAD ORGANIZACIONAL</b> y <b>Puesto Organizacional</b>. Se mostrará un resumen para que lo revise <b>antes</b> de crear nada.</p>
  <form method="post" enctype="multipart/form-data" class="form"><?= csrf_field() ?>
    <label>Archivo Excel (.xlsx) o CSV<input type="file" name="archivo" accept=".xlsx,.csv" required></label>
    <button class="btn primary">Subir y revisar</button></form>
  <p class="muted">Se creará una oficina por cada unidad y un usuario por cada cargo, con el nombre «Por asignar» y una clave temporal. Si repite la importación, no se duplican los datos.</p>
</div>
<?php else: $nuevasO = array_filter($plan['oficinas'], fn($o) => !$o['existe']); $nuevosU = array_filter($plan['usuarios'], fn($u) => !$u['existe']); ?>
<div class="flash ok">Revise este resumen. Todavía no se ha creado nada.</div>
<p><b><?= count($nuevasO) ?></b> oficina(s) nueva(s) · <b><?= count($nuevosU) ?></b> usuario(s) nuevo(s) · <?= count($plan['usuarios']) - count($nuevosU) ?> ya existente(s) (se omiten).</p>
<?php foreach ($plan['avisos'] as $a): ?><div class="flash warn">⚠ <?= e($a) ?></div><?php endforeach; ?>
<h3>Oficinas</h3>
<table class="t"><thead><tr><th>Nombre</th><th>Sigla (para el CITE)</th><th>Estado</th></tr></thead><tbody>
<?php foreach ($plan['oficinas'] as $o): ?><tr><td><?= e($o['nombre']) ?></td><td><?= e($o['sigla']) ?></td><td><?= $o['existe'] ? 'Ya existe' : 'Se creará' ?></td></tr><?php endforeach; ?></tbody></table>
<h3>Usuarios (uno por cargo)</h3>
<table class="t"><thead><tr><th>Ítem</th><th>Usuario</th><th>Oficina</th><th>Cargo</th><th>Rol</th><th>Depende de</th><th></th></tr></thead><tbody>
<?php foreach ($plan['usuarios'] as $u): ?><tr><td><?= e($u['item']) ?></td><td><code><?= e($u['login']) ?></code></td><td><?= e($u['unidad']) ?></td><td><?= e($u['cargo']) ?></td><td><?= e($u['rol']) ?></td><td><?= e($u['jefe'] ?? '—') ?></td><td><?= $u['existe'] ? 'ya existe' : '' ?></td></tr><?php endforeach; ?></tbody></table>
<form method="post" action="<?= url('admin/importar_confirmar') ?>"><?= csrf_field() ?>
  <button class="btn primary" data-confirm="¿Crear las oficinas y usuarios mostrados?">Confirmar e importar</button>
  <button class="btn" name="cancelar" value="1">Cancelar</button></form>
<?php endif; ?>
