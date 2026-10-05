<p><a class="btn primary" href="<?= url('ventanilla/nueva') ?>">+ Registrar correspondencia externa</a></p>
<label>Filtrar: <input type="search" data-filtro="tbody tr"></label>
<table class="t"><thead><tr><th>NUR</th><th>Remitente</th><th>Referencia</th><th>Fecha</th><th>Código consulta</th><th></th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><a href="<?= url('seguimiento/ver', ['id' => $r['id']]) ?>"><?= e($r['nur']) ?></a></td><td><?= e($r['ext_remitente']) ?><br><small><?= e($r['ext_institucion']) ?></small></td><td><?= e($r['referencia']) ?></td><td><?= e(fecha_corta($r['creado_en'])) ?></td><td><code><?= e($r['codigo_consulta']) ?></code></td><td><a class="btn sm" target="_blank" href="<?= url('ventanilla/cargo', ['id' => $r['id']]) ?>">Cargo</a></td></tr><?php endforeach; ?>
<?php if (!$rows): ?><tr><td colspan="6" class="vacio">Sin registros.</td></tr><?php endif; ?></tbody></table>
