<form method="get" class="form card"><input type="hidden" name="r" value="busqueda/index"><input type="hidden" name="avanzada" value="1">
  <label>Texto a buscar (parte del NUR, CITE o referencia)<input name="q" value="<?= e($q) ?>" autofocus></label>
  <div class="chips"><?php foreach (['hoja' => 'Hoja de ruta', 'cite' => 'Cite documento', 'destinatario' => 'Destinatario', 'remitente' => 'Remitente', 'referencia' => 'Referencia'] as $k => $t): ?>
    <label><input type="checkbox" name="campos[]" value="<?= $k ?>" <?= in_array($k, $campos, true) ? 'checked' : '' ?>> <?= $t ?></label><?php endforeach; ?></div>
  <button class="btn primary">Buscar</button></form>
<?php if ($rows !== null): ?>
  <p class="muted"><?= count($rows) ?> resultado(s) para «<?= e($q) ?>». Se muestran solo documentos de su oficina o en los que participó.</p>
  <?php if (!$rows): ?><div class="flash warn">¡Lo sentimos! Ningún proceso encontrado. Pruebe la búsqueda avanzada marcando otros campos.</div><?php endif; ?>
  <?php if ($rows): ?><table class="t"><thead><tr><th>NUR</th><th>Documento</th><th>Tipo</th><th>Destinatario</th><th>Remitente</th><th>Referencia</th><th>Fecha</th><th></th></tr></thead><tbody>
  <?php foreach ($rows as $r): ?><tr><td><a href="<?= url('seguimiento/ver', ['id' => $r['hoja_id']]) ?>"><?= e($r['nur']) ?></a></td><td><?= $r['doc_id'] ? '<a href="' . url('documento/ver', ['id' => $r['doc_id']]) . '">' . e($r['cite']) . '</a>' : '—' ?></td><td><?= e($r['tipo']) ?></td>
    <td><?= e($r['destinatario_nombre']) ?><br><small><?= e($r['destinatario_cargo']) ?></small></td><td><?= e($r['remitente_nombre']) ?><br><small><?= e($r['remitente_cargo']) ?></small></td><td><?= e($r['referencia']) ?></td><td><?= e(fecha_corta($r['creado_en'])) ?></td>
    <td><a class="btn sm" href="<?= url('seguimiento/ver', ['id' => $r['hoja_id']]) ?>">Ver</a></td></tr><?php endforeach; ?></tbody></table><?php endif; ?>
<?php endif; ?>
