<?php
// Respaldo: volcado SQL + archivos adjuntos en storage/backups/. Uso: php bin/backup.php  (programar con cron diario)
require dirname(__DIR__) . '/app/bootstrap.php';
use App\Core\Config;
$db = Config::get('db');
$stamp = date('Ymd_His');
$dir = ROOT . '/storage/backups';
$sql = "$dir/db_$stamp.sql.gz";
$cmd = sprintf('mysqldump --single-transaction -h%s -P%d -u%s %s %s | gzip > %s',
    escapeshellarg($db['host']), (int)($db['port'] ?? 3306), escapeshellarg($db['user']), $db['pass'] !== '' ? '-p' . escapeshellarg($db['pass']) : '', escapeshellarg($db['name']), escapeshellarg($sql));
exec($cmd, $o, $rc);
if ($rc !== 0) { fwrite(STDERR, "Falló mysqldump (código $rc). ¿Está instalado?\n"); exit(1); }
$zip = new ZipArchive();
if ($zip->open("$dir/archivos_$stamp.zip", ZipArchive::CREATE) === true) {
    foreach (glob(ROOT . '/storage/uploads/*') ?: [] as $f) if (is_file($f) && basename($f) !== '.gitkeep') $zip->addFile($f, basename($f));
    $zip->close();
}
// Conserva los últimos 14 respaldos de cada tipo.
foreach (['db_*.sql.gz', 'archivos_*.zip'] as $pat) { $f = glob("$dir/$pat") ?: []; sort($f); foreach (array_slice($f, 0, max(0, count($f) - 14)) as $old) unlink($old); }
echo "Respaldo creado: $sql\n";
