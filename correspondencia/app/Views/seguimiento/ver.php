<p class="noprint"><a class="btn sm" href="<?= url('hoja/imprimir', ['id' => $hoja['id']]) ?>" target="_blank">Imprimir hoja de ruta</a></p>
<section class="card"><p><b>Hoja de ruta:</b> <?= e($hoja['nur']) ?><?= $hoja['origen'] === 'externo' ? ' <span class="tag">EXTERNA</span>' : '' ?><br><b>Referencia:</b> <?= e($hoja['referencia']) ?><br><b>Creada:</b> <?= e(fecha_larga($hoja['creado_en'])) ?></p>
<?php if ($hoja['origen'] === 'externo'): ?><p><b>Remitente externo:</b> <?= e($hoja['ext_remitente']) ?> <?= $hoja['ext_institucion'] ? '(' . e($hoja['ext_institucion']) . ')' : '' ?></p><?php endif; ?>
<?php foreach ($docs as $d): ?><p><b><?= e($d['tipo']) ?>:</b> <a href="<?= url('documento/ver', ['id' => $d['id']]) ?>"><?= e($d['cite']) ?></a> · De: <?= e($d['remitente_nombre']) ?> → <?= e($d['destinatario_nombre']) ?></p><?php endforeach; ?>
<?php if ($adjuntos): ?><p><b>Adjuntos:</b> <?php foreach ($adjuntos as $a): ?><a href="<?= url('documento/descargar', ['id' => $a['id']]) ?>">📎 <?= e($a['nombre_original']) ?></a> <?php endforeach; ?></p><?php endif; ?></section>
<h3>Seguimiento</h3>
<?php foreach ($seg as $s): $actual = in_array($s['estado'], ['no_recibido', 'pendiente'], true); ?>
<div class="paso <?= $actual ? 'actual' : '' ?>"><div class="de"><b><?= e($s['de_oficina']) ?></b><br><?= e($s['de_nombre']) ?><br><small><?= e($s['de_cargo']) ?></small></div><div class="flecha">➜</div>
  <div class="a"><b><?= e($s['a_oficina']) ?></b><br><?= e($s['a_nombre']) ?> <?= $s['tipo'] === 'copia' ? '<span class="tag copia">COPIA</span>' : '' ?><br><small><?= e($s['a_cargo']) ?></small></div>
  <div class="det"><b>Acción:</b> <?= e($s['accion']) ?> · <b>Estado:</b> <?= ['no_recibido' => 'No recibido', 'pendiente' => 'Recibido / acción pendiente', 'derivado' => 'Recibido / derivado', 'archivado' => 'Archivado', 'agrupado' => 'Agrupado'][$s['estado']] ?><br>
  <small>Enviado <?= e(fecha_corta($s['fecha_envio'])) ?><?= $s['fecha_recepcion'] ? ' · Recibido ' . e(fecha_corta($s['fecha_recepcion'])) : '' ?></small><br>Proveído: <?= e($s['proveido']) ?></div></div>
<?php endforeach; ?>
<?php if (!$seg): ?><p class="vacio">Aún no se ha derivado esta hoja de ruta.</p><?php endif; ?>
