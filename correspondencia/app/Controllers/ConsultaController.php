<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Controller, DB};

/** Consulta pública del estado de un trámite con NUR + código (sin datos personales). */
final class ConsultaController extends Controller
{
    protected array $publicas = ['index'];

    /** Trazabilidad pública: solo oficinas y cargos (sin nombres ni contenido). */
    private static function trazabilidad(array $h): array
    {
        $origen = DB::one('SELECT o.nombre AS oficina, u.cargo FROM usuarios u JOIN oficinas o ON o.id=u.oficina_id WHERE u.id=?', [$h['creada_por']]);
        $ders = DB::all("SELECT d.id, d.padre_id, d.tipo, d.estado, d.accion, d.urgente, d.fecha_envio, d.fecha_recepcion,
                ro.nombre AS de_oficina, ru.cargo AS de_cargo, ao.nombre AS a_oficina, au.cargo AS a_cargo, ar.fecha AS fecha_archivo
            FROM derivaciones d JOIN usuarios ru ON ru.id=d.de_usuario_id JOIN oficinas ro ON ro.id=ru.oficina_id
            JOIN usuarios au ON au.id=d.a_usuario_id JOIN oficinas ao ON ao.id=au.oficina_id
            LEFT JOIN archivados ar ON ar.derivacion_id=d.id
            WHERE d.hoja_id=? AND d.estado<>'cancelado' ORDER BY d.id", [$h['id']]);
        $hijos = [];
        foreach ($ders as $d) if ($d['padre_id']) $hijos[$d['padre_id']][] = $d['fecha_envio'];
        $actual = []; $archivado = false;
        foreach ($ders as &$d) {
            $inicio = $d['fecha_recepcion'] ?: $d['fecha_envio'];
            $fin = null;
            if ($d['estado'] === 'derivado' && !empty($hijos[$d['id']])) $fin = min($hijos[$d['id']]);
            elseif ($d['estado'] === 'archivado') { $fin = $d['fecha_archivo']; $archivado = $archivado || $d['tipo'] === 'oficial'; }
            $d['dias'] = max(0, (int)floor((($fin ? strtotime($fin) : time()) - strtotime($inicio)) / 86400));
            $d['vigente'] = in_array($d['estado'], ['no_recibido', 'pendiente'], true);
            if ($d['vigente']) $actual[] = $d;
        }
        unset($d);
        $oficialesVigentes = array_filter($actual, fn($d) => $d['tipo'] === 'oficial');
        $estado = $oficialesVigentes || $actual ? 'En trámite' : ($archivado ? 'Concluido / archivado' : ($ders ? 'En trámite' : 'Registrado, pendiente de derivación'));
        return ['h' => $h, 'origen' => $origen, 'ders' => $ders, 'actual' => $actual, 'estado' => $estado, 'total_dias' => (int)floor((time() - strtotime($h['creado_en'])) / 86400)];
    }

    public function index(): void
    {
        $nur = strtoupper($this->in('nur'));
        $cod = strtoupper($this->in('codigo'));
        $res = null; $error = '';
        if ($nur !== '' || $cod !== '') {
            $ip = $_SERVER['REMOTE_ADDR'] ?? '';
            $desde = date('Y-m-d H:i:s', time() - 900);
            if ((int)DB::val("SELECT COUNT(*) FROM intentos_login WHERE ok=0 AND login='consulta' AND ip=? AND fecha>=?", [$ip, $desde]) >= 10) {
                $error = 'Demasiados intentos. Intente nuevamente en unos minutos.';
            } else {
                $h = DB::one('SELECT * FROM hojas_ruta WHERE nur=? AND codigo_consulta=?', [$nur, $cod]);
                if (!$h) {
                    DB::insert('intentos_login', ['login' => 'consulta', 'ip' => $ip, 'ok' => 0, 'fecha' => ahora()]);
                    $error = 'No se encontró un trámite con esos datos.';
                } else {
                    $res = self::trazabilidad($h);
                }
            }
        }
        $this->view('consulta/index', ['nur' => $nur, 'codigo' => $cod, 'res' => $res, 'error' => $error], 'layout_simple');
    }
}
