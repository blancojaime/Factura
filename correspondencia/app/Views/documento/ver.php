<p class="noprint"><button class="btn primary" data-print>Imprimir / Guardar PDF</button>
  <a class="btn" href="<?= e($volver ?: url('seguimiento/ver', ['id' => $d['hoja_id']])) ?>" onclick="if(history.length>1){history.back();return false}">Volver</a></p>
<article class="memo">
  <header><h2><?= e(App\Core\Config::get('entidad')) ?></h2><h3><?= e(mb_strtoupper($d['tipo'])) ?></h3><p><b><?= e($d['cite']) ?></b><br>NUR: <?= e($d['nur']) ?></p></header>
  <table class="datos">
    <tr><th>A:</th><td><b><?= e($d['destinatario_nombre']) ?></b><br><?= e($d['destinatario_cargo']) ?></td></tr>
    <?php if ($d['via_nombre']): ?><tr><th>VÍA:</th><td><b><?= e($d['via_nombre']) ?></b><br><?= e($d['via_cargo']) ?></td></tr><?php endif; ?>
    <tr><th>DE:</th><td><b><?= e($d['remitente_nombre']) ?></b><br><?= e($d['remitente_cargo']) ?></td></tr>
    <tr><th>FECHA:</th><td><?= e(fecha_larga($d['creado_en'])) ?></td></tr>
    <tr><th>REF.:</th><td><b><?= e($d['referencia']) ?></b></td></tr>
    <?php if ($d['adjunto_txt']): ?><tr><th>ADJUNTO:</th><td><?= e($d['adjunto_txt']) ?></td></tr><?php endif; ?>
  </table>
  <div class="contenido ql-editor"><?= $d['contenido'] /* saneado al guardar */ ?></div>
  <?php if ($d['con_copia']): ?><p><small>Cc.: <?= e($d['con_copia']) ?></small></p><?php endif; ?>
  <p class="mosca"><small><?= e($d['mosca']) ?></small></p>
</article>
<?php if ($adjuntos): ?><section class="noprint"><h4>Archivos adjuntos</h4><ul><?php foreach ($adjuntos as $a): ?><li><a href="<?= url('documento/descargar', ['id' => $a['id']]) ?>"><?= e($a['nombre_original']) ?></a></li><?php endforeach; ?></ul></section><?php endif; ?>
