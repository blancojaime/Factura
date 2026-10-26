<?php
declare(strict_types=1);
namespace App\Services;

use App\Core\DB;

/** Aplica de forma segura (y repetible) los cambios de base de datos de database/migrations/*.sql. */
final class Migrador
{
    private static function tabla(): void
    {
        DB::q('CREATE TABLE IF NOT EXISTS migraciones (nombre VARCHAR(80) NOT NULL PRIMARY KEY, aplicada_en DATETIME NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4');
    }

    private static function columnaExiste(string $t, string $c): bool
    {
        return (bool)DB::val('SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?', [$t, $c]);
    }

    /** ¿Ya están aplicadas todas las migraciones? (consulta barata, se usa en cada petición) */
    public static function alDia(): bool
    {
        try {
            $n = (int)DB::val('SELECT COUNT(*) FROM migraciones');
        } catch (\Throwable $e) {
            return false;
        }
        return $n >= count(glob(ROOT . '/database/migrations/*.sql') ?: []);
    }

    /** @return list<string> migraciones aplicadas en esta ejecución */
    public static function aplicar(): array
    {
        self::tabla();
        $hechas = [];
        $archivos = glob(ROOT . '/database/migrations/*.sql') ?: [];
        sort($archivos);
        foreach ($archivos as $f) {
            $nombre = basename($f, '.sql');
            if (DB::val('SELECT 1 FROM migraciones WHERE nombre=?', [$nombre])) continue;
            $sql = preg_replace('/^\s*--.*$/m', '', (string)file_get_contents($f));
            foreach (array_filter(array_map('trim', explode(';', $sql))) as $st) {
                // Si la columna ya existe (instalación parcial o antigua), no se repite.
                if (preg_match('/^ALTER TABLE\s+(\w+)\s+ADD COLUMN\s+(\w+)/i', $st, $m) && self::columnaExiste($m[1], $m[2])) continue;
                DB::q($st);
            }
            DB::insert('migraciones', ['nombre' => $nombre, 'aplicada_en' => ahora()]);
            $hechas[] = $nombre;
        }
        return $hechas;
    }

    /** Instalación nueva: el esquema ya incluye todo; se registran como aplicadas. */
    public static function marcarTodas(): void
    {
        self::tabla();
        foreach (glob(ROOT . '/database/migrations/*.sql') ?: [] as $f) {
            DB::q('INSERT IGNORE INTO migraciones (nombre, aplicada_en) VALUES (?, ?)', [basename($f, '.sql'), ahora()]);
        }
    }
}
