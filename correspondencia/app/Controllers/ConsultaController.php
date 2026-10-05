<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Controller, DB};

/** Consulta pública del estado de un trámite con NUR + código (sin datos personales). */
final class ConsultaController extends Controller
{
    protected array $publicas = ['index'];

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
                    $mov = DB::all("SELECT d.fecha_envio, d.fecha_recepcion, d.estado, ro.nombre AS de_oficina, ao.nombre AS a_oficina
                        FROM derivaciones d JOIN usuarios ru ON ru.id=d.de_usuario_id JOIN oficinas ro ON ro.id=ru.oficina_id JOIN usuarios au ON au.id=d.a_usuario_id JOIN oficinas ao ON ao.id=au.oficina_id
                        WHERE d.hoja_id=? AND d.estado<>'cancelado' AND d.tipo='oficial' ORDER BY d.id", [$h['id']]);
                    $enCurso = array_values(array_unique(array_map(fn($m) => $m['a_oficina'], array_filter($mov, fn($m) => in_array($m['estado'], ['no_recibido', 'pendiente'], true)))));
                    $res = ['h' => $h, 'mov' => $mov, 'enCurso' => $enCurso, 'archivado' => (bool)array_filter($mov, fn($m) => $m['estado'] === 'archivado')];
                }
            }
        }
        $this->view('consulta/index', ['nur' => $nur, 'codigo' => $cod, 'res' => $res, 'error' => $error], 'layout_simple');
    }
}
