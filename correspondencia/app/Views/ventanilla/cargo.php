<?php
use App\Services\{Ajustes, TextoQr};
$logo = Ajustes::logoUrl(); $entidad = Ajustes::entidad(); $superior = Ajustes::superior();
$qr = TextoQr::recepcion($h);
$fecha = strtotime($h['creado_en']);
$url = (!empty($_SERVER['HTTPS']) ? 'https://' : 'http://') . ($_SERVER['HTTP_HOST'] ?? '') . url('consulta/index');
$etiqueta = function () use ($logo, $entidad, $h, $qr, $fecha) { ?>
  <div class="rc-etiq">
    <div class="rc-etiq-logo"><?php if ($logo): ?><img src="<?= e($logo) ?>" alt=""><?php else: ?><b><?= e($entidad) ?></b><?php endif; ?></div>
    <div class="rc-etiq-cod"><?= e($h['nur']) ?></div>
    <div class="rc-etiq-qr" data-qr="<?= e($qr) ?>"></div>
    <div class="rc-etiq-fecha"><?= e(date('d/m/Y H:i:s', $fecha)) ?></div>
  </div>
<?php };
$base = ['id' => $h['id']]; ?>
<div class="noprint hr-barra"><button class="btn primary" data-print>Imprimir (Carta vertical)</button>
  <a class="btn" href="<?= url('ventanilla/cargo', $base) ?>">Cargo + etiquetas</a>
  <a class="btn" href="<?= url('ventanilla/cargo', $base + ['solo' => 'cargo']) ?>">Solo cargo</a>
  <a class="btn" href="<?= url('ventanilla/cargo', $base + ['solo' => 'etiqueta']) ?>">Solo etiquetas</a>
  <a class="btn" href="<?= url('ventanilla/index') ?>">Volver</a></div>
<section class="pagina rc-pagina">
<?php if ($solo !== 'etiqueta'): ?>
  <div class="rc-cargo">
    <header class="rc-cab"><div class="rc-logo"><?php if ($logo): ?><img src="<?= e($logo) ?>" alt="Logo"><?php endif; ?></div>
      <div class="rc-ent"><?php if ($superior): ?><small><?= e($superior) ?></small><?php endif; ?><b><?= e(mb_strtoupper($entidad)) ?></b><h2>CARGO DE RECEPCIÓN DE CORRESPONDENCIA</h2></div></header>
    <div class="rc-cuerpo">
      <table class="rc-datos">
        <tr><th>Código del trámite (NUR)</th><td><b class="rc-nur"><?= e($h['nur']) ?></b></td></tr>
        <tr><th>Fecha y hora de registro</th><td><?= e(date('d/m/Y H:i:s', $fecha)) ?></td></tr>
        <tr><th>Remitente</th><td><?= e($h['ext_remitente']) ?></td></tr>
        <?php if ($h['ext_institucion']): ?><tr><th>Institución / OTB</th><td><?= e($h['ext_institucion']) ?></td></tr><?php endif; ?>
        <tr><th>Tipo de entrada</th><td><?= e($h['ext_documento']) ?></td></tr>
        <tr><th>Fojas · Anexos</th><td><?= e($h['ext_fojas'] ?: '—') ?> fojas · <?= e($h['ext_anexos'] ?: 'sin anexos') ?></td></tr>
        <?php if ($h['ext_celular']): ?><tr><th>Celular de contacto</th><td><?= e($h['ext_celular']) ?></td></tr><?php endif; ?>
        <tr><th>Referencia</th><td><?= e($h['referencia']) ?></td></tr>
        <tr><th>Derivado a</th><td><?= e(($der['nombre'] ?? '') . ' — ' . ($der['cargo'] ?? '')) ?><br><small><?= e($der['oficina'] ?? '') ?></small></td></tr>
        <tr><th>Recibido por</th><td><?= e(($der['registrador'] ?? '') . ' — ' . ($der['registrador_cargo'] ?? '')) ?></td></tr>
      </table>
      <div class="rc-qrbox"><div class="rc-qr" data-qr="<?= e($qr) ?>" aria-label="Código QR de recepción"></div><small>Escanee para ver los datos de recepción</small></div>
    </div>
    <div class="rc-consulta"><b>Consulte el estado de su trámite</b> ingresando a <u><?= e($url) ?></u><br>con el NUR <b><?= e($h['nur']) ?></b> y el código <b class="rc-codigo"><?= e($h['codigo_consulta']) ?></b></div>
    <div class="rc-firmas"><div><span>Firma y sello de ventanilla</span></div><div><span>Firma del interesado (opcional)</span></div></div>
  </div>
<?php endif; ?>
<?php if ($solo === ''): ?><div class="rc-corte">✂ - - - - - - recortar las etiquetas y pegarlas en el documento recibido - - - - - -</div><?php endif; ?>
<?php if ($solo !== 'cargo'): ?><div class="rc-etiquetas"><?php for ($i = 0; $i < $copias; $i++) $etiqueta(); ?></div><?php endif; ?>
</section>
