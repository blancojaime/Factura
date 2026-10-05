<?php
$d = $doc; $tab = $tab ?? 'edicion'; $u = App\Core\Auth::user();
if ($nuevo): ?><p class="muted">Llene correctamente los datos. El NUR y el CITE se asignan automáticamente.</p><?php else: ?>
<p><b>NUR:</b> <?= e($hoja['nur']) ?> · <b>CITE:</b> <?= e($d['cite']) ?>
  · <a href="<?= url('documento/ver', ['id' => $d['id']]) ?>" target="_blank">Ver / imprimir</a> · <a href="<?= url('hoja/derivar', ['id' => $hoja['id']]) ?>">Derivar</a></p>
<div class="tabs"><a href="<?= url('documento/editar', ['id' => $d['id']]) ?>" class="<?= $tab === 'edicion' ? 'on' : '' ?>">Edición</a>
  <a href="<?= url('documento/editar', ['id' => $d['id'], 'tab' => 'adjuntos']) ?>" class="<?= $tab === 'adjuntos' ? 'on' : '' ?>">Adjuntos (<?= count($adjuntos) ?>)</a></div>
<?php endif; ?>
<?php if ($nuevo || $tab === 'edicion'): ?>
<form method="post" class="form doc" data-editor-form><?= csrf_field() ?>
  <?php if ($nuevo): ?><label>Asignar NUR existente (opcional)<input name="nur" list="nurs" data-nur autocomplete="off" value="<?= e($hoja['nur'] ?? '') ?>" <?= $hoja ? 'readonly' : '' ?> placeholder="Deje vacío para generar uno nuevo"><datalist id="nurs"></datalist></label><?php endif; ?>
  <div class="cols">
    <fieldset><legend>Destinatario</legend>
      <label>Seleccionar funcionario <?= select_usuarios('_dest', (int)$u['id'], 'data-fill="destinatario"') ?></label>
      <label>Nombre del destinatario<input name="destinatario_nombre" value="<?= e($d['destinatario_nombre'] ?? '') ?>" required maxlength="150"></label>
      <label>Cargo del destinatario<input name="destinatario_cargo" value="<?= e($d['destinatario_cargo'] ?? '') ?>" maxlength="150"></label>
    </fieldset>
    <fieldset><legend>Vía</legend>
      <label>Seleccionar funcionario <?= select_usuarios('_via', (int)$u['id'], 'data-fill="via"') ?></label>
      <label>Nombre (vía)<input name="via_nombre" value="<?= e($d['via_nombre'] ?? '') ?>" maxlength="150"></label>
      <label>Cargo (vía)<input name="via_cargo" value="<?= e($d['via_cargo'] ?? '') ?>" maxlength="150"></label>
    </fieldset>
  </div>
  <p class="muted"><b>Remitente:</b> <?= e($d['remitente_nombre'] ?? $u['nombre']) ?> — <?= e($d['remitente_cargo'] ?? $u['cargo']) ?></p>
  <div class="cols"><label>Adjunto (descripción)<input name="adjunto_txt" value="<?= e($d['adjunto_txt'] ?? '') ?>" maxlength="255"></label>
  <label>Con copia a<input name="con_copia" value="<?= e($d['con_copia'] ?? '') ?>" maxlength="255"></label></div>
  <label>Referencia<input name="referencia" value="<?= e($d['referencia'] ?? '') ?>" required maxlength="255"></label>
  <label>Contenido<div id="editor"></div><textarea name="contenido" id="contenido" rows="14"><?= e($d['contenido'] ?? '') ?></textarea></label>
  <button class="btn primary"><?= $nuevo ? 'Crear documento' : 'Modificar documento' ?></button>
</form>
<?php else: ?>
<table class="t"><thead><tr><th>Archivo</th><th>Tamaño</th><th>Fecha</th><th></th></tr></thead><tbody>
<?php foreach ($adjuntos as $a): ?><tr><td><a href="<?= url('documento/descargar', ['id' => $a['id']]) ?>"><?= e($a['nombre_original']) ?></a></td><td><?= number_format($a['tamano'] / 1024, 0) ?> KB</td><td><?= e(fecha_corta($a['creado_en'])) ?></td>
  <td><form method="post" action="<?= url('documento/quitar') ?>"><?= csrf_field() ?><input type="hidden" name="id" value="<?= (int)$a['id'] ?>"><button class="btn sm" data-confirm="¿Eliminar este archivo?">Quitar</button></form></td></tr><?php endforeach; ?>
<?php if (!$adjuntos): ?><tr><td colspan="4" class="vacio">Sin adjuntos.</td></tr><?php endif; ?></tbody></table>
<form method="post" action="<?= url('documento/adjuntar') ?>" enctype="multipart/form-data" class="form card"><?= csrf_field() ?><input type="hidden" name="id" value="<?= (int)$d['id'] ?>">
  <label>Subir archivos (PDF, imágenes, Word, Excel…; máx. <?= (int)App\Core\Config::get('max_upload_mb', 10) ?> MB c/u)<input type="file" name="archivos[]" multiple required></label>
  <button class="btn primary">Subir</button></form>
<?php endif; ?>
