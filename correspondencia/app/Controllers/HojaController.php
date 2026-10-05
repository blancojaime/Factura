<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Auth, Controller, DB};
use App\Services\Correspondencia as C;

final class HojaController extends Controller
{
    private function pag(string $tpl, string $titulo, array $d = []): void
    {
        $this->view($tpl, $d + ['menu' => 'hojas', 'titulo' => $titulo]);
    }

    public function lista(): void
    {
        $u = Auth::user();
        $rows = DB::all("SELECT h.*, (SELECT GROUP_CONCAT(dc.cite SEPARATOR ', ') FROM documentos dc WHERE dc.hoja_id=h.id) AS cites,
            (SELECT COUNT(*) FROM derivaciones d WHERE d.hoja_id=h.id AND d.de_usuario_id=? AND d.estado<>'cancelado') AS derivadas
            FROM hojas_ruta h WHERE h.creada_por=? ORDER BY h.id DESC LIMIT 200", [$u['id'], $u['id']]);
        $this->pag('hoja/lista', 'Hojas de ruta creadas', ['rows' => $rows, 'tipos' => C::tiposHabilitados($u)]);
    }

    public function derivar(): void
    {
        $u = Auth::user();
        $hojaId = $this->inInt('id');
        $hoja = C::hoja($hojaId);
        $hold = C::tenencia((int)$u['id'], $hojaId);
        if (!$hold && (int)$hoja['creada_por'] !== (int)$u['id']) throw new \RuntimeException('No tiene esta hoja de ruta para derivarla.');
        if ($this->esPost()) {
            C::derivar($u, $hojaId, $this->inInt('destino'), $this->in('tipo'), $this->in('accion'), $this->in('proveido'), $this->in('urgente') === '1', $this->in('adjunto_txt'));
            flash($this->in('tipo') === 'oficial' ? 'Derivación oficial registrada.' : 'Copia derivada.');
            redirect('hoja/derivar', ['id' => $hojaId]);
        }
        $padre = $hold['id'] ?? null;
        $enviadas = DB::all("SELECT d.*, au.nombre AS a_nombre, au.cargo AS a_cargo, ao.nombre AS a_oficina FROM derivaciones d JOIN usuarios au ON au.id=d.a_usuario_id JOIN oficinas ao ON ao.id=au.oficina_id
            WHERE d.hoja_id=? AND d.de_usuario_id=? AND d.padre_id <=> ? AND d.estado<>'cancelado' ORDER BY d.id", [$hojaId, $u['id'], $padre]);
        $docs = DB::all('SELECT d.id, d.cite, d.referencia, t.nombre AS tipo FROM documentos d JOIN tipos_documento t ON t.id=d.tipo_id WHERE d.hoja_id=? ORDER BY d.id', [$hojaId]);
        $this->pag('hoja/derivar', 'Derivar hoja de ruta', [
            'hoja' => $hoja, 'docs' => $docs, 'enviadas' => $enviadas,
            'hayOficial' => (bool)array_filter($enviadas, fn($x) => $x['tipo'] === 'oficial'),
        ]);
    }

    public function quitar(): void
    {
        $d = DB::one('SELECT hoja_id FROM derivaciones WHERE id=?', [$this->inInt('id')]);
        C::cancelar(Auth::user(), $this->inInt('id'));
        flash('Derivación eliminada.');
        redirect('hoja/derivar', ['id' => $d['hoja_id'] ?? 0]);
    }

    public function imprimir(): void
    {
        $u = Auth::user();
        $nur = $this->in('nur');
        $id = $this->inInt('id');
        if (!$id && $nur === '') { $this->pag('hoja/imprimir_form', 'Imprimir hoja de ruta'); return; }
        $hoja = $id ? C::hoja($id) : DB::one('SELECT * FROM hojas_ruta WHERE nur=?', [$nur]);
        if (!$hoja) throw new \RuntimeException("No existe la hoja de ruta «$nur».");
        if (!C::puedeVer($u, (int)$hoja['id'])) throw new \RuntimeException('No tiene acceso a esta hoja de ruta.');
        $this->view('hoja/imprimir', [
            'hoja' => $hoja, 'seg' => C::seguimiento((int)$hoja['id']),
            'docs' => DB::all('SELECT d.*, t.nombre AS tipo FROM documentos d JOIN tipos_documento t ON t.id=d.tipo_id WHERE d.hoja_id=? ORDER BY d.id', [$hoja['id']]),
        ], 'layout_print');
    }
}
