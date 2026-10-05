<p class="noprint"><button class="btn" data-print>Imprimir carátula</button> <a class="btn" href="<?= url('bandeja/agrupados') ?>">Volver</a></p>
<div class="caratula"><h2>Carátula de agrupación</h2><p><?= e(App\Core\Config::get('entidad')) ?> · <?= e(fecha_corta($g['creada_en'])) ?></p>
<table class="t"><thead><tr><th></th><th>Hoja de ruta</th><th>Documentos</th><th>Referencia</th></tr></thead><tbody>
<?php foreach ($items as $i): ?><tr><td><?= $i['principal'] ? '<b>Principal</b>' : 'Agrupada' ?></td><td><?= e($i['nur']) ?></td><td><?= e($i['cites']) ?></td><td><?= e($i['referencia']) ?></td></tr><?php endforeach; ?></tbody></table></div>
