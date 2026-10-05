<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title><?= e($titulo ?? 'Correspondencia') ?></title><link rel="stylesheet" href="<?= asset('css/app.css') ?>"></head>
<body class="simple"><?php foreach (flash() ?? [] as [$tipo, $msg]): ?><div class="flash <?= e($tipo) ?>"><?= e($msg) ?></div><?php endforeach; ?>
<?= $contenido ?></body></html>
