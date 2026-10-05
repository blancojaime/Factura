<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Audit, Auth, Controller, DB, Uploader};
use App\Services\Correspondencia as C;

/** Ventanilla única: registro de correspondencia externa (ciudadanos, comunidades, instituciones). */
final class VentanillaController extends Controller
{
    protected array $roles = ['index' => ['admin', 'ventanilla'], 'nueva' => ['admin', 'ventanilla'], 'cargo' => ['admin', 'ventanilla']];

    public function index(): void
    {
        $rows = DB::all("SELECT h.*, (SELECT COUNT(*) FROM derivaciones d WHERE d.hoja_id=h.id AND d.estado<>'cancelado') AS derivaciones FROM hojas_ruta h WHERE h.origen='externo' ORDER BY h.id DESC LIMIT 100");
        $this->view('ventanilla/index', ['menu' => 'ventanilla', 'titulo' => 'Correspondencia externa', 'rows' => $rows]);
    }

    public function nueva(): void
    {
        $u = Auth::user();
        if ($this->esPost()) {
            $remitente = $this->in('remitente');
            if ($remitente === '') throw new \RuntimeException('Indique el nombre del remitente.');
            if ($this->inInt('destino') === 0) throw new \RuntimeException('Seleccione el destinatario.');
            $dest = DB::one('SELECT id, nombre, cargo FROM usuarios WHERE id=? AND activo=1', [$this->inInt('destino')]);
            if (!$dest) throw new \RuntimeException('Destinatario no válido.');
            $tipoExt = (int)DB::val("SELECT id FROM tipos_documento WHERE prefijo='EXT'");
            $institucion = $this->in('institucion');
            $contenido = '<p><strong>Remitente:</strong> ' . e($remitente) . ($institucion ? ' (' . e($institucion) . ')' : '') . '</p>'
                . '<p><strong>Documento:</strong> ' . e($this->in('documento')) . ' — <strong>Fojas:</strong> ' . e($this->in('fojas')) . '</p>'
                . ($this->in('observaciones') !== '' ? '<p>' . nl2br(e($this->in('observaciones'))) . '</p>' : '');
            $hojaId = DB::tx(function () use ($u, $dest, $tipoExt, $contenido, $remitente, $institucion) {
                [$docId, $hojaId] = C::crearDocumento($u, $tipoExt, [
                    'destinatario_nombre' => $dest['nombre'], 'destinatario_cargo' => $dest['cargo'], 'referencia' => $this->in('referencia'), 'contenido' => $contenido,
                ]);
                DB::update('hojas_ruta', $hojaId, ['origen' => 'externo', 'ext_remitente' => mb_substr($remitente, 0, 150), 'ext_institucion' => mb_substr($institucion, 0, 150), 'ext_fojas' => mb_substr($this->in('fojas'), 0, 30), 'ext_documento' => mb_substr($this->in('documento'), 0, 120)]);
                $files = $_FILES['archivos'] ?? null;
                if ($files && is_array($files['name'])) {
                    foreach ($files['name'] as $i => $nombre) {
                        if ($files['error'][$i] === UPLOAD_ERR_NO_FILE) continue;
                        [$orig, $disco, $mime, $tam] = Uploader::guardar(['name' => $nombre, 'tmp_name' => $files['tmp_name'][$i], 'size' => $files['size'][$i], 'error' => $files['error'][$i]]);
                        DB::insert('adjuntos', ['hoja_id' => $hojaId, 'documento_id' => $docId, 'nombre_original' => $orig, 'nombre_disco' => $disco, 'mime' => $mime, 'tamano' => $tam, 'subido_por' => $u['id'], 'creado_en' => ahora()]);
                    }
                }
                C::derivar($u, $hojaId, (int)$dest['id'], 'oficial', 'Acción Necesaria', $this->in('proveido') ?: 'Correspondencia externa recibida en ventanilla', $this->in('urgente') === '1');
                Audit::log('ventanilla', 'hoja', $hojaId);
                return $hojaId;
            });
            flash('Correspondencia externa registrada y derivada.');
            redirect('ventanilla/cargo', ['id' => $hojaId]);
        }
        $this->view('ventanilla/nueva', ['menu' => 'ventanilla', 'titulo' => 'Registrar correspondencia externa']);
    }

    public function cargo(): void
    {
        $h = C::hoja($this->inInt('id'));
        if ($h['origen'] !== 'externo') throw new \RuntimeException('Esta hoja no es de correspondencia externa.');
        $der = DB::one("SELECT d.*, au.nombre, au.cargo, ao.nombre AS oficina FROM derivaciones d JOIN usuarios au ON au.id=d.a_usuario_id JOIN oficinas ao ON ao.id=au.oficina_id WHERE d.hoja_id=? AND d.estado<>'cancelado' ORDER BY d.id LIMIT 1", [$h['id']]);
        $this->view('ventanilla/cargo', ['h' => $h, 'der' => $der], 'layout_print');
    }
}
