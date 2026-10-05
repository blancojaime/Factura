<?php
declare(strict_types=1);

use App\Core\Config;

function e($v): string { return htmlspecialchars((string)$v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }

function ahora(): string { return date('Y-m-d H:i:s'); }

function gestion(): int { return (int)date('Y'); }

function base_path(): string
{
    $d = str_replace('\\', '/', dirname($_SERVER['SCRIPT_NAME'] ?? '/'));
    return rtrim($d, '/');
}

function url(string $ruta = '', array $q = []): string
{
    $params = $ruta !== '' ? ['r' => $ruta] + $q : $q;
    return base_path() . '/index.php' . ($params ? '?' . http_build_query($params) : '');
}

function asset(string $p): string { return base_path() . '/assets/' . ltrim($p, '/'); }

function redirect(string $ruta, array $q = []): never
{
    header('Location: ' . (str_starts_with($ruta, 'http') || str_starts_with($ruta, '/') ? $ruta : url($ruta, $q)));
    exit;
}

function flash(?string $msg = null, string $tipo = 'ok')
{
    if ($msg !== null) { $_SESSION['flash'][] = [$tipo, $msg]; return null; }
    $f = $_SESSION['flash'] ?? [];
    unset($_SESSION['flash']);
    return $f;
}

function fecha_larga(?string $dt): string
{
    if (!$dt) return '';
    $t = strtotime($dt);
    $dias = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
    $meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
    return ucfirst($dias[(int)date('w', $t)]) . ', ' . date('d', $t) . ' de ' . ucfirst($meses[(int)date('n', $t) - 1]) . ' de ' . date('Y', $t);
}

function fecha_corta(?string $dt): string { return $dt ? date('d/m/Y H:i', strtotime($dt)) : ''; }

function dias_desde(?string $dt): int
{
    if (!$dt) return 0;
    return (int)floor((time() - strtotime($dt)) / 86400);
}

function csrf_field(): string { return App\Core\Csrf::field(); }

function acciones(): array
{
    return ['Acción Necesaria', 'Para su conocimiento', 'Preparar respuesta', 'Elaborar informe', 'Revisar y opinar', 'Coordinar', 'Atender y devolver', 'Archivar'];
}

/** Semáforo de antigüedad de una correspondencia pendiente. */
function semaforo(?string $desde): string
{
    $d = dias_desde($desde);
    if ($d >= (int)App\Core\Config::get('dias_alerta_rojo', 6)) return 'rojo';
    if ($d >= (int)App\Core\Config::get('dias_alerta_amarillo', 3)) return 'amarillo';
    return 'verde';
}

function usuarios_agrupados(int $excluirId = 0): array
{
    $r = App\Core\DB::all('SELECT u.id, u.nombre, u.cargo, o.nombre AS oficina FROM usuarios u JOIN oficinas o ON o.id=u.oficina_id WHERE u.activo=1 AND o.activa=1 AND u.id<>? ORDER BY o.nombre, u.nombre', [$excluirId]);
    $g = [];
    foreach ($r as $x) $g[$x['oficina']][] = $x;
    return $g;
}

function select_usuarios(string $name, int $excluirId = 0, string $extra = ''): string
{
    $h = '<select name="' . e($name) . '" ' . $extra . '><option value="">— Seleccione —</option>';
    foreach (usuarios_agrupados($excluirId) as $of => $us) {
        $h .= '<optgroup label="' . e($of) . '">';
        foreach ($us as $u) $h .= '<option value="' . (int)$u['id'] . '" data-nombre="' . e($u['nombre']) . '" data-cargo="' . e($u['cargo']) . '">' . e($u['nombre'] . ' — ' . $u['cargo']) . '</option>';
        $h .= '</optgroup>';
    }
    return $h . '</select>';
}
