<?php
declare(strict_types=1);
namespace App;

use App\Core\Config;
use App\Core\DB;

/** Crea tablas, datos iniciales y archivo de configuración. Usado por public/install.php y bin/install.php. */
final class Installer
{
    public static function instalar(array $db, string $entidad, string $sigla, array $admin, bool $escribirConfig = true): void
    {
        if (!preg_match('/^[A-Za-z0-9_]{1,64}$/', (string)$db['name'])) throw new \RuntimeException('El nombre de la base de datos solo puede tener letras, números y guion bajo.');
        try {
            $srv = DB::connect(array_merge($db, ['name' => '']));
            $srv->exec('CREATE DATABASE IF NOT EXISTS `' . $db['name'] . '` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');
            $pdo = DB::connect($db);
        } catch (\PDOException $e) {
            throw new \RuntimeException('No se pudo conectar a MySQL (' . $e->getMessage() . '). Verifique que MySQL esté iniciado (botón Start en XAMPP), y el usuario y la clave.');
        }
        Config::set(['db' => $db, 'entidad' => $entidad, 'entidad_sigla' => $sigla]);
        DB::reset();
        foreach (array_filter(array_map('trim', explode(';', file_get_contents(ROOT . '/database/schema.sql')))) as $sql) {
            $pdo->exec($sql);
        }
        DB::reset();
        if ((int)DB::val('SELECT COUNT(*) FROM usuarios') > 0) throw new \RuntimeException('La base de datos ya tiene usuarios; instalación cancelada.');
        DB::tx(function () use ($entidad, $sigla, $admin) {
            $of = DB::insert('oficinas', ['nombre' => $entidad . ' - Administración del sistema', 'sigla' => 'ADM', 'activa' => 1]);
            DB::insert('oficinas', ['nombre' => 'Ventanilla de Correspondencia', 'sigla' => 'VENT', 'activa' => 1]);
            DB::insert('usuarios', [
                'login' => $admin['login'], 'nombre' => $admin['nombre'], 'cargo' => 'Administrador del sistema', 'mosca' => 'ADM',
                'email' => $admin['email'] ?? '', 'oficina_id' => $of, 'rol' => 'admin',
                'password_hash' => password_hash($admin['password'], PASSWORD_DEFAULT),
            ]);
            $tipos = [['Circular', 'CIR'], ['Memorándum', 'MEM'], ['Informe', 'INF'], ['Nota Interna', 'NI'], ['Carta', 'CAR'],
                ['Instructivo', 'INS'], ['Certificación', 'CER'], ['Resolución Administrativa', 'RA'], ['Informe Legal', 'IL'],
                ['Comunicación Externa', 'EXT'], ['Solicitud', 'SOL']];
            foreach ($tipos as [$n, $p]) DB::insert('tipos_documento', ['nombre' => $n, 'prefijo' => $p, 'activo' => 1]);
        });
        if ($escribirConfig) {
            $cfg = [
                'db' => $db, 'entidad' => $entidad, 'entidad_sigla' => $sigla, 'timezone' => 'America/La_Paz',
                'max_upload_mb' => 10, 'dias_alerta_amarillo' => 3, 'dias_alerta_rojo' => 6, 'debug' => false,
            ];
            $php = "<?php\n// Generado por el instalador. No compartir este archivo.\nreturn " . var_export($cfg, true) . ";\n";
            if (file_put_contents(ROOT . '/config/config.php', $php) === false) throw new \RuntimeException('No se pudo escribir config/config.php (revise permisos).');
            @chmod(ROOT . '/config/config.php', 0640);
            file_put_contents(ROOT . '/storage/installed.lock', ahora());
        }
    }
}
