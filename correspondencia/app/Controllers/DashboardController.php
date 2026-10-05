<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Auth, Controller, DB};
use App\Services\Correspondencia as C;

final class DashboardController extends Controller
{
    public function index(): void
    {
        $u = Auth::user();
        $dependientes = DB::all(
            "SELECT us.id, us.nombre, us.cargo, (SELECT COUNT(*) FROM derivaciones d WHERE d.a_usuario_id=us.id AND d.estado IN ('pendiente','no_recibido')) AS pendientes
             FROM usuarios us WHERE us.jefe_id=? AND us.activo=1 ORDER BY us.nombre", [$u['id']]);
        $docs = DB::all('SELECT t.nombre, COUNT(d.id) n FROM tipos_documento t LEFT JOIN documentos d ON d.tipo_id=t.id AND d.creado_por=? WHERE t.activo=1 GROUP BY t.id, t.nombre, t.prefijo HAVING n>0 OR t.prefijo IN ("INF","NI","CAR","MEM") ORDER BY t.nombre', [$u['id']]);
        $this->view('dashboard/index', [
            'menu' => 'inicio', 'titulo' => 'Inicio', 'c' => C::contadores((int)$u['id']), 'dependientes' => $dependientes,
            'docs' => $docs, 'grafico' => self::graficoOficina((int)$u['oficina_id']),
        ]);
    }

    public static function graficoOficina(int $oficinaId): array
    {
        $r = DB::all(
            "SELECT us.mosca, us.nombre,
               SUM(d.estado='pendiente' AND d.tipo='oficial') AS oficial, SUM(d.estado='pendiente' AND d.tipo='copia') AS copia, SUM(d.estado='archivado') AS archivado
             FROM usuarios us LEFT JOIN derivaciones d ON d.a_usuario_id=us.id WHERE us.oficina_id=? AND us.activo=1 GROUP BY us.id ORDER BY us.nombre", [$oficinaId]);
        return [
            'labels' => array_map(fn($x) => $x['mosca'] ?: $x['nombre'], $r),
            'datasets' => [
                ['label' => 'Pendientes oficiales', 'data' => array_map(fn($x) => (int)$x['oficial'], $r)],
                ['label' => 'Copias pendientes', 'data' => array_map(fn($x) => (int)$x['copia'], $r)],
                ['label' => 'Archivados', 'data' => array_map(fn($x) => (int)$x['archivado'], $r)],
            ],
        ];
    }
}
