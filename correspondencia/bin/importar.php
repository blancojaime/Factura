<?php
// Importa cargos y oficinas desde Excel/CSV por consola.
// Uso: php bin/importar.php archivo.xlsx [salida_claves.csv]
require dirname(__DIR__) . '/app/bootstrap.php';
use App\Services\ImportadorCargos as IC;

$archivo = $argv[1] ?? '';
if (!is_file($archivo)) { fwrite(STDERR, "Uso: php bin/importar.php archivo.xlsx [claves.csv]\n"); exit(1); }
$plan = IC::planificar(IC::leer($archivo, $archivo));
foreach ($plan['avisos'] as $a) echo "Aviso: $a\n";
$cred = IC::aplicar($plan);
echo count($plan['oficinas']) . ' oficinas, ' . count($cred) . " usuarios nuevos.\n";
if ($cred && !empty($argv[2])) {
    $o = fopen($argv[2], 'w'); fwrite($o, "\xEF\xBB\xBF");
    fputcsv($o, ['Oficina', 'Cargo', 'Usuario', 'Clave temporal'], ';');
    foreach ($cred as $c) fputcsv($o, [$c['oficina'], $c['cargo'], $c['login'], $c['clave']], ';');
    fclose($o);
    echo "Claves temporales guardadas en {$argv[2]}\n";
}
