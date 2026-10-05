<?php
declare(strict_types=1);
require dirname(__DIR__) . '/app/bootstrap.php';

if (is_file(ROOT . '/storage/installed.lock') || App\Core\Config::installed()) {
    http_response_code(403);
    exit('El sistema ya está instalado. Elimine public/install.php por seguridad.');
}
$err = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $p = fn($k) => trim((string)($_POST[$k] ?? ''));
        if (strlen($p('adm_pass')) < 8) throw new RuntimeException('La contraseña del administrador debe tener al menos 8 caracteres.');
        if (!preg_match('/^[A-Za-z0-9_.-]{3,60}$/', $p('adm_login'))) throw new RuntimeException('Usuario administrador inválido.');
        App\Installer::instalar(
            ['host' => $p('host') ?: 'localhost', 'port' => 3306, 'name' => $p('dbname'), 'user' => $p('dbuser'), 'pass' => (string)($_POST['dbpass'] ?? '')],
            $p('entidad'), strtoupper($p('sigla')),
            ['login' => $p('adm_login'), 'nombre' => $p('adm_nombre') ?: 'Administrador', 'password' => (string)$_POST['adm_pass']]
        );
        header('Location: index.php');
        exit;
    } catch (Throwable $e) {
        $err = $e->getMessage();
    }
}
?><!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Instalación</title><link rel="stylesheet" href="assets/css/app.css"></head><body class="simple">
<main class="card narrow"><h1>Instalación del sistema de correspondencia</h1>
<p class="muted">Cree primero una base de datos vacía (utf8mb4) en su hosting.</p>
<?php if ($err): ?><div class="flash error"><?= e($err) ?></div><?php endif; ?>
<form method="post" class="form">
<h3>Base de datos</h3>
<label>Servidor<input name="host" value="localhost"></label>
<label>Nombre de la base<input name="dbname" required></label>
<label>Usuario<input name="dbuser" required></label>
<label>Contraseña<input name="dbpass" type="password"></label>
<h3>Entidad</h3>
<label>Nombre (ej. Gobierno Autónomo Municipal de …)<input name="entidad" required></label>
<label>Sigla (ej. GAMX)<input name="sigla" required maxlength="12"></label>
<h3>Administrador</h3>
<label>Nombre completo<input name="adm_nombre"></label>
<label>Usuario<input name="adm_login" required></label>
<label>Contraseña (mín. 8)<input name="adm_pass" type="password" required minlength="8"></label>
<button class="btn primary">Instalar</button>
</form></main></body></html>
