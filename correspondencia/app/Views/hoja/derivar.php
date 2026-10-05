<p><b>Hoja de ruta:</b> <?= e($hoja['nur']) ?> · <b>Documentos:</b> <?php foreach ($docs as $d): ?><a href="<?= url('documento/ver', ['id' => $d['id']]) ?>" target="_blank"><?= e($d['cite']) ?></a> <?php endforeach; ?></p>
<p><b>Referencia:</b> <?= e($hoja['referencia']) ?></p>
<form method="post" class="form card"><?= csrf_field() ?>
  <label>Derivar a <?= select_usuarios('destino', (int)App\Core\Auth::id(), 'required') ?></label>
  <div class="cols"><label>Acción<select name="accion"><?php foreach (acciones() as $a): ?><option><?= e($a) ?></option><?php endforeach; ?></select></label>
  <label>Adjunto (opcional)<input name="adjunto_txt" maxlength="255" placeholder="Lista de documentos que acompañan"></label></div>
  <label>Proveído (obligatorio)<textarea name="proveido" rows="3" required></textarea></label>
  <label class="radio"><input type="checkbox" name="urgente" value="1"> Urgente</label>
  <p><?php if (!$hayOficial): ?><button class="btn primary" name="tipo" value="oficial">Derivar oficial</button><?php endif; ?>
     <button class="btn" name="tipo" value="copia">Derivar copia</button>
     <a class="btn" href="<?= url('hoja/imprimir', ['id' => $hoja['id']]) ?>" target="_blank">Imprimir hoja de ruta</a></p>
  <?php if ($hayOficial): ?><p class="muted">La derivación oficial solo puede hacerse una vez; puede agregar copias.</p><?php endif; ?>
</form>
<h3>Derivaciones realizadas</h3>
<table class="t"><thead><tr><th>Tipo</th><th>Derivado a</th><th>Acción</th><th>Proveído</th><th>Estado</th><th></th></tr></thead><tbody>
<?php foreach ($enviadas as $x): ?><tr class="<?= $x['tipo'] === 'oficial' ? 'amarillo' : '' ?>"><td><?= $x['tipo'] === 'oficial' ? 'OFICIAL' : 'COPIA' ?><?= $x['urgente'] ? ' ⚑' : '' ?></td><td><b><?= e($x['a_nombre']) ?></b><br><?= e($x['a_cargo']) ?> · <?= e($x['a_oficina']) ?></td><td><?= e($x['accion']) ?></td><td><?= e($x['proveido']) ?></td>
  <td><?= $x['estado'] === 'no_recibido' ? 'Enviado' : 'Recibido' ?></td>
  <td><?php if ($x['estado'] === 'no_recibido'): ?><form method="post" action="<?= url('hoja/quitar') ?>"><?= csrf_field() ?><input type="hidden" name="id" value="<?= (int)$x['id'] ?>"><button class="btn sm" data-confirm="¿Eliminar esta derivación?">Eliminar</button></form><?php endif; ?></td></tr><?php endforeach; ?>
<?php if (!$enviadas): ?><tr><td colspan="6" class="vacio">Aún no hay derivaciones.</td></tr><?php endif; ?></tbody></table>
