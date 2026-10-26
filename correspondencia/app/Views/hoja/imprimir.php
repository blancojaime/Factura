<?php
use App\Services\{Ajustes, TextoQr};
$externa = $hoja['origen'] === 'externo';
$logo = Ajustes::logoUrl(); $entidad = Ajustes::entidad(); $superior = Ajustes::superior();
$cite = $doc['cite'] ?? '—';
$fechaDoc = strtotime($doc['creado_en'] ?? $hoja['creado_en']);
$remitente = $externa ? [$hoja['ext_remitente'], $hoja['ext_institucion']] : [$doc['remitente_nombre'] ?? '', $doc['remitente_cargo'] ?? ''];
$procedencia = $externa ? ($hoja['ext_institucion'] ?: $hoja['ext_remitente']) : ($doc['oficina'] ?? '');
$etiquetas = ['ATENCIÓN URGENTE', 'ELABORAR INFORME', 'ELABORAR RESPUESTA', 'PARA SU CONSIDERACIÓN', 'PARA SU CONOCIMIENTO', 'PARA VoBo', 'ARCHIVAR', 'OTRO'];
$mapa = ['elaborar informe' => 1, 'elaborar respuesta' => 2, 'para su consideración' => 3, 'para su conocimiento' => 4, 'para vobo' => 5, 'archivar' => 6];
$marcadas = function (?array $s) use ($mapa): array {
    if (!$s) return [];
    $m = [$mapa[mb_strtolower($s['accion'])] ?? 7];
    if ($s['urgente']) $m[] = 0;
    return $m;
};
$bloque = function (?array $s, bool $sello = false) use ($etiquetas, $marcadas) { $on = $marcadas($s); ?>
  <div class="hr-bloque">
    <div class="hr-fila"><div class="hr-a"><span>A:</span><b><?= $s ? e($s['a_nombre'] . ' — ' . $s['a_cargo']) . ($s['tipo'] === 'copia' ? ' (COPIA)' : '') : '' ?></b><?= $s ? '<small>' . e($s['a_oficina']) . '</small>' : '' ?></div>
      <div class="hr-fecha"><span>FECHA:</span><b><?= $s ? e(date('d/m/Y', strtotime($s['fecha_envio']))) : '' ?></b></div></div>
    <div class="hr-acc"><?php foreach ($etiquetas as $i => $t): ?><div><span><?= e($t) ?></span><i><?= in_array($i, $on, true) ? '✕' : '' ?></i></div><?php endforeach; ?></div>
    <div class="hr-cuerpo"><?php if ($s): ?><p><?= nl2br(e($s['proveido'])) ?></p><?php endif; ?>
      <?php if ($sello): ?><div class="hr-sello"><b>RECIBIDO</b><div><span>Fojas</span><span>Nº Reg.</span><span>Hora ingreso</span><span>Hoja de Ruta</span></div></div><?php endif; ?></div>
    <div class="hr-pie"><div class="hr-adj"><span>Adjunto:</span><?= $s ? e($s['adjunto_txt']) : '' ?></div><div class="hr-hora"><span>Hora:</span><b><?= $s ? e(date('H:i', strtotime($s['fecha_envio']))) : '' ?></b></div></div>
  </div>
<?php };
$idx = 0; ?>
<div class="noprint hr-barra">
  <form method="get" action="<?= url() ?>"><input type="hidden" name="r" value="hoja/imprimir"><input type="hidden" name="id" value="<?= (int)$hoja['id'] ?>">
    <button type="button" class="btn primary" data-print>Imprimir (Carta vertical)</button>
    <label>Contenido <select name="modo"><option value="registrado" <?= $modo === 'registrado' ? 'selected' : '' ?>>Con derivaciones registradas</option><option value="blanco" <?= $modo === 'blanco' ? 'selected' : '' ?>>En blanco (llenado manual)</option></select></label>
    <label>Hojas anexas <input type="number" name="anexas" min="0" max="20" value="<?= (int)$solicitadas ?>" style="width:70px"></label>
    <button class="btn">Actualizar vista</button>
    <span class="muted">Páginas: <?= 1 + (int)$anexas ?><?= $anexas > $solicitadas ? ' (se agregaron anexas para las derivaciones registradas)' : '' ?></span>
    <a class="btn" href="<?= url('hoja/blanco') ?>">Otro trámite</a></form>
</div>

<section class="pagina hr-pagina">
  <header class="hr-cab">
    <div class="hr-logo"><?php if ($logo): ?><img src="<?= e($logo) ?>" alt="Logo"><?php endif; ?></div>
    <div class="hr-ent"><?php if ($superior): ?><small><?= e($superior) ?></small><?php endif; ?><b><?= e(mb_strtoupper($entidad)) ?></b></div>
    <div class="hr-qr" data-qr="<?= e(TextoQr::hojaRuta($hoja, $doc)) ?>" aria-label="Código QR de la hoja de ruta"></div>
    <div class="hr-titulo"><span>HOJA DE RUTA <?= $externa ? 'EXTERNA' : 'INTERNA' ?></span><strong><?= e($hoja['nur']) ?></strong></div>
  </header>
  <div class="hr-datos">
    <div class="hr-g1">
      <div class="hr-c"><span>PROCEDENCIA:</span><b><?= e($procedencia) ?></b></div>
      <div class="hr-cite"><span>CITE ORIGINAL</span><b><?= e($cite) ?></b><div><span>FECHA:</span> <?= e(date('d/m/Y', $fechaDoc)) ?></div><div><span>HORA:</span> <?= e(date('H:i:s', $fechaDoc)) ?></div></div>
      <div class="hr-c"><span>REMITENTE:</span><b><?= e($remitente[0]) ?></b><em><?= e($remitente[1]) ?></em></div>
      <div class="hr-c"><span>DESTINATARIO:</span><b><?= e($doc['destinatario_nombre'] ?? '') ?></b><em><?= e($doc['destinatario_cargo'] ?? '') ?></em></div>
    </div>
    <div class="hr-c hr-ref"><span>REFERENCIA:</span><b><?= e($doc['referencia'] ?? $hoja['referencia']) ?></b></div>
    <div class="hr-g3"><div class="hr-c"><span>PROCESO:</span><b><?= e($doc['tipo'] ?? '') ?></b></div><div class="hr-c"><span>ADJUNTO:</span><b><?= e($doc['adjunto_txt'] ?? '') ?></b></div><div class="hr-c"><span>HOJAS:</span><b><?= e($hoja['ext_fojas'] ?: '0') ?></b></div></div>
  </div>
  <div class="hr-bloques"><?php for ($i = 0; $i < 3; $i++) $bloque($seg[$idx++] ?? null, $i === 0); ?></div>
</section>
<?php for ($a = 1; $a <= (int)$anexas; $a++): ?>
<section class="pagina hr-pagina">
  <div class="hr-anexa-cab"><div>CITE: <?= e($cite) ?></div><div class="hr-anexa-n">Anexa <?= $a ?> de <?= (int)$anexas ?></div><div class="hr-nur"><?= e($hoja['nur']) ?></div></div>
  <div class="hr-bloques"><?php for ($i = 0; $i < 4; $i++) $bloque($seg[$idx++] ?? null); ?></div>
</section>
<?php endfor; ?>
