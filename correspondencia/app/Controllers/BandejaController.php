<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Auth, Controller, DB};
use App\Services\Correspondencia as C;

final class BandejaController extends Controller
{
    private function pag(string $tpl, string $titulo, array $d): void
    {
        $this->view($tpl, $d + ['menu' => 'bandeja', 'titulo' => $titulo, 'c' => C::contadores(Auth::id())]);
    }

    public function entrada(): void
    {
        $orden = $this->in('orden');
        $this->pag('bandeja/entrada', 'Bandeja de Entrada', ['items' => C::entrada(Auth::id(), $orden), 'orden' => $orden]);
    }

    public function pendientes(): void
    {
        $orden = $this->in('orden');
        $mostrar = $this->in('mostrar', 'todo');
        $this->pag('bandeja/pendientes', 'Pendientes', [
            'items' => C::pendientes(Auth::id(), $mostrar, $orden), 'orden' => $orden, 'mostrar' => $mostrar,
            'tipos' => C::tiposHabilitados(Auth::user()),
        ]);
    }

    public function enviados(): void
    {
        $this->pag('bandeja/enviados', 'Enviados', ['items' => C::enviados(Auth::id())]);
    }

    public function recibir(): void
    {
        $ids = $this->ids();
        if ($solo = $this->inInt('solo')) $ids = [$solo];
        if (!$ids) throw new \RuntimeException('Seleccione al menos una hoja de ruta.');
        $n = C::recibir(Auth::user(), $ids);
        flash("$n hoja(s) de ruta recepcionada(s). Ahora están en Pendientes.");
        redirect('bandeja/pendientes');
    }

    public function cancelar(): void
    {
        C::cancelar(Auth::user(), $this->inInt('id'));
        flash('Derivación cancelada. La hoja de ruta volvió a sus Pendientes.');
        redirect('bandeja/enviados');
    }

    public function archivar(): void
    {
        $u = Auth::user();
        $ids = $this->ids();
        if (!$ids) throw new \RuntimeException('Seleccione al menos una hoja de ruta.');
        if ($this->in('confirmar') === '1') {
            $n = C::archivar($u, $ids, $this->inInt('carpeta_id'), $this->in('nueva_carpeta'), $this->in('observacion'));
            flash("$n hoja(s) de ruta archivada(s).");
            redirect('bandeja/archivados');
        }
        $sel = DB::all('SELECT d.id, h.nur FROM derivaciones d JOIN hojas_ruta h ON h.id=d.hoja_id WHERE d.a_usuario_id=? AND d.estado="pendiente" AND d.id IN (' . implode(',', array_map('intval', $ids)) . ')', [$u['id']]);
        $this->pag('bandeja/archivar', 'Archivar correspondencia', ['sel' => $sel, 'carpetas' => DB::all('SELECT * FROM carpetas WHERE usuario_id=? ORDER BY nombre', [$u['id']])]);
    }

    public function archivados(): void
    {
        $u = Auth::user();
        $carpetaId = $this->inInt('carpeta');
        if ($carpetaId) {
            $carpeta = DB::one('SELECT * FROM carpetas WHERE id=? AND usuario_id=?', [$carpetaId, $u['id']]);
            if (!$carpeta) throw new \RuntimeException('Carpeta no encontrada.');
            $items = DB::all('SELECT d.id, d.hoja_id, h.nur, h.referencia, a.observacion, a.fecha, (SELECT GROUP_CONCAT(dc.cite SEPARATOR ", ") FROM documentos dc WHERE dc.hoja_id=h.id) AS cites
                FROM archivados a JOIN derivaciones d ON d.id=a.derivacion_id JOIN hojas_ruta h ON h.id=d.hoja_id WHERE a.carpeta_id=? AND d.estado="archivado" ORDER BY a.fecha DESC', [$carpetaId]);
            $this->pag('bandeja/archivados_carpeta', 'Carpeta: ' . $carpeta['nombre'], ['carpeta' => $carpeta, 'items' => $items]);
            return;
        }
        $carpetas = DB::all('SELECT c.*, (SELECT COUNT(*) FROM archivados a JOIN derivaciones d ON d.id=a.derivacion_id WHERE a.carpeta_id=c.id AND d.estado="archivado") AS n FROM carpetas c WHERE c.usuario_id=? ORDER BY c.nombre', [$u['id']]);
        $this->pag('bandeja/archivados', 'Archivados', ['carpetas' => $carpetas]);
    }

    public function desarchivar(): void
    {
        C::desarchivar(Auth::user(), $this->inInt('id'));
        flash('La hoja de ruta volvió a Pendientes.');
        redirect('bandeja/pendientes');
    }

    public function agrupar(): void
    {
        $u = Auth::user();
        $ids = $this->ids();
        if (count($ids) < 2) throw new \RuntimeException('Seleccione al menos 2 hojas de ruta para agrupar.');
        if ($this->in('confirmar') === '1') {
            $g = C::agrupar($u, $ids, $this->inInt('principal'));
            flash('Correspondencia agrupada.');
            redirect('bandeja/agrupacion', ['id' => $g]);
        }
        $sel = DB::all('SELECT d.id, h.nur, h.referencia FROM derivaciones d JOIN hojas_ruta h ON h.id=d.hoja_id WHERE d.a_usuario_id=? AND d.estado="pendiente" AND d.id IN (' . implode(',', array_map('intval', $ids)) . ')', [$u['id']]);
        $this->pag('bandeja/agrupar', 'Agrupar correspondencia', ['sel' => $sel]);
    }

    public function agrupados(): void
    {
        $rows = DB::all('SELECT g.*, hp.nur AS nur_principal, (SELECT COUNT(*) FROM agrupacion_items i WHERE i.agrupacion_id=g.id) AS n
            FROM agrupaciones g JOIN derivaciones dp ON dp.id=g.principal_derivacion_id JOIN hojas_ruta hp ON hp.id=dp.hoja_id WHERE g.usuario_id=? ORDER BY g.id DESC', [Auth::id()]);
        $this->pag('bandeja/agrupados', 'Agrupados', ['rows' => $rows]);
    }

    public function agrupacion(): void
    {
        $g = DB::one('SELECT * FROM agrupaciones WHERE id=? AND usuario_id=?', [$this->inInt('id'), Auth::id()]);
        if (!$g) throw new \RuntimeException('Agrupación no encontrada.');
        $items = DB::all('SELECT d.id, h.nur, h.referencia, (d.id=?) AS principal, (SELECT GROUP_CONCAT(dc.cite SEPARATOR ", ") FROM documentos dc WHERE dc.hoja_id=h.id) AS cites
            FROM agrupacion_items i JOIN derivaciones d ON d.id=i.derivacion_id JOIN hojas_ruta h ON h.id=d.hoja_id WHERE i.agrupacion_id=? ORDER BY principal DESC, h.nur', [$g['principal_derivacion_id'], $g['id']]);
        $this->pag('bandeja/agrupacion', 'Detalle de agrupación', ['g' => $g, 'items' => $items, 'imprimir' => $this->in('imprimir') === '1']);
    }

    /** Cuaderno de derivaciones: imprime las hojas seleccionadas en 6 posiciones por página. */
    public function cuaderno(): void
    {
        $ids = $this->ids();
        if (!$ids) throw new \RuntimeException('Seleccione al menos una derivación enviada.');
        $pos = max(1, min(6, $this->inInt('pos') ?: 1));
        $rows = DB::all('SELECT d.*, h.nur, au.nombre AS a_nombre, au.cargo AS a_cargo, ao.nombre AS a_oficina FROM derivaciones d JOIN hojas_ruta h ON h.id=d.hoja_id
            JOIN usuarios au ON au.id=d.a_usuario_id JOIN oficinas ao ON ao.id=au.oficina_id
            WHERE d.de_usuario_id=? AND d.id IN (' . implode(',', array_map('intval', $ids)) . ') ORDER BY d.fecha_envio', [Auth::id()]);
        $this->view('bandeja/cuaderno', ['rows' => $rows, 'pos' => $pos], 'layout_print');
    }
}
