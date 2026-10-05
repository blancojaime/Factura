<?php
declare(strict_types=1);
namespace App\Services;

use App\Core\Config;
use App\Core\DB;

final class Numerador
{
    /** Siguiente correlativo atómico (el bloqueo de fila dura hasta el commit de la transacción). */
    public static function siguiente(string $clave): int
    {
        return (int)DB::tx(function () use ($clave) {
            DB::q('INSERT INTO correlativos (clave, ultimo) VALUES (?, 1) ON DUPLICATE KEY UPDATE ultimo = ultimo + 1', [$clave]);
            return DB::val('SELECT ultimo FROM correlativos WHERE clave=?', [$clave]);
        });
    }

    public static function nur(int $gestion): string
    {
        $n = self::siguiente('NUR:' . $gestion);
        return sprintf('%s/%d-%05d', Config::get('entidad_sigla', 'ENT'), $gestion, $n);
    }

    public static function cite(array $tipo, array $oficina, int $gestion): string
    {
        $n = self::siguiente("CITE:{$tipo['prefijo']}:{$oficina['sigla']}:$gestion");
        return sprintf('%s/%s/%s Nº %04d/%d', $tipo['prefijo'], Config::get('entidad_sigla', 'ENT'), $oficina['sigla'], $n, $gestion);
    }
}
