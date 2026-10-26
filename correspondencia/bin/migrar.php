<?php
// Aplica los cambios de base de datos pendientes (seguro de repetir). Uso: php bin/migrar.php
require dirname(__DIR__) . '/app/bootstrap.php';
try {
    $h = App\Services\Migrador::aplicar();
    echo $h ? 'Base de datos actualizada: ' . implode(', ', $h) . "\n" : "Base de datos al día.\n";
} catch (Throwable $e) {
    fwrite(STDERR, 'Error al actualizar la base de datos: ' . $e->getMessage() . "\n");
    exit(1);
}
