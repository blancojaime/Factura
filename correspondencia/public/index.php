<?php
declare(strict_types=1);

require dirname(__DIR__) . '/app/bootstrap.php';

try {
    App\Core\Router::run();
} catch (Throwable $e) {
    error_log((string)$e);
    @file_put_contents(ROOT . '/storage/logs/error.log', '[' . date('c') . '] ' . $e . "\n", FILE_APPEND);
    http_response_code(500);
    $debug = App\Core\Config::get('debug', false);
    echo '<!doctype html><meta charset="utf-8"><title>Error</title><body style="font-family:sans-serif;padding:2rem"><h1>Error del sistema</h1><p>Ocurrió un error inesperado. Contacte al administrador.</p>' . ($debug ? '<pre>' . htmlspecialchars((string)$e) . '</pre>' : '') . '</body>';
}
