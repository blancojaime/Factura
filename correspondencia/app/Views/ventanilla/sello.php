<?php
use App\Services\{Ajustes, TextoQr};
$logo = Ajustes::logoUrl(); $entidad = Ajustes::entidad(); $qr = TextoQr::recepcion($h);
$fecha = date('d/m/Y H:i:s', strtotime($h['creado_en']));
$tamanos = ['p' => 'Pequeño (34 mm)', 'm' => 'Mediano (44 mm)', 'g' => 'Grande (56 mm)'];
$sello = function (string $p) use ($logo, $entidad, $h, $qr, $fecha, $dx, $dy) { ?>
  <div class="sello-q pos-<?= e($p) ?>" style="--dx:<?= (int)$dx ?>mm;--dy:<?= (int)$dy ?>mm">
    <div class="sq-esc"><?php if ($logo): ?><img src="<?= e($logo) ?>" alt="Escudo"><?php else: ?><b><?= e($entidad) ?></b><?php endif; ?></div>
    <div class="sq-nur"><?= e($h['nur']) ?></div>
    <div class="sq-qr" data-qr="<?= e($qr) ?>"></div>
    <div class="sq-fecha"><?= e($fecha) ?></div>
  </div>
<?php }; ?>
<div class="noprint sello-barra">
  <form method="get" action="<?= url() ?>" id="fsello"><input type="hidden" name="r" value="ventanilla/sello"><input type="hidden" name="id" value="<?= (int)$h['id'] ?>"><input type="hidden" name="f" value="1">
    <div class="sb-titulo"><b>Sello de recepción con QR y escudo</b><span>Coloque en la impresora la <u>copia de la nota de presentación</u> y marque dónde hay espacio libre para el sello.</span></div>
    <fieldset class="sb-pos"><legend>Posición en la hoja (puede marcar más de una)</legend>
      <?php foreach ($validas as $k => $t): ?><label class="sb-chk"><input type="checkbox" name="pos[]" value="<?= $k ?>" <?= in_array($k, $pos, true) ? 'checked' : '' ?> onchange="this.form.submit()"> <?= e($t) ?></label><?php endforeach; ?></fieldset>
    <label>Tamaño <select name="tam" onchange="this.form.submit()"><?php foreach ($tamanos as $k => $t): ?><option value="<?= $k ?>" <?= $tam === $k ? 'selected' : '' ?>><?= e($t) ?></option><?php endforeach; ?></select></label>
    <label>Ajuste horizontal (mm) <input type="number" name="dx" min="-30" max="30" value="<?= (int)$dx ?>" style="width:70px"></label>
    <label>Ajuste vertical (mm) <input type="number" name="dy" min="-30" max="30" value="<?= (int)$dy ?>" style="width:70px"></label>
    <button class="btn">Actualizar vista</button>
    <button type="button" class="btn primary" onclick="window.print()">Imprimir sello (Carta vertical)</button>
    <a class="btn" href="<?= url('ventanilla/cargo', ['id' => $h['id']]) ?>">Volver al cargo</a>
  </form>
  <p class="muted">Se imprime <b>solo el sello</b> en las posiciones marcadas; el resto de la hoja queda en blanco para no tapar el texto de la copia. Si el sello sale desplazado, corrija con los ajustes en milímetros.</p>
</div>
<section class="pagina sello-hoja tam-<?= e($tam) ?>">
  <div class="sello-guia noprint">Vista previa de la hoja Carta (las líneas tenues no se imprimen)</div>
  <?php foreach ($pos as $p) $sello($p); ?>
</section>
