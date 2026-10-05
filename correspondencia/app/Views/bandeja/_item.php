<?php
/** Tarjeta de correspondencia. $d fila, $modo: entrada|pendientes|enviados, $tipos (pendientes) */
$cls = $d['tipo'] === 'copia' ? 'copia' : 'oficial';
$sem = $modo === 'pendientes' ? semaforo($d['fecha_recepcion']) : '';
$procedencia = $modo === 'enviados' ? 'Derivado a: ' . $d['a_oficina'] : 'Procedencia: ' . $d['de_oficina'];
$persona = $modo === 'enviados' ? $d['a_nombre'] . ' | ' . $d['a_cargo'] : $d['de_nombre'] . ' | ' . $d['de_cargo'];
?>
<article class="item <?= $cls ?><?= $d['urgente'] ? ' urgente' : '' ?>">
  <input type="checkbox" name="ids[]" value="<?= (int)$d['id'] ?>" aria-label="Seleccionar <?= e($d['nur']) ?>">
  <div class="sello"><span class="tag <?= $cls ?>"><?= $cls === 'copia' ? 'COPIA' : 'OFICIAL' ?></span><?php if ($d['urgente']): ?><span class="tag urg">URGENTE</span><?php endif; ?>
    <a class="nur" href="<?= url('seguimiento/ver', ['id' => $d['hoja_id']]) ?>"><?= e($d['nur']) ?></a></div>
  <div class="cuerpo">
    <?php $primerDoc = $d['primer_doc']; ?>
    <h4><?= $primerDoc ? '<a href="' . url('documento/ver', ['id' => $primerDoc]) . '">' . e($d['referencia']) . '</a>' : e($d['referencia']) ?></h4>
    <p><?= e($procedencia) ?><br><small><?= e($persona) ?><?= $d['cites'] ? ' · ' . e($d['cites']) : '' ?></small><br><small>Acción: <?= e($d['accion'] ?: '—') ?></small></p>
    <div class="acciones">
      <?php if ($modo === 'entrada'): ?><button name="solo" value="<?= (int)$d['id'] ?>" formaction="<?= url('bandeja/recibir') ?>" class="btn sm primary">Recepcionar</button><?php endif; ?>
      <?php if ($modo === 'pendientes'): ?>
        <a class="btn sm" href="<?= url('hoja/derivar', ['id' => $d['hoja_id']]) ?>">Derivar</a>
        <a class="btn sm" href="<?= url('documento/index', ['hoja' => $d['hoja_id']]) ?>">Generar respuesta</a>
      <?php endif; ?>
      <?php if ($modo === 'enviados'): ?>
        <button name="id" value="<?= (int)$d['id'] ?>" formaction="<?= url('bandeja/cancelar') ?>" class="btn sm" data-confirm="¿Cancelar esta derivación? La hoja volverá a sus pendientes.">Cancelar derivación</button>
        <a class="btn sm" href="<?= url('hoja/imprimir', ['id' => $d['hoja_id']]) ?>" target="_blank">Imprimir</a>
      <?php endif; ?>
      <?php if ($d['n_adjuntos'] > 0): ?><span class="muted">📎 <?= (int)$d['n_adjuntos'] ?></span><?php endif; ?>
    </div>
  </div>
  <div class="meta"><?= e(fecha_larga($modo === 'pendientes' ? $d['fecha_recepcion'] : $d['fecha_envio'])) ?><br>
    <small>Proveído: <?= e($d['proveido']) ?></small>
    <?php if ($sem): ?><br><span class="sem <?= $sem ?>"><?= dias_desde($d['fecha_recepcion']) ?> días</span><?php endif; ?></div>
</article>
