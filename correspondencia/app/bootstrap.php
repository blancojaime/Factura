<?php
declare(strict_types=1);

define('ROOT', dirname(__DIR__));

spl_autoload_register(function (string $class): void {
    if (strncmp($class, 'App\\', 4) !== 0) return;
    $file = ROOT . '/app/' . str_replace('\\', '/', substr($class, 4)) . '.php';
    if (is_file($file)) require $file;
});

require __DIR__ . '/helpers.php';
App\Core\Config::load();
date_default_timezone_set(App\Core\Config::get('timezone', 'America/La_Paz'));
mb_internal_encoding('UTF-8');
