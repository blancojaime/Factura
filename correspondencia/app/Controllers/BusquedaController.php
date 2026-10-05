<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Auth, Controller, DB};

final class BusquedaController extends Controller
{
    public function index(): void
    {
        $u = Auth::user();
        $q = $this->in('q');
        $campos = array_intersect((array)($_GET['campos'] ?? ['hoja', 'cite', 'referencia']), ['hoja', 'cite', 'destinatario', 'remitente', 'referencia']);
        $rows = null;
        if ($q !== '') {
            $like = '%' . str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $q) . '%';
            $cond = []; $p = [];
            $map = ['hoja' => 'h.nur LIKE ?', 'cite' => 'dc.cite LIKE ?', 'destinatario' => 'dc.destinatario_nombre LIKE ?', 'remitente' => 'dc.remitente_nombre LIKE ?', 'referencia' => '(h.referencia LIKE ? OR dc.referencia LIKE ?)'];
            foreach ($campos as $c) { $cond[] = $map[$c]; $p[] = $like; if ($c === 'referencia') $p[] = $like; }
            if (!$cond) { $cond[] = 'h.nur LIKE ?'; $p[] = $like; }
            $vis = '1=1'; $pv = [];
            if ($u['rol'] !== 'admin') {
                $vis = 'h.creada_por=? OR EXISTS (SELECT 1 FROM derivaciones d JOIN usuarios x ON x.id IN (d.de_usuario_id, d.a_usuario_id) WHERE d.hoja_id=h.id AND d.estado<>"cancelado" AND (x.id=? OR x.oficina_id=?))
                        OR EXISTS (SELECT 1 FROM documentos d2 WHERE d2.hoja_id=h.id AND d2.oficina_id=?)';
                $pv = [$u['id'], $u['id'], $u['oficina_id'], $u['oficina_id']];
            }
            $rows = DB::all('SELECT h.id AS hoja_id, h.nur, h.creado_en, dc.id AS doc_id, dc.cite, dc.destinatario_nombre, dc.destinatario_cargo, dc.remitente_nombre, dc.remitente_cargo, COALESCE(dc.referencia, h.referencia) AS referencia, t.nombre AS tipo
                FROM hojas_ruta h LEFT JOIN documentos dc ON dc.hoja_id=h.id LEFT JOIN tipos_documento t ON t.id=dc.tipo_id
                WHERE (' . implode(' OR ', $cond) . ') AND (' . $vis . ') ORDER BY h.id DESC, dc.id LIMIT 200', array_merge($p, $pv));
        }
        $this->view('busqueda/index', ['menu' => 'busqueda', 'titulo' => 'Búsqueda', 'q' => $q, 'campos' => $campos, 'rows' => $rows, 'avanzada' => $this->in('avanzada') === '1' || ($q === '' && isset($_GET['q']))]);
    }
}
