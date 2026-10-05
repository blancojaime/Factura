<?php
$page = [];
$i = 0;
foreach ($rows as $r) { $page[intdiv($pos - 1 + $i, 6)][($pos - 1 + $i) % 6 + 1] = $r; $i++; }
?>
<p class="noprint"><button class="btn primary" data-print>Imprimir</button> <button class="btn" onclick="window.close()">Cerrar</button></p>
<?php foreach ($page as $slotsPag): ?><section class="hoja-a4">
  <?php for ($s = 1; $s <= 6; $s++): $r = $slotsPag[$s] ?? null; ?><div class="slot"><?php if ($r): ?>
    <b><?= e($r['nur']) ?></b> · <?= e(fecha_corta($r['fecha_envio'])) ?><br>Proveído: <?= e($r['proveido']) ?><br>Derivado a: <b><?= e($r['a_nombre']) ?></b> — <?= e($r['a_cargo']) ?> (<?= e($r['a_oficina']) ?>)<?= $r['tipo'] === 'copia' ? ' [COPIA]' : '' ?>
    <div class="firma">Recibí conforme: __________________ Fecha: ____________</div><?php endif; ?></div><?php endfor; ?></section><?php endforeach; ?>
