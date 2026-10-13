<?php
// Instalación por consola. Dos formas:
//   1) php bin/install.php host base usuario clave "Entidad" SIGLA adminlogin adminpass
//   2) con variables de entorno: CORR_DB_HOST, CORR_DB_PORT, CORR_DB_NAME, CORR_DB_USER, CORR_DB_PASS,
//      CORR_ENTIDAD, CORR_SIGLA, CORR_ADMIN_LOGIN, CORR_ADMIN_PASS, CORR_ADMIN_NOMBRE  (lo usa instalador\instalar.ps1)
require dirname(__DIR__) . '/app/bootstrap.php';

$e = fn($k, $i, $d = '') => getenv($k) !== false && getenv($k) !== '' ? getenv($k) : ($GLOBALS['argv'][$i] ?? $d);
$db = ['host' => $e('CORR_DB_HOST', 1, '127.0.0.1'), 'port' => (int)($e('CORR_DB_PORT', 99, 3306)), 'name' => $e('CORR_DB_NAME', 2), 'user' => $e('CORR_DB_USER', 3), 'pass' => $e('CORR_DB_PASS', 4)];
$entidad = $e('CORR_ENTIDAD', 5); $sigla = $e('CORR_SIGLA', 6);
$admin = ['login' => $e('CORR_ADMIN_LOGIN', 7), 'nombre' => $e('CORR_ADMIN_NOMBRE', 99, 'Administrador'), 'password' => $e('CORR_ADMIN_PASS', 8)];
if ($db['name'] === '' || $db['user'] === '' || $entidad === '' || $sigla === '' || $admin['login'] === '' || strlen($admin['password']) < 8) {
    fwrite(STDERR, "Faltan datos (la clave del administrador debe tener 8 o más caracteres).\nUso: php bin/install.php host base usuario clave \"Entidad\" SIGLA adminlogin adminpass\n");
    exit(1);
}
try {
    App\Installer::instalar($db, $entidad, strtoupper($sigla), $admin, getenv('NO_CONFIG') ? false : true);
} catch (Throwable $ex) {
    fwrite(STDERR, 'Error: ' . $ex->getMessage() . "\n");
    exit(2);
}
echo "Instalación completa.\n";
