<?php
declare(strict_types=1);
namespace App\Core;

final class Uploader
{
    private const PERMITIDOS = [
        'pdf' => 'application/pdf', 'jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png',
        'doc' => 'application/msword', 'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls' => 'application/vnd.ms-excel', 'xlsx' => 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'odt' => 'application/vnd.oasis.opendocument.text', 'ods' => 'application/vnd.oasis.opendocument.spreadsheet',
        'txt' => 'text/plain', 'zip' => 'application/zip',
    ];

    public static function dir(): string
    {
        $d = Config::get('uploads_dir', ROOT . '/storage/uploads');
        if (!is_dir($d)) mkdir($d, 0750, true);
        return $d;
    }

    /** Guarda un archivo subido ($_FILES[x]) y devuelve [nombre_original, nombre_disco, mime, tamano] o lanza \RuntimeException. */
    public static function guardar(array $f): array
    {
        if (($f['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) throw new \RuntimeException('Error al subir el archivo (código ' . ($f['error'] ?? '?') . ').');
        $max = (int)Config::get('max_upload_mb', 10) * 1048576;
        if ($f['size'] > $max) throw new \RuntimeException('El archivo supera el máximo de ' . Config::get('max_upload_mb', 10) . ' MB.');
        if (!is_uploaded_file($f['tmp_name']) && !Config::get('testing')) throw new \RuntimeException('Archivo no válido.');
        $nombre = basename(str_replace("\0", '', $f['name']));
        $ext = strtolower(pathinfo($nombre, PATHINFO_EXTENSION));
        if (!isset(self::PERMITIDOS[$ext])) throw new \RuntimeException('Tipo de archivo no permitido (.' . $ext . ').');
        $mime = (new \finfo(FILEINFO_MIME_TYPE))->file($f['tmp_name']) ?: '';
        $okMime = $mime === self::PERMITIDOS[$ext]
            || ($ext === 'zip' || str_starts_with(self::PERMITIDOS[$ext], 'application/vnd.')) && in_array($mime, ['application/zip', 'application/octet-stream', self::PERMITIDOS[$ext]], true)
            || ($ext === 'doc' || $ext === 'xls') && $mime === 'application/octet-stream'
            || ($ext === 'doc' || $ext === 'xls') && $mime === 'application/CDFV2'
            || ($ext === 'txt' && str_starts_with($mime, 'text/'));
        if (!$okMime) throw new \RuntimeException('El contenido del archivo no coincide con su extensión.');
        $disco = bin2hex(random_bytes(16)) . '.' . $ext;
        $dest = self::dir() . '/' . $disco;
        $mover = Config::get('testing') ? 'rename' : 'move_uploaded_file';
        if (!$mover($f['tmp_name'], $dest)) throw new \RuntimeException('No se pudo guardar el archivo.');
        chmod($dest, 0640);
        return [mb_substr($nombre, 0, 200), $disco, self::PERMITIDOS[$ext], (int)$f['size']];
    }
}
