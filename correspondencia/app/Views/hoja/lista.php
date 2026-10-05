<label>Filtrar: <input type="search" data-filtro="tbody tr"></label>
<table class="t"><thead><tr><th>Hoja de ruta</th><th>Documentos</th><th>Referencia</th><th>Fecha</th><th>Acciones</th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><a href="<?= url('seguimiento/ver', ['id' => $r['id']]) ?>"><?= e($r['nur']) ?></a></td><td><?= e($r['cites']) ?></td><td><?= e($r['referencia']) ?></td><td><?= e(fecha_corta($r['creado_en'])) ?></td>
  <td class="acciones"><a class="btn sm" href="<?= url('hoja/derivar', ['id' => $r['id']]) ?>"><?= $r['derivadas'] ? 'Derivada' : 'Derivar' ?></a>
    <a class="btn sm" href="<?= url('documento/index', ['hoja' => $r['id']]) ?>">+ Documento</a>
    <a class="btn sm" href="<?= url('hoja/imprimir', ['id' => $r['id']]) ?>" target="_blank">Imprimir</a></td></tr><?php endforeach; ?>
<?php if (!$rows): ?><tr><td colspan="5" class="vacio">No ha creado hojas de ruta.</td></tr><?php endif; ?></tbody></table>
