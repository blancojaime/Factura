<?php
declare(strict_types=1);
namespace App\Core;

final class Auth
{
    private static ?array $user = null;
    private const IDLE = 7200;

    public static function start(): void
    {
        if (session_status() === PHP_SESSION_ACTIVE) return;
        $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
        session_name('corrsid');
        session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => $https, 'httponly' => true, 'samesite' => 'Lax']);
        ini_set('session.use_strict_mode', '1');
        session_start();
        if (isset($_SESSION['t']) && time() - $_SESSION['t'] > self::IDLE) {
            $_SESSION = [];
            session_regenerate_id(true);
        }
        $_SESSION['t'] = time();
    }

    public static function user(): ?array
    {
        if (self::$user !== null) return self::$user;
        $id = $_SESSION['uid'] ?? null;
        if (!$id) return null;
        $u = DB::one('SELECT u.*, o.nombre AS oficina, o.sigla AS oficina_sigla FROM usuarios u JOIN oficinas o ON o.id=u.oficina_id WHERE u.id=? AND u.activo=1', [$id]);
        if (!$u) { unset($_SESSION['uid']); return null; }
        return self::$user = $u;
    }

    public static function id(): int { return (int)(self::user()['id'] ?? 0); }

    public static function es(string ...$roles): bool
    {
        $u = self::user();
        return $u !== null && in_array($u['rol'], $roles, true);
    }

    public static function esJefe(): bool
    {
        return self::es('admin', 'jefe') || (bool)DB::val('SELECT 1 FROM usuarios WHERE jefe_id=? AND activo=1 LIMIT 1', [self::id()]);
    }

    /** Devuelve null si ok o un mensaje de error. */
    public static function login(string $login, string $pass): ?string
    {
        $ip = $_SERVER['REMOTE_ADDR'] ?? '';
        $desde = date('Y-m-d H:i:s', time() - 900);
        $fallos = (int)DB::val('SELECT COUNT(*) FROM intentos_login WHERE ok=0 AND fecha>=? AND (login=? OR ip=?)', [$desde, $login, $ip]);
        if ($fallos >= 8) return 'Demasiados intentos fallidos. Espere 15 minutos.';
        $u = DB::one('SELECT * FROM usuarios WHERE login=? AND activo=1', [$login]);
        $ok = $u && password_verify($pass, $u['password_hash']);
        DB::insert('intentos_login', ['login' => mb_substr($login, 0, 60), 'ip' => $ip, 'ok' => $ok ? 1 : 0, 'fecha' => ahora()]);
        if (!$ok) return 'Usuario o contraseña incorrectos.';
        if (password_needs_rehash($u['password_hash'], PASSWORD_DEFAULT)) {
            DB::update('usuarios', (int)$u['id'], ['password_hash' => password_hash($pass, PASSWORD_DEFAULT)]);
        }
        session_regenerate_id(true);
        $_SESSION['uid'] = (int)$u['id'];
        DB::update('usuarios', (int)$u['id'], ['ultimo_ingreso' => ahora(), 'nro_ingresos' => (int)$u['nro_ingresos'] + 1]);
        Audit::log('login', 'usuario', (int)$u['id']);
        return null;
    }

    public static function logout(): void
    {
        $_SESSION = [];
        session_regenerate_id(true);
        self::$user = null;
    }

    public static function resetCache(): void { self::$user = null; }
}
