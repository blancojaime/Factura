<?php
// Prueba de flujo de negocio. Uso: php tests/flujo.php  (usa BD "corr_test"; la RECREA)
declare(strict_types=1);
require dirname(__DIR__) . '/app/bootstrap.php';

use App\Core\{Config, DB};
use App\Services\Correspondencia as C;

$db = ['host' => getenv('DB_HOST') ?: '127.0.0.1', 'port' => 3306, 'name' => 'corr_test', 'user' => getenv('DB_USER') ?: 'root', 'pass' => getenv('DB_PASS') ?: ''];
$root = new PDO("mysql:host={$db['host']}", $db['user'], $db['pass']);
$root->exec('DROP DATABASE IF EXISTS corr_test; CREATE DATABASE corr_test CHARACTER SET utf8mb4');
App\Installer::instalar($db, 'Municipio de Prueba', 'GAMP', ['login' => 'admin', 'nombre' => 'Admin', 'password' => 'admin12345'], false);

$fallos = 0;
function ok(bool $c, string $m): void { global $fallos; echo ($c ? "  OK   " : "  FALLA") . " $m\n"; if (!$c) $fallos++; }
function falla(callable $f, string $m): void { try { $f(); ok(false, "$m (no lanzó excepción)"); } catch (RuntimeException $e) { ok(true, "$m → «{$e->getMessage()}»"); } }

$of1 = DB::insert('oficinas', ['nombre' => 'Alcaldía', 'sigla' => 'ALC']);
$of2 = DB::insert('oficinas', ['nombre' => 'Finanzas', 'sigla' => 'FIN']);
$of3 = DB::insert('oficinas', ['nombre' => 'Obras', 'sigla' => 'OBR']);
$mk = fn($l, $of, $rol = 'usuario') => DB::one('SELECT * FROM usuarios WHERE id=?', [DB::insert('usuarios', ['login' => $l, 'nombre' => strtoupper($l), 'cargo' => "Cargo $l", 'mosca' => substr($l, 0, 2), 'oficina_id' => $of, 'rol' => $rol, 'password_hash' => password_hash('x', PASSWORD_DEFAULT)])]);
$alc = $mk('alcalde', $of1, 'jefe'); $fin = $mk('finanzas', $of2, 'jefe'); $obr = $mk('obras', $of3); $obr2 = $mk('obras2', $of3);
$tipoInf = (int)DB::val("SELECT id FROM tipos_documento WHERE prefijo='INF'");

echo "== Documentos, NUR y CITE\n";
[$d1, $h1] = C::crearDocumento($alc, $tipoInf, ['destinatario_nombre' => 'FINANZAS', 'referencia' => 'Presupuesto', 'contenido' => '<p>Hola<script>alert(1)</script><b onclick="x()">negrita</b></p>']);
[$d2, $h2] = C::crearDocumento($alc, $tipoInf, ['destinatario_nombre' => 'FINANZAS', 'referencia' => 'Otro']);
$nur1 = DB::val('SELECT nur FROM hojas_ruta WHERE id=?', [$h1]); $nur2 = DB::val('SELECT nur FROM hojas_ruta WHERE id=?', [$h2]);
ok($nur1 === 'GAMP/' . gestion() . '-00001' && $nur2 === 'GAMP/' . gestion() . '-00002', "NUR correlativo: $nur1, $nur2");
ok(DB::val('SELECT cite FROM documentos WHERE id=?', [$d2]) === 'INF/GAMP/ALC Nº 0002/' . gestion(), 'CITE correlativo por tipo/oficina: ' . DB::val('SELECT cite FROM documentos WHERE id=?', [$d2]));
$html = DB::val('SELECT contenido FROM documentos WHERE id=?', [$d1]);
ok(!str_contains($html, 'script') && !str_contains($html, 'onclick') && str_contains($html, '<b>negrita</b>'), "HTML saneado: $html");
[$d3] = C::crearDocumento($alc, $tipoInf, ['destinatario_nombre' => 'X', 'referencia' => 'Respuesta mismo NUR'], $h1);
ok((int)DB::val('SELECT hoja_id FROM documentos WHERE id=?', [$d3]) === $h1, 'Asignar NUR existente propio');
falla(fn() => C::crearDocumento($fin, $tipoInf, ['destinatario_nombre' => 'X', 'referencia' => 'Intruso'], $h1), 'No se puede usar NUR ajeno');
falla(fn() => C::crearDocumento($alc, $tipoInf, ['destinatario_nombre' => 'X', 'referencia' => ''], null), 'Referencia obligatoria');
DB::insert('tipos_documento_oficina', ['tipo_id' => $tipoInf, 'oficina_id' => $of2]);
falla(fn() => C::crearDocumento($alc, $tipoInf, ['destinatario_nombre' => 'X', 'referencia' => 'x']), 'Tipo restringido a otra oficina');
DB::exec('DELETE FROM tipos_documento_oficina');

echo "== Derivación y recepción\n";
$der = C::derivar($alc, $h1, (int)$fin['id'], 'oficial', 'Acción Necesaria', 'Remito para su atención', true);
falla(fn() => C::derivar($alc, $h1, (int)$obr['id'], 'oficial', '', 'otra oficial', false), 'Oficial solo una vez');
$cop = C::derivar($alc, $h1, (int)$obr['id'], 'copia', '', 'Para su conocimiento', false);
ok(count(C::entrada((int)$fin['id'])) === 1 && count(C::enviados((int)$alc['id'])) === 2, 'Entrada del destino y Enviados del origen');
falla(fn() => C::derivar($obr2, $h1, (int)$fin['id'], 'copia', '', 'sin tenencia', false), 'No deriva quien no tiene la hoja');
C::cancelar($alc, $cop);
ok(count(C::enviados((int)$alc['id'])) === 1, 'Cancelar derivación de copia');
ok(C::recibir($obr, [$cop]) === 0, 'Derivación cancelada no se puede recibir');
ok(C::recibir($fin, [$der]) === 1 && count(C::pendientes((int)$fin['id'])) === 1, 'Recepción → Pendientes');
falla(fn() => C::cancelar($alc, $der), 'No se cancela una derivación ya recibida');
ok(C::tenencia((int)$fin['id'], $h1) !== null, 'Tenencia del receptor');

echo "== Reenvío, respuesta, archivo\n";
[$dr] = C::crearDocumento($fin, $tipoInf, ['destinatario_nombre' => 'ALCALDE', 'referencia' => 'Respuesta'], $h1);
ok((int)DB::val('SELECT hoja_id FROM documentos WHERE id=?', [$dr]) === $h1, 'Generar respuesta con mismo NUR (por tenencia)');
$der2 = C::derivar($fin, $h1, (int)$obr['id'], 'oficial', 'Revisar', 'Remito', false);
ok(DB::val('SELECT estado FROM derivaciones WHERE id=?', [$der]) === 'derivado', 'Origen pasa a "derivado"');
C::cancelar($fin, $der2);
ok(DB::val('SELECT estado FROM derivaciones WHERE id=?', [$der]) === 'pendiente', 'Cancelar devuelve a Pendientes');
C::archivar($fin, [$der], 0, 'Correspondencia 2026', 'ok');
ok(DB::val('SELECT estado FROM derivaciones WHERE id=?', [$der]) === 'archivado' && (int)DB::val('SELECT COUNT(*) FROM archivados') === 1, 'Archivar en carpeta nueva');
C::desarchivar($fin, $der);
ok(DB::val('SELECT estado FROM derivaciones WHERE id=?', [$der]) === 'pendiente', 'Desarchivar');

echo "== Agrupar\n";
$der3 = C::derivar($alc, $h2, (int)$fin['id'], 'oficial', '', 'segunda', false);
C::recibir($fin, [$der3]);
falla(fn() => C::agrupar($fin, [$der], $der), 'Agrupar requiere 2+');
$g = C::agrupar($fin, [$der, $der3], $der);
ok(count(C::pendientes((int)$fin['id'])) === 1, 'Solo la principal queda en Pendientes');
$dd = C::derivar($fin, $h1, (int)$obr['id'], 'oficial', '', 'agrupadas', false);
ok((int)DB::val("SELECT COUNT(*) FROM derivaciones WHERE a_usuario_id=? AND estado='no_recibido'", [$obr['id']]) === 2, 'Derivar principal arrastra la agrupada');
C::cancelar($fin, $dd);
ok(count(C::pendientes((int)$fin['id'])) === 1 && DB::val('SELECT estado FROM derivaciones WHERE id=?', [$der3]) === 'agrupado', 'Cancelar restituye la agrupación');

echo "== Acceso y seguimiento\n";
ok(C::puedeVer($fin, $h1) && !C::puedeVer($obr2, $h2), 'Control de acceso por participación/oficina');
ok(count(C::seguimiento($h1)) === 1, 'Seguimiento omite canceladas');

echo "== Concurrencia de correlativos\n";
$pids = [];
for ($i = 0; $i < 4; $i++) {
    $pid = pcntl_fork();
    if ($pid === 0) { DB::reset(); for ($j = 0; $j < 10; $j++) App\Services\Numerador::siguiente('TEST'); exit(0); }
    $pids[] = $pid;
}
foreach ($pids as $p) pcntl_waitpid($p, $st);
DB::reset();
ok((int)DB::val("SELECT ultimo FROM correlativos WHERE clave='TEST'") === 40, 'Sin duplicados ni saltos con 4 procesos × 10');

echo "== Importador de cargos (Excel real)\n";
use App\Services\ImportadorCargos as IC;
$plan = IC::planificar(IC::leer(ROOT . '/database/Cargos_y_Oficinas_GAM.xlsx', 'x.xlsx'));
ok(count($plan['usuarios']) === 46, 'Plan: 46 cargos → ' . count($plan['usuarios']));
ok(count($plan['oficinas']) === 4, 'Plan: 4 oficinas (unidad truncada unida) → ' . implode(' | ', array_map(fn($o) => $o['sigla'] . ':' . $o['nombre'], $plan['oficinas'])));
ok(count($plan['avisos']) >= 2, 'Avisos de nombres cortados: ' . implode(' / ', $plan['avisos']));
$cred = IC::aplicar($plan);
ok(count($cred) === 46 && strlen($cred[0]['clave']) === 8, 'Aplicar crea 46 usuarios con clave temporal');
ok(count(IC::aplicar(IC::planificar(IC::leer(ROOT . '/database/Cargos_y_Oficinas_GAM.xlsx', 'x.xlsx')))) === 0, 'Idempotente: segunda importación no crea nada');
ok(DB::val("SELECT rol FROM usuarios WHERE login='u401'") === 'jefe' && DB::val("SELECT jefe_id FROM usuarios WHERE login='u401'") === null, 'Alcalde: rol jefe sin jefe superior');
ok(DB::val("SELECT j.login FROM usuarios u JOIN usuarios j ON j.id=u.jefe_id WHERE u.login='u410'") === 'u402', 'Jefe de Contrataciones depende del Secretario Administrativo (u402)');
ok(DB::val("SELECT rol FROM usuarios WHERE login='u435'") === 'ventanilla', 'Responsable de Archivo → ventanilla');
ok((int)DB::val("SELECT COUNT(*) FROM usuarios u JOIN oficinas o ON o.id=u.oficina_id WHERE o.sigla LIKE 'SMOP%'") === 6, 'Fila 151 unida a Obras Públicas (6 cargos)');
ok((int)DB::val("SELECT COUNT(*) FROM usuarios WHERE cambiar_clave=1") === 46 && password_verify($cred[0]['clave'], DB::val("SELECT password_hash FROM usuarios WHERE login=?", [$cred[0]['login']])), 'Clave temporal válida y cambio obligatorio');

echo $fallos ? "\n$fallos FALLO(S)\n" : "\nTODO OK\n";
exit($fallos ? 1 : 0);
