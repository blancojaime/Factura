<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Auth, Controller, DB};

final class ReporteController extends Controller
{
    private const ESTADOS = ['' => 'Todos', 'no_recibido' => 'No recibido', 'pendiente' => 'Pendiente', 'derivado' => 'Derivado', 'archivado' => 'Archivado', 'agrupado' => 'Agrupado'];

    /** Usuarios sobre los que el usuario actual puede reportar. */
    private function alcance(): array
    {
        $u = Auth::user();
        if ($u['rol'] === 'admin') return DB::all('SELECT id, nombre, oficina_id FROM usuarios WHERE activo=1 ORDER BY nombre');
        if (Auth::esJefe()) return DB::all('SELECT id, nombre, oficina_id FROM usuarios WHERE activo=1 AND oficina_id=? ORDER BY nombre', [$u['oficina_id']]);
        return [['id' => $u['id'], 'nombre' => $u['nombre'], 'oficina_id' => $u['oficina_id']]];
    }

    private function pag(string $tpl, string $titulo, array $d = []): void
    {
        $this->view($tpl, $d + ['menu' => 'reportes', 'titulo' => $titulo]);
    }

    public function oficina(): void
    {
        $u = Auth::user();
        if (!Auth::esJefe()) throw new \RuntimeException('Este reporte es solo para responsables de oficina.');
        $of = $u['rol'] === 'admin' && $this->inInt('oficina') ? $this->inInt('oficina') : (int)$u['oficina_id'];
        $oficina = DB::one('SELECT * FROM oficinas WHERE id=?', [$of]);
        $this->pag('reporte/oficina', 'Pendientes de la oficina', [
            'oficina' => $oficina, 'grafico' => DashboardController::graficoOficina($of), 'oficinas' => $u['rol'] === 'admin' ? DB::all('SELECT id, nombre FROM oficinas WHERE activa=1 ORDER BY nombre') : [],
            'filas' => DB::all("SELECT us.nombre, us.cargo, SUM(d.estado='pendiente' AND d.tipo='oficial') AS oficial, SUM(d.estado='pendiente' AND d.tipo='copia') AS copia, SUM(d.estado='archivado') AS archivado, SUM(d.estado='no_recibido') AS no_recibido
                FROM usuarios us LEFT JOIN derivaciones d ON d.a_usuario_id=us.id WHERE us.oficina_id=? AND us.activo=1 GROUP BY us.id ORDER BY us.nombre", [$of]),
        ]);
    }

    public function recibida(): void { $this->listado('a', 'Correspondencia recibida', false); }

    public function enviada(): void { $this->listado('de', 'Correspondencia enviada', false); }

    public function personalizado(): void { $this->listado('a', 'Reporte personalizado', true); }

    private function listado(string $lado, string $titulo, bool $conEstado): void
    {
        $alcance = $this->alcance();
        $ids = array_map(fn($x) => (int)$x['id'], $alcance);
        $generar = isset($_GET['generar']);
        $desde = $this->in('desde', date('Y-m-d', strtotime('-30 days')));
        $hasta = $this->in('hasta', date('Y-m-d'));
        $quien = $this->inInt('quien');
        $estado = $conEstado ? $this->in('estado') : '';
        $rows = null;
        if ($generar) {
            if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $desde) || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $hasta)) throw new \RuntimeException('Fechas inválidas.');
            $sel = $quien && in_array($quien, $ids, true) ? [$quien] : $ids;
            $campo = $lado === 'a' ? 'd.a_usuario_id' : 'd.de_usuario_id';
            $sql = "SELECT h.nur, GROUP_CONCAT(DISTINCT dc.cite SEPARATOR ', ') AS cites, h.referencia, d.estado, d.tipo, d.accion, d.proveido, d.fecha_envio, d.fecha_recepcion,
                ru.nombre AS de_nombre, ru.cargo AS de_cargo, au.nombre AS a_nombre, au.cargo AS a_cargo
                FROM derivaciones d JOIN hojas_ruta h ON h.id=d.hoja_id JOIN usuarios ru ON ru.id=d.de_usuario_id JOIN usuarios au ON au.id=d.a_usuario_id LEFT JOIN documentos dc ON dc.hoja_id=h.id
                WHERE $campo IN (" . implode(',', $sel) . ") AND d.estado<>'cancelado' AND d.fecha_envio BETWEEN ? AND ?";
            $p = [$desde . ' 00:00:00', $hasta . ' 23:59:59'];
            if ($estado !== '' && isset(self::ESTADOS[$estado])) { $sql .= ' AND d.estado=?'; $p[] = $estado; }
            $rows = DB::all($sql . ' GROUP BY d.id ORDER BY d.fecha_envio DESC LIMIT 1000', $p);
            if ($this->in('csv') === '1') { $this->csv($rows); return; }
        }
        $this->pag('reporte/listado', $titulo, ['lado' => $lado, 'alcance' => $alcance, 'desde' => $desde, 'hasta' => $hasta, 'quien' => $quien, 'estado' => $estado, 'estados' => self::ESTADOS, 'conEstado' => $conEstado, 'rows' => $rows, 'accion' => $_GET['r']]);
    }

    private function csv(array $rows): void
    {
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="reporte_' . date('Ymd_His') . '.csv"');
        $o = fopen('php://output', 'w');
        fwrite($o, "\xEF\xBB\xBF");
        fputcsv($o, ['NUR', 'Documentos', 'Referencia', 'Tipo', 'Estado', 'De', 'A', 'Acción', 'Proveído', 'Fecha envío', 'Fecha recepción'], ';');
        foreach ($rows as $r) fputcsv($o, [$r['nur'], $r['cites'], $r['referencia'], $r['tipo'], $r['estado'], $r['de_nombre'], $r['a_nombre'], $r['accion'], $r['proveido'], $r['fecha_envio'], $r['fecha_recepcion']], ';');
        fclose($o);
        exit;
    }
}
