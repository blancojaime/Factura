<table class="t"><thead><tr><th>Hoja principal</th><th>Hojas agrupadas</th><th>Fecha</th><th></th></tr></thead><tbody>
<?php foreach ($rows as $r): ?><tr><td><?= e($r['nur_principal']) ?></td><td><?= (int)$r['n'] ?></td><td><?= e(fecha_corta($r['creada_en'])) ?></td><td><a class="btn sm" href="<?= url('bandeja/agrupacion', ['id' => $r['id']]) ?>">Detalle</a></td></tr><?php endforeach; ?>
<?php if (!$rows): ?><tr><td colspan="4" class="vacio">No ha agrupado correspondencia.</td></tr><?php endif; ?></tbody></table>
