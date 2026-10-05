<p class="noprint"><button class="btn primary" data-print>Imprimir cargo</button> <a class="btn" href="<?= url('ventanilla/index') ?>">Volver</a></p>
<article class="hojaruta"><header><h2><?= e(App\Core\Config::get('entidad')) ?></h2><h3>CARGO DE RECEPCIÓN DE CORRESPONDENCIA</h3><p class="nur"><?= e($h['nur']) ?></p></header>
<p><b>Fecha y hora:</b> <?= e(fecha_corta($h['creado_en'])) ?><br><b>Remitente:</b> <?= e($h['ext_remitente']) ?> <?= $h['ext_institucion'] ? '(' . e($h['ext_institucion']) . ')' : '' ?><br>
<b>Documento:</b> <?= e($h['ext_documento']) ?> — <b>Fojas:</b> <?= e($h['ext_fojas']) ?><br><b>Referencia:</b> <?= e($h['referencia']) ?><br>
<b>Derivado a:</b> <?= e($der['nombre'] ?? '') ?> — <?= e($der['cargo'] ?? '') ?> (<?= e($der['oficina'] ?? '') ?>)</p>
<div class="consulta-box"><p><b>Consulte el estado de su trámite:</b><br>Ingrese a <u><?= e((!empty($_SERVER['HTTPS']) ? 'https://' : 'http://') . ($_SERVER['HTTP_HOST'] ?? '') . url('consulta/index')) ?></u><br>
NUR: <b><?= e($h['nur']) ?></b> &nbsp; Código: <b class="codigo"><?= e($h['codigo_consulta']) ?></b></p></div>
<p class="firma">Recibido por: ______________________ &nbsp;&nbsp; Sello</p></article>
