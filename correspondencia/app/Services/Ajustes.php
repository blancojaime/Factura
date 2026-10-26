<?php
declare(strict_types=1);
namespace App\Services;

use App\Core\{Config, DB};

/** Datos configurables de la entidad (nombre oficial, entidad superior, logo). */
final class Ajustes
{
    private static ?array $cache = null;

    private static function todos(): array
    {
        if (self::$cache === null) {
            self::$cache = [];
            try {
                foreach (DB::all('SELECT clave, valor FROM ajustes') as $r) self::$cache[$r['clave']] = (string)$r['valor'];
            } catch (\Throwable $e) { /* tabla aún no migrada */ }
        }
        return self::$cache;
    }

    public static function get(string $k, string $d = ''): string
    {
        $v = self::todos()[$k] ?? '';
        return $v !== '' ? $v : $d;
    }

    public static function set(string $k, string $v): void
    {
        DB::q('INSERT INTO ajustes (clave, valor) VALUES (?, ?) ON DUPLICATE KEY UPDATE valor=VALUES(valor)', [$k, $v]);
        self::$cache = null;
    }

    public static function entidad(): string { return self::get('entidad_nombre', (string)Config::get('entidad', '')); }

    public static function superior(): string { return self::get('entidad_superior'); }

    public static function logoPath(): ?string
    {
        $f = self::get('logo');
        $p = $f !== '' ? ROOT . '/storage/uploads/entidad/' . basename($f) : '';
        return $p !== '' && is_file($p) ? $p : null;
    }

    public static function logoUrl(): ?string
    {
        return self::logoPath() ? url('entidad/logo', ['v' => substr(md5((string)filemtime(self::logoPath())), 0, 6)]) : null;
    }
}
