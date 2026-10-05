<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Audit, Auth, Controller, DB, Uploader};
use App\Services\Correspondencia as C;

final class DocumentoController extends Controller
{
    private function pag(string $tpl, string $titulo, array $d = []): void
    {
        $this->view($tpl, $d + ['menu' => 'documentos', 'titulo' => $titulo]);
    }

    private function propio(int $id): array
    {
        $d = DB::one('SELECT d.*, t.nombre AS tipo, t.prefijo, h.nur FROM documentos d JOIN tipos_documento t ON t.id=d.tipo_id JOIN hojas_ruta h ON h.id=d.hoja_id WHERE d.id=?', [$id]);
        if (!$d) throw new \RuntimeException('Documento no encontrado.');
        return $d;
    }

    public function index(): void
    {
        $this->pag('documento/index', 'Crear nuevo documento', ['tipos' => C::tiposHabilitados(Auth::user()), 'hoja' => $this->inInt('hoja')]);
    }

    public function nuevo(): void
    {
        $u = Auth::user();
        $tipoId = $this->inInt('tipo');
        $tipo = null;
        foreach (C::tiposHabilitados($u) as $t) if ((int)$t['id'] === $tipoId) $tipo = $t;
        if (!$tipo) throw new \RuntimeException('Tipo de documento no habilitado.');
        $hojaId = $this->inInt('hoja') ?: null;
        $nur = $this->in('nur');
        if (!$hojaId && $nur !== '') {
            $hojaId = (int)DB::val('SELECT id FROM hojas_ruta WHERE nur=?', [$nur]) ?: null;
            if (!$hojaId) throw new \RuntimeException("No existe el NUR «$nur».");
        }
        if ($this->esPost()) {
            [$id] = C::crearDocumento($u, $tipoId, $_POST, $hojaId);
            flash('Documento creado. Puede adjuntar archivos y derivarlo.');
            redirect('documento/editar', ['id' => $id]);
        }
        $hoja = $hojaId ? C::hoja($hojaId) : null;
        $this->pag('documento/form', 'Crear ' . $tipo['nombre'], ['tipo' => $tipo, 'doc' => ['referencia' => $hoja['referencia'] ?? ''], 'hoja' => $hoja, 'nuevo' => true]);
    }

    public function editar(): void
    {
        $u = Auth::user();
        $d = $this->propio($this->inInt('id'));
        if ((int)$d['creado_por'] !== (int)$u['id'] && $u['rol'] !== 'admin') throw new \RuntimeException('Solo el autor puede editar el documento.');
        if ($this->esPost()) {
            C::actualizarDocumento($u, (int)$d['id'], $_POST);
            flash('Documento actualizado.');
            redirect('documento/editar', ['id' => $d['id']]);
        }
        $adj = DB::all('SELECT * FROM adjuntos WHERE documento_id=? ORDER BY id', [$d['id']]);
        $this->pag('documento/form', 'Editar ' . $d['cite'], ['tipo' => ['nombre' => $d['tipo']], 'doc' => $d, 'hoja' => C::hoja((int)$d['hoja_id']), 'nuevo' => false, 'adjuntos' => $adj, 'tab' => $this->in('tab', 'edicion')]);
    }

    public function ver(): void
    {
        $u = Auth::user();
        $d = $this->propio($this->inInt('id'));
        if (!C::puedeVer($u, (int)$d['hoja_id'])) throw new \RuntimeException('No tiene acceso a este documento.');
        $adj = DB::all('SELECT * FROM adjuntos WHERE hoja_id=? ORDER BY id', [$d['hoja_id']]);
        $this->view('documento/ver', ['d' => $d, 'adjuntos' => $adj, 'volver' => $this->in('volver')], 'layout_print');
    }

    public function creados(): void
    {
        $u = Auth::user();
        $tipo = $this->inInt('tipo');
        $conteo = DB::all('SELECT t.id, t.nombre, COUNT(d.id) n FROM tipos_documento t LEFT JOIN documentos d ON d.tipo_id=t.id AND d.creado_por=? WHERE t.activo=1 GROUP BY t.id, t.nombre HAVING n>0 ORDER BY t.nombre', [$u['id']]);
        $docs = DB::all('SELECT d.id, d.cite, d.referencia, d.destinatario_nombre, d.destinatario_cargo, d.creado_en, t.nombre AS tipo, h.id AS hoja_id, h.nur
            FROM documentos d JOIN tipos_documento t ON t.id=d.tipo_id JOIN hojas_ruta h ON h.id=d.hoja_id
            WHERE d.creado_por=?' . ($tipo ? ' AND d.tipo_id=' . $tipo : '') . ' ORDER BY d.id DESC LIMIT 100', [$u['id']]);
        $this->pag('documento/creados', 'Documentos creados', ['conteo' => $conteo, 'docs' => $docs, 'tipo' => $tipo]);
    }

    public function archivos(): void
    {
        $rows = DB::all('SELECT a.*, h.nur, d.cite, d.referencia FROM adjuntos a JOIN hojas_ruta h ON h.id=a.hoja_id LEFT JOIN documentos d ON d.id=a.documento_id WHERE a.subido_por=? ORDER BY a.id DESC LIMIT 200', [Auth::id()]);
        $this->pag('documento/archivos', 'Archivos digitales', ['rows' => $rows]);
    }

    public function adjuntar(): void
    {
        $u = Auth::user();
        $d = $this->propio($this->inInt('id'));
        if (!C::puedeVer($u, (int)$d['hoja_id']) || ((int)$d['creado_por'] !== (int)$u['id'] && $u['rol'] !== 'admin')) throw new \RuntimeException('Sin permiso para adjuntar.');
        $n = 0;
        $files = $_FILES['archivos'] ?? null;
        if ($files && is_array($files['name'])) {
            foreach ($files['name'] as $i => $nombre) {
                if ($files['error'][$i] === UPLOAD_ERR_NO_FILE) continue;
                [$orig, $disco, $mime, $tam] = Uploader::guardar(['name' => $nombre, 'tmp_name' => $files['tmp_name'][$i], 'size' => $files['size'][$i], 'error' => $files['error'][$i]]);
                $id = DB::insert('adjuntos', ['hoja_id' => $d['hoja_id'], 'documento_id' => $d['id'], 'nombre_original' => $orig, 'nombre_disco' => $disco, 'mime' => $mime, 'tamano' => $tam, 'subido_por' => $u['id'], 'creado_en' => ahora()]);
                Audit::log('adjuntar', 'adjunto', $id, $orig);
                $n++;
            }
        }
        if (!$n) throw new \RuntimeException('Seleccione al menos un archivo.');
        flash("$n archivo(s) adjuntado(s).");
        redirect('documento/editar', ['id' => $d['id'], 'tab' => 'adjuntos']);
    }

    public function quitar(): void
    {
        $u = Auth::user();
        $a = DB::one('SELECT * FROM adjuntos WHERE id=?', [$this->inInt('id')]);
        if (!$a || ((int)$a['subido_por'] !== (int)$u['id'] && $u['rol'] !== 'admin')) throw new \RuntimeException('Adjunto no encontrado.');
        DB::exec('DELETE FROM adjuntos WHERE id=?', [$a['id']]);
        @unlink(Uploader::dir() . '/' . $a['nombre_disco']);
        Audit::log('quitar_adjunto', 'adjunto', (int)$a['id'], $a['nombre_original']);
        flash('Archivo eliminado.');
        redirect('documento/editar', ['id' => $a['documento_id'], 'tab' => 'adjuntos']);
    }

    public function descargar(): void
    {
        $a = DB::one('SELECT * FROM adjuntos WHERE id=?', [$this->inInt('id')]);
        if (!$a || !C::puedeVer(Auth::user(), (int)$a['hoja_id'])) $this->abort(404, 'Archivo no encontrado.');
        $path = Uploader::dir() . '/' . $a['nombre_disco'];
        if (!is_file($path)) $this->abort(404, 'El archivo ya no existe en el servidor.');
        Audit::log('descargar', 'adjunto', (int)$a['id']);
        $inline = in_array($a['mime'], ['application/pdf', 'image/png', 'image/jpeg'], true) && $this->in('ver') === '1';
        header('Content-Type: ' . $a['mime']);
        header('Content-Length: ' . filesize($path));
        header('Content-Disposition: ' . ($inline ? 'inline' : 'attachment') . '; filename*=UTF-8\'\'' . rawurlencode($a['nombre_original']));
        header("Content-Security-Policy: sandbox");
        readfile($path);
    }

    /** Autocompletado de NUR propios (JSON). */
    public function hojas(): void
    {
        $q = str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $this->in('q'));
        $r = DB::all('SELECT nur, referencia FROM hojas_ruta WHERE creada_por=? AND nur LIKE ? ORDER BY id DESC LIMIT 15', [Auth::id(), "%$q%"]);
        $this->json($r);
    }
}
