<p class="noprint"><button class="btn primary" data-print>Imprimir / Guardar PDF</button></p>
<article class="hojaruta">
  <header><h2><?= e(App\Core\Config::get('entidad')) ?></h2><h3>HOJA DE RUTA</h3><p class="nur"><?= e($hoja['nur']) ?></p></header>
  <p><b>Referencia:</b> <?= e($hoja['referencia']) ?><br><b>Fecha:</b> <?= e(fecha_larga($hoja['creado_en'])) ?></p>
  <?php foreach ($docs as $d): ?><p><b><?= e($d['tipo']) ?>:</b> <?= e($d['cite']) ?> — De: <?= e($d['remitente_nombre']) ?> A: <?= e($d['destinatario_nombre']) ?></p><?php endforeach; ?>
  <table class="t"><thead><tr><th>Fecha</th><th>De</th><th>Derivado a</th><th>Acción / Proveído</th><th>Recepción</th><th>Firma</th></tr></thead><tbody>
  <?php foreach ($seg as $s): ?><tr><td><?= e(fecha_corta($s['fecha_envio'])) ?></td><td><?= e($s['de_nombre']) ?><br><small><?= e($s['de_cargo']) ?></small></td><td><b><?= e($s['a_nombre']) ?></b><br><small><?= e($s['a_cargo']) ?> · <?= e($s['a_oficina']) ?></small> <?= $s['tipo'] === 'copia' ? '[COPIA]' : '' ?></td><td><?= e($s['accion']) ?><br><small><?= e($s['proveido']) ?></small></td><td><?= e(fecha_corta($s['fecha_recepcion'])) ?></td><td></td></tr><?php endforeach; ?>
  <?php for ($i = 0; $i < 3; $i++): ?><tr class="blanco"><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td></tr><?php endfor; ?></tbody></table>
</article>
