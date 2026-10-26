<?php
declare(strict_types=1);
namespace App\Services;

/** Arma el texto (campo: valor) que se codifica en los QR impresos. */
final class TextoQr
{
    private static function limpio(?string $s, int $max = 120): string
    {
        $s = trim(preg_replace('/\s+/u', ' ', (string)$s));
        return mb_strlen($s) > $max ? mb_substr($s, 0, $max - 1) . '…' : $s;
    }

    /** Sin tildes ni símbolos especiales: así todos los lectores de QR muestran el texto bien (como en el modelo). */
    public static function ascii(string $s): string
    {
        $s = strtr($s, ['á' => 'a', 'é' => 'e', 'í' => 'i', 'ó' => 'o', 'ú' => 'u', 'ü' => 'u', 'ñ' => 'n', 'Á' => 'A', 'É' => 'E', 'Í' => 'I', 'Ó' => 'O', 'Ú' => 'U', 'Ü' => 'U', 'Ñ' => 'N',
            'º' => 'o', 'ª' => 'a', '°' => 'o', '—' => '-', '–' => '-', '“' => '"', '”' => '"', '‘' => "'", '’' => "'", '…' => '...', '¿' => '', '¡' => '']);
        return preg_replace('/[^\x20-\x7E]/', '', $s) ?? '';
    }

    private static function armar(array $campos): string
    {
        $l = [];
        foreach ($campos as $k => $v) if ($v !== '' && $v !== null) $l[] = $k . ': ' . self::ascii((string)$v);
        return implode("\n", $l);
    }

    /** QR de la cabecera de la Hoja de Ruta: datos iniciales / de origen del trámite. */
    public static function hojaRuta(array $hoja, ?array $doc): string
    {
        $externa = $hoja['origen'] === 'externo';
        return self::armar([
            'HOJA DE RUTA' => $hoja['nur'] . ($externa ? ' (EXTERNA)' : ' (INTERNA)'),
            'CITE ORIGINAL' => $doc['cite'] ?? '',
            'FECHA/HORA' => date('d/m/Y H:i:s', strtotime($doc['creado_en'] ?? $hoja['creado_en'])),
            'PROCEDENCIA' => self::limpio($externa ? ($hoja['ext_institucion'] ?: $hoja['ext_remitente']) : ($doc['oficina'] ?? ''), 80),
            'REMITENTE' => self::limpio($externa ? $hoja['ext_remitente'] : trim(($doc['remitente_nombre'] ?? '') . ' - ' . ($doc['remitente_cargo'] ?? ''), ' -'), 90),
            'DESTINATARIO' => self::limpio(trim(($doc['destinatario_nombre'] ?? '') . ' - ' . ($doc['destinatario_cargo'] ?? ''), ' -'), 90),
            'REFERENCIA' => self::limpio($hoja['referencia'], 110),
            'PROCESO' => self::limpio($doc['tipo'] ?? '', 40),
            'ADJUNTO' => self::limpio($doc['adjunto_txt'] ?? '', 60),
            'HOJAS' => (string)($hoja['ext_fojas'] ?: '0'),
        ]);
    }

    /** QR de recepción de correspondencia externa (ventanilla). */
    public static function recepcion(array $hoja): string
    {
        return self::armar([
            'CODIGO DE CONTROL' => $hoja['nur'],
            'TIPO DE ENTRADA' => self::limpio($hoja['ext_documento'], 60),
            'FECHA/HORA DE REGISTRO' => date('d/m/Y H:i:s', strtotime($hoja['creado_en'])),
            'REFERENCIA' => self::limpio($hoja['referencia'], 120),
            'REMITENTE' => self::limpio(trim($hoja['ext_remitente'] . ($hoja['ext_institucion'] ? ' - ' . $hoja['ext_institucion'] : '')), 90),
            'FOJAS' => (string)($hoja['ext_fojas'] ?? ''),
            'ANEXOS' => self::limpio($hoja['ext_anexos'] ?? '', 60),
            'CELULAR CONTACTO' => self::limpio($hoja['ext_celular'] ?? '', 30),
        ]);
    }
}
