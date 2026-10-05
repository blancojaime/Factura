<label>Filtrar: <input type="search" data-filtro="tbody tr"></label>
<table class="t"><thead><tr><th>Archivo</th><th>Tamaño</th><th>Documento</th><th>Referencia</th><th>Hoja de ruta</th><th>Fecha</th></tr></thead><tbody>
<?php foreach ($rows as $a): ?><tr><td><a href="<?= url('documento/descargar', ['id' => $a['id']]) ?>"><?= e($a['nombre_original']) ?></a></td><td><?= number_format($a['tamano'] / 1024, 0) ?> KB</td><td><?= e($a['cite']) ?></td><td><?= e($a['referencia']) ?></td><td><?= e($a['nur']) ?></td><td><?= e(fecha_corta($a['creado_en'])) ?></td></tr><?php endforeach; ?>
<?php if (!$rows): ?><tr><td colspan="6" class="vacio">No ha subido archivos.</td></tr><?php endif; ?></tbody></table>
