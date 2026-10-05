<?php
// Carga oficinas y usuarios de ejemplo (contraseña: Demo12345). Solo para pruebas/capacitación.
require dirname(__DIR__) . '/app/bootstrap.php';
use App\Core\DB;
$of = [['Alcaldía Municipal', 'ALC'], ['Secretaría Municipal General', 'SMG'], ['Finanzas', 'FIN'], ['Obras Públicas', 'OBR'], ['Desarrollo Humano', 'DH']];
foreach ($of as [$n, $s]) if (!DB::val('SELECT 1 FROM oficinas WHERE sigla=?', [$s])) DB::insert('oficinas', ['nombre' => $n, 'sigla' => $s]);
$id = fn($s) => (int)DB::val('SELECT id FROM oficinas WHERE sigla=?', [$s]);
$us = [['alcalde', 'Juan Mamani Quispe', 'Alcalde Municipal', 'JM', 'ALC', 'jefe'], ['secretaria', 'María Flores', 'Secretaria Municipal', 'MF', 'SMG', 'jefe'],
    ['finanzas', 'Carlos Choque', 'Director de Finanzas', 'CC', 'FIN', 'jefe'], ['contador', 'Ana Condori', 'Contadora', 'AC', 'FIN', 'usuario'],
    ['obras', 'Luis Rojas', 'Director de Obras Públicas', 'LR', 'OBR', 'jefe'], ['ventanilla', 'Rosa Vargas', 'Encargada de Ventanilla', 'RV', 'SMG', 'ventanilla']];
foreach ($us as [$l, $n, $c, $m, $o, $r]) if (!DB::val('SELECT 1 FROM usuarios WHERE login=?', [$l])) {
    DB::insert('usuarios', ['login' => $l, 'nombre' => $n, 'cargo' => $c, 'mosca' => $m, 'oficina_id' => $id($o), 'rol' => $r, 'password_hash' => password_hash('Demo12345', PASSWORD_DEFAULT)]);
}
DB::exec("UPDATE usuarios SET jefe_id=(SELECT x.id FROM (SELECT id FROM usuarios WHERE login='finanzas') x) WHERE login='contador'");
echo "Datos de ejemplo cargados.\n";
