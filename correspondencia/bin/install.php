<?php
// Uso: php bin/install.php host dbname dbuser dbpass "Entidad" SIGLA adminlogin adminpass
require dirname(__DIR__) . '/app/bootstrap.php';
if ($argc < 9) { fwrite(STDERR, "Uso: php bin/install.php host dbname dbuser dbpass \"Entidad\" SIGLA adminlogin adminpass\n"); exit(1); }
App\Installer::instalar(['host' => $argv[1], 'port' => 3306, 'name' => $argv[2], 'user' => $argv[3], 'pass' => $argv[4]], $argv[5], $argv[6],
    ['login' => $argv[7], 'nombre' => 'Administrador', 'password' => $argv[8]], getenv('NO_CONFIG') ? false : true);
echo "Instalación completa.\n";
