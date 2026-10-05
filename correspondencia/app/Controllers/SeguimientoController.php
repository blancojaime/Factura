<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Auth, Controller, DB};
use App\Services\Correspondencia as C;

final class SeguimientoController extends Controller
{
    public function index(): void
    {
        $u = Auth::user();
        $rows = DB::all("SELECT d.*, h.nur, au.nombre AS a_nombre, au.cargo AS a_cargo FROM derivaciones d JOIN hojas_ruta h ON h.id=d.hoja_id JOIN usuarios au ON au.id=d.a_usuario_id
            WHERE d.de_usuario_id=? AND d.estado<>'cancelado' ORDER BY d.id DESC LIMIT 200", [$u['id']]);
        $this->view('seguimiento/index', ['menu' => 'seguimiento', 'titulo' => 'Seguimiento', 'rows' => $rows]);
    }

    public function ver(): void
    {
        $u = Auth::user();
        $hoja = DB::one('SELECT * FROM hojas_ruta WHERE id=?', [$this->inInt('id')]);
        if (!$hoja) throw new \RuntimeException('Hoja de ruta no encontrada.');
        if (!C::puedeVer($u, (int)$hoja['id'])) throw new \RuntimeException('No tiene acceso al seguimiento de esta hoja de ruta.');
        $this->view('seguimiento/ver', [
            'menu' => 'seguimiento', 'titulo' => 'Seguimiento ' . $hoja['nur'], 'hoja' => $hoja, 'seg' => C::seguimiento((int)$hoja['id']),
            'docs' => DB::all('SELECT d.*, t.nombre AS tipo FROM documentos d JOIN tipos_documento t ON t.id=d.tipo_id WHERE d.hoja_id=? ORDER BY d.id', [$hoja['id']]),
            'adjuntos' => DB::all('SELECT * FROM adjuntos WHERE hoja_id=? ORDER BY id', [$hoja['id']]),
        ]);
    }
}
