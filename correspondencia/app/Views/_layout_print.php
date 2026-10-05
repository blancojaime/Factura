<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title><?= e($titulo ?? 'Impresión') ?></title><link rel="stylesheet" href="<?= asset('css/app.css') ?>"></head>
<body class="print"><?= $contenido ?><script src="<?= asset('js/app.js') ?>" defer></script></body></html>
