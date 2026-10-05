<?php
declare(strict_types=1);
namespace App\Core;

final class Audit
{
    public static function log(string $accion, string $entidad = '', ?int $id = null, string $detalle = ''): void
    {
        try {
            DB::insert('auditoria', [
                'usuario_id' => $_SESSION['uid'] ?? null,
                'accion' => $accion, 'entidad' => $entidad, 'entidad_id' => $id,
                'detalle' => mb_substr($detalle, 0, 500), 'ip' => $_SERVER['REMOTE_ADDR'] ?? 'cli', 'fecha' => ahora(),
            ]);
        } catch (\Throwable $e) {
            error_log('Audit: ' . $e->getMessage());
        }
    }
}
