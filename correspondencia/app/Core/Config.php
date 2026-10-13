<?php
declare(strict_types=1);
namespace App\Core;

final class Config
{
    private static array $c = [];

    public static function load(): void
    {
        $f = self::archivo();
        self::$c = is_file($f) ? (require $f) : [];
    }

    /** Ruta del archivo de configuración (CORR_CONFIG permite varias instalaciones de prueba). */
    public static function archivo(): string { return getenv('CORR_CONFIG') ?: ROOT . '/config/config.php'; }

    public static function lockFile(): string { return getenv('CORR_CONFIG') ? getenv('CORR_CONFIG') . '.lock' : ROOT . '/storage/installed.lock'; }

    public static function installed(): bool { return self::$c !== []; }

    public static function get(string $k, $default = null)
    {
        $v = self::$c;
        foreach (explode('.', $k) as $p) {
            if (!is_array($v) || !array_key_exists($p, $v)) return $default;
            $v = $v[$p];
        }
        return $v;
    }

    public static function set(array $c): void { self::$c = $c; }
}
