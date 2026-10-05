<?php
declare(strict_types=1);
namespace App\Services;

use App\Core\Audit;
use App\Core\DB;
use App\Core\Sanitizer;

/** Reglas de negocio de documentos, hojas de ruta y derivaciones. Lanza \RuntimeException con mensajes para el usuario. */
final class Correspondencia
{
    // ---------- Acceso ----------

    public static function hoja(int $id): array
    {
        $h = DB::one('SELECT * FROM hojas_ruta WHERE id=?', [$id]);
        if (!$h) throw new \RuntimeException('Hoja de ruta no encontrada.');
        return $h;
    }

    /** ¿El usuario puede consultar esta hoja (seguimiento, documentos, adjuntos)? */
    public static function puedeVer(array $u, int $hojaId): bool
    {
        if ($u['rol'] === 'admin') return true;
        return (bool)DB::val(
            'SELECT 1 FROM hojas_ruta h WHERE h.id=:h AND (
               h.creada_por=:u
               OR EXISTS (SELECT 1 FROM derivaciones d JOIN usuarios x ON x.id IN (d.de_usuario_id, d.a_usuario_id)
                          WHERE d.hoja_id=h.id AND d.estado<>"cancelado" AND (x.id=:u2 OR x.oficina_id=:o))
               OR EXISTS (SELECT 1 FROM documentos dc WHERE dc.hoja_id=h.id AND dc.oficina_id=:o2)
            ) LIMIT 1',
            ['h' => $hojaId, 'u' => $u['id'], 'u2' => $u['id'], 'o' => $u['oficina_id'], 'o2' => $u['oficina_id']]
        );
    }

    /** Derivación pendiente que el usuario tiene actualmente sobre la hoja (la oficial prevalece). */
    public static function tenencia(int $uid, int $hojaId): ?array
    {
        return DB::one(
            "SELECT * FROM derivaciones WHERE hoja_id=? AND a_usuario_id=? AND estado='pendiente' ORDER BY (tipo='oficial') DESC, id DESC LIMIT 1",
            [$hojaId, $uid]
        );
    }

    /** ¿Puede actuar (crear documentos / derivar) sobre la hoja? */
    public static function puedeActuar(array $u, int $hojaId): bool
    {
        $h = self::hoja($hojaId);
        if (self::tenencia((int)$u['id'], $hojaId)) return true;
        if ((int)$h['creada_por'] === (int)$u['id']) {
            // El creador conserva la hoja mientras no haya derivado la oficial.
            return !DB::val("SELECT 1 FROM derivaciones WHERE hoja_id=? AND de_usuario_id=? AND padre_id IS NULL AND tipo='oficial' AND estado<>'cancelado'", [$hojaId, $u['id']]);
        }
        return false;
    }

    // ---------- Hojas de ruta y documentos ----------

    public static function crearHoja(array $u, string $referencia, string $origen = 'interno', array $ext = []): int
    {
        return (int)DB::tx(function () use ($u, $referencia, $origen, $ext) {
            $g = gestion();
            return DB::insert('hojas_ruta', [
                'nur' => Numerador::nur($g), 'gestion' => $g, 'creada_por' => $u['id'], 'referencia' => mb_substr($referencia, 0, 255),
                'origen' => $origen, 'ext_remitente' => $ext['remitente'] ?? null, 'ext_institucion' => $ext['institucion'] ?? null,
                'ext_fojas' => $ext['fojas'] ?? null, 'ext_documento' => $ext['documento'] ?? null,
                'codigo_consulta' => strtoupper(substr(bin2hex(random_bytes(4)), 0, 6)), 'creado_en' => ahora(),
            ]);
        });
    }

    public static function tiposHabilitados(array $u): array
    {
        return DB::all(
            'SELECT t.* FROM tipos_documento t WHERE t.activo=1 AND (
               NOT EXISTS (SELECT 1 FROM tipos_documento_oficina x WHERE x.tipo_id=t.id)
               OR EXISTS (SELECT 1 FROM tipos_documento_oficina x WHERE x.tipo_id=t.id AND x.oficina_id=?)
             ) ORDER BY t.nombre',
            [$u['oficina_id']]
        );
    }

    private static function camposDocumento(array $d): array
    {
        $t = fn($k, $n) => mb_substr(trim((string)($d[$k] ?? '')), 0, $n);
        return [
            'destinatario_nombre' => $t('destinatario_nombre', 150), 'destinatario_cargo' => $t('destinatario_cargo', 150),
            'via_nombre' => $t('via_nombre', 150), 'via_cargo' => $t('via_cargo', 150),
            'adjunto_txt' => $t('adjunto_txt', 255), 'con_copia' => $t('con_copia', 255), 'referencia' => $t('referencia', 255),
            'contenido' => Sanitizer::html((string)($d['contenido'] ?? '')),
        ];
    }

    /** Crea documento; si $hojaId es null genera un NUR nuevo. Devuelve [documento_id, hoja_id]. */
    public static function crearDocumento(array $u, int $tipoId, array $datos, ?int $hojaId = null): array
    {
        $tipo = null;
        foreach (self::tiposHabilitados($u) as $t) if ((int)$t['id'] === $tipoId) $tipo = $t;
        if (!$tipo) throw new \RuntimeException('Tipo de documento no habilitado para su oficina.');
        $c = self::camposDocumento($datos);
        if ($c['referencia'] === '') throw new \RuntimeException('La referencia es obligatoria.');
        if ($c['destinatario_nombre'] === '') throw new \RuntimeException('Indique el destinatario.');

        return DB::tx(function () use ($u, $tipo, $c, $hojaId) {
            if ($hojaId) {
                $h = self::hoja($hojaId);
                $esSuya = (int)$h['creada_por'] === (int)$u['id'];
                if (!$esSuya && !self::tenencia((int)$u['id'], $hojaId) && $u['rol'] !== 'admin') {
                    throw new \RuntimeException('No puede asignar ese NUR: no lo creó ni lo tiene pendiente.');
                }
            } else {
                $hojaId = self::crearHoja($u, $c['referencia']);
            }
            $of = DB::one('SELECT * FROM oficinas WHERE id=?', [$u['oficina_id']]);
            $id = DB::insert('documentos', $c + [
                'hoja_id' => $hojaId, 'tipo_id' => $tipo['id'], 'cite' => Numerador::cite($tipo, $of, gestion()),
                'oficina_id' => $u['oficina_id'], 'creado_por' => $u['id'],
                'remitente_nombre' => $u['nombre'], 'remitente_cargo' => $u['cargo'], 'mosca' => $u['mosca'],
                'creado_en' => ahora(), 'modificado_en' => ahora(),
            ]);
            Audit::log('crear_documento', 'documento', $id);
            return [$id, $hojaId];
        });
    }

    public static function actualizarDocumento(array $u, int $id, array $datos): void
    {
        $d = DB::one('SELECT * FROM documentos WHERE id=?', [$id]);
        if (!$d || ((int)$d['creado_por'] !== (int)$u['id'] && $u['rol'] !== 'admin')) throw new \RuntimeException('Solo el autor puede modificar el documento.');
        $c = self::camposDocumento($datos);
        if ($c['referencia'] === '') throw new \RuntimeException('La referencia es obligatoria.');
        DB::update('documentos', $id, $c + ['modificado_en' => ahora()]);
        Audit::log('editar_documento', 'documento', $id);
    }

    // ---------- Derivación ----------

    /**
     * Deriva la hoja. $tipo: oficial|copia. Devuelve id de derivación creada.
     * Si el usuario tiene una hoja principal de agrupación, se derivan también las agrupadas.
     */
    public static function derivar(array $u, int $hojaId, int $destinoId, string $tipo, string $accion, string $proveido, bool $urgente, string $adjuntoTxt = ''): int
    {
        if (!in_array($tipo, ['oficial', 'copia'], true)) throw new \RuntimeException('Tipo de derivación inválido.');
        if (trim($proveido) === '') throw new \RuntimeException('El proveído es obligatorio.');
        if ($destinoId === (int)$u['id']) throw new \RuntimeException('No puede derivar a sí mismo.');
        $dest = DB::one('SELECT u.id FROM usuarios u JOIN oficinas o ON o.id=u.oficina_id WHERE u.id=? AND u.activo=1 AND o.activa=1', [$destinoId]);
        if (!$dest) throw new \RuntimeException('Destinatario no válido.');

        return (int)DB::tx(function () use ($u, $hojaId, $destinoId, $tipo, $accion, $proveido, $urgente, $adjuntoTxt) {
            $hold = self::tenencia((int)$u['id'], $hojaId);
            if (!$hold && (int)self::hoja($hojaId)['creada_por'] !== (int)$u['id']) throw new \RuntimeException('No tiene esta hoja de ruta para derivarla.');
            $padre = $hold['id'] ?? null;
            if ($tipo === 'oficial' && DB::val(
                "SELECT 1 FROM derivaciones WHERE hoja_id=? AND de_usuario_id=? AND padre_id <=> ? AND tipo='oficial' AND estado<>'cancelado'",
                [$hojaId, $u['id'], $padre]
            )) throw new \RuntimeException('La derivación oficial ya fue realizada; use "Derivar copia" o cancélela primero.');
            if (DB::val("SELECT 1 FROM derivaciones WHERE hoja_id=? AND de_usuario_id=? AND a_usuario_id=? AND padre_id <=> ? AND estado<>'cancelado'", [$hojaId, $u['id'], $destinoId, $padre])) {
                throw new \RuntimeException('Ya derivó esta hoja a ese destinatario.');
            }
            $ts = ahora();
            $id = self::insertarDerivacion($u, $hojaId, $padre, $destinoId, $tipo, $accion, $proveido, $urgente, $adjuntoTxt, $ts);

            // Hojas agrupadas bajo la principal acompañan a la derivación oficial.
            if ($padre && $tipo === 'oficial') {
                $ag = DB::all(
                    "SELECT d.* FROM agrupaciones g JOIN agrupacion_items i ON i.agrupacion_id=g.id JOIN derivaciones d ON d.id=i.derivacion_id
                     WHERE g.principal_derivacion_id=? AND d.estado='agrupado'", [$padre]);
                foreach ($ag as $d) {
                    self::insertarDerivacion($u, (int)$d['hoja_id'], (int)$d['id'], $destinoId, 'oficial', $accion, $proveido, $urgente, $adjuntoTxt, $ts);
                    DB::update('derivaciones', (int)$d['id'], ['estado' => 'derivado']);
                }
            }
            if ($padre && $tipo === 'oficial') DB::update('derivaciones', (int)$padre, ['estado' => 'derivado']);
            Audit::log('derivar', 'hoja', $hojaId, "a usuario $destinoId ($tipo)");
            return $id;
        });
    }

    private static function insertarDerivacion(array $u, int $hoja, ?int $padre, int $dest, string $tipo, string $accion, string $prov, bool $urg, string $adj, string $ts): int
    {
        return DB::insert('derivaciones', [
            'hoja_id' => $hoja, 'padre_id' => $padre, 'de_usuario_id' => $u['id'], 'a_usuario_id' => $dest, 'tipo' => $tipo,
            'accion' => mb_substr($accion, 0, 80), 'adjunto_txt' => mb_substr($adj, 0, 255), 'proveido' => trim($prov),
            'urgente' => $urg ? 1 : 0, 'estado' => 'no_recibido', 'fecha_envio' => $ts,
        ]);
    }

    /** Cancela (paso atrás) una derivación enviada y aún no recibida. */
    public static function cancelar(array $u, int $derivacionId): void
    {
        DB::tx(function () use ($u, $derivacionId) {
            $d = DB::one('SELECT * FROM derivaciones WHERE id=? FOR UPDATE', [$derivacionId]);
            if (!$d || (int)$d['de_usuario_id'] !== (int)$u['id']) throw new \RuntimeException('Derivación no encontrada.');
            if ($d['estado'] !== 'no_recibido') throw new \RuntimeException('El destinatario ya recibió la hoja de ruta; no se puede cancelar.');
            DB::update('derivaciones', $derivacionId, ['estado' => 'cancelado']);
            if ($d['tipo'] === 'oficial' && $d['padre_id']) {
                DB::update('derivaciones', (int)$d['padre_id'], ['estado' => 'pendiente']);
                // Restituye las agrupadas que viajaban con ella.
                foreach (DB::all("SELECT d2.id, d2.padre_id FROM derivaciones d2 WHERE d2.estado='no_recibido' AND d2.de_usuario_id=? AND d2.a_usuario_id=? AND d2.fecha_envio=? AND d2.id<>? AND d2.tipo='oficial'",
                    [$u['id'], $d['a_usuario_id'], $d['fecha_envio'], $derivacionId]) as $x) {
                    if ($x['padre_id']) { DB::update('derivaciones', (int)$x['id'], ['estado' => 'cancelado']); DB::update('derivaciones', (int)$x['padre_id'], ['estado' => 'agrupado']); }
                }
            }
            Audit::log('cancelar_derivacion', 'derivacion', $derivacionId);
        });
    }

    public static function recibir(array $u, array $ids): int
    {
        $n = 0;
        foreach ($ids as $id) {
            $n += DB::exec("UPDATE derivaciones SET estado='pendiente', fecha_recepcion=? WHERE id=? AND a_usuario_id=? AND estado='no_recibido'", [ahora(), $id, $u['id']]);
            Audit::log('recibir', 'derivacion', (int)$id);
        }
        return $n;
    }

    // ---------- Archivo y agrupación ----------

    public static function archivar(array $u, array $ids, int $carpetaId, string $nuevaCarpeta, string $obs): int
    {
        if (!$ids) throw new \RuntimeException('Seleccione al menos una hoja de ruta.');
        return (int)DB::tx(function () use ($u, $ids, $carpetaId, $nuevaCarpeta, $obs) {
            if (trim($nuevaCarpeta) !== '') {
                $nombre = mb_substr(trim($nuevaCarpeta), 0, 100);
                $carpetaId = (int)DB::val('SELECT id FROM carpetas WHERE usuario_id=? AND nombre=?', [$u['id'], $nombre]) ?: DB::insert('carpetas', ['usuario_id' => $u['id'], 'nombre' => $nombre]);
            } elseif (!DB::val('SELECT 1 FROM carpetas WHERE id=? AND usuario_id=?', [$carpetaId, $u['id']])) {
                throw new \RuntimeException('Seleccione o cree una carpeta.');
            }
            $n = 0;
            foreach ($ids as $id) {
                if (!DB::val("SELECT 1 FROM derivaciones WHERE id=? AND a_usuario_id=? AND estado='pendiente'", [$id, $u['id']])) continue;
                DB::update('derivaciones', (int)$id, ['estado' => 'archivado']);
                DB::q('INSERT INTO archivados (derivacion_id, carpeta_id, observacion, fecha) VALUES (?,?,?,?) ON DUPLICATE KEY UPDATE carpeta_id=VALUES(carpeta_id), observacion=VALUES(observacion), fecha=VALUES(fecha)',
                    [$id, $carpetaId, mb_substr(trim($obs), 0, 255), ahora()]);
                Audit::log('archivar', 'derivacion', (int)$id);
                $n++;
            }
            return $n;
        });
    }

    public static function desarchivar(array $u, int $id): void
    {
        DB::tx(function () use ($u, $id) {
            if (!DB::val("SELECT 1 FROM derivaciones WHERE id=? AND a_usuario_id=? AND estado='archivado'", [$id, $u['id']])) throw new \RuntimeException('Elemento no encontrado.');
            DB::update('derivaciones', $id, ['estado' => 'pendiente']);
            DB::exec('DELETE FROM archivados WHERE derivacion_id=?', [$id]);
            Audit::log('desarchivar', 'derivacion', $id);
        });
    }

    public static function agrupar(array $u, array $ids, int $principalId): int
    {
        if (count($ids) < 2) throw new \RuntimeException('Seleccione al menos 2 hojas de ruta para agrupar.');
        if (!in_array($principalId, $ids, true)) throw new \RuntimeException('Elija cuál será la hoja principal.');
        return (int)DB::tx(function () use ($u, $ids, $principalId) {
            foreach ($ids as $id) {
                if (!DB::val("SELECT 1 FROM derivaciones WHERE id=? AND a_usuario_id=? AND estado='pendiente'", [$id, $u['id']])) {
                    throw new \RuntimeException('Solo se pueden agrupar hojas de ruta pendientes propias.');
                }
            }
            $g = DB::insert('agrupaciones', ['usuario_id' => $u['id'], 'principal_derivacion_id' => $principalId, 'creada_en' => ahora()]);
            foreach ($ids as $id) {
                DB::insert('agrupacion_items', ['agrupacion_id' => $g, 'derivacion_id' => $id]);
                if ((int)$id !== $principalId) DB::update('derivaciones', (int)$id, ['estado' => 'agrupado']);
            }
            Audit::log('agrupar', 'agrupacion', $g);
            return $g;
        });
    }

    // ---------- Consultas ----------

    private const SELECT_BANDEJA = "SELECT d.*, h.nur, h.referencia, h.origen, h.ext_remitente, h.ext_institucion,
        ru.nombre AS de_nombre, ru.cargo AS de_cargo, ro.nombre AS de_oficina,
        au.nombre AS a_nombre, au.cargo AS a_cargo, ao.nombre AS a_oficina,
        (SELECT GROUP_CONCAT(dc.cite SEPARATOR ', ') FROM documentos dc WHERE dc.hoja_id=h.id) AS cites,
        (SELECT MIN(dc2.id) FROM documentos dc2 WHERE dc2.hoja_id=h.id) AS primer_doc,
        (SELECT COUNT(*) FROM adjuntos aj WHERE aj.hoja_id=h.id) AS n_adjuntos
        FROM derivaciones d JOIN hojas_ruta h ON h.id=d.hoja_id
        JOIN usuarios ru ON ru.id=d.de_usuario_id JOIN oficinas ro ON ro.id=ru.oficina_id
        JOIN usuarios au ON au.id=d.a_usuario_id JOIN oficinas ao ON ao.id=au.oficina_id";

    private static function orden(string $o): string
    {
        return ['hr' => 'h.nur ASC', 'fecha' => 'd.fecha_envio DESC', 'oficina' => 'ro.nombre ASC, d.fecha_envio DESC', 'proceso' => 'h.referencia ASC'][$o] ?? 'd.urgente DESC, d.fecha_envio DESC';
    }

    public static function entrada(int $uid, string $orden = ''): array
    {
        return DB::all(self::SELECT_BANDEJA . " WHERE d.a_usuario_id=? AND d.estado='no_recibido' ORDER BY " . self::orden($orden), [$uid]);
    }

    public static function pendientes(int $uid, string $mostrar = 'todo', string $orden = ''): array
    {
        $f = $mostrar === 'oficial' ? " AND d.tipo='oficial'" : ($mostrar === 'copia' ? " AND d.tipo='copia'" : '');
        return DB::all(self::SELECT_BANDEJA . " WHERE d.a_usuario_id=? AND d.estado='pendiente'$f ORDER BY " . self::orden($orden), [$uid]);
    }

    public static function enviados(int $uid): array
    {
        return DB::all(self::SELECT_BANDEJA . " WHERE d.de_usuario_id=? AND d.estado='no_recibido' ORDER BY d.fecha_envio DESC", [$uid]);
    }

    public static function contadores(int $uid): array
    {
        $r = DB::all('SELECT estado, COUNT(*) n FROM derivaciones WHERE a_usuario_id=? GROUP BY estado', [$uid]);
        $c = ['no_recibido' => 0, 'pendiente' => 0, 'archivado' => 0, 'agrupado' => 0];
        foreach ($r as $x) $c[$x['estado']] = (int)$x['n'];
        $c['grupos'] = (int)DB::val('SELECT COUNT(*) FROM agrupaciones WHERE usuario_id=?', [$uid]);
        return $c;
    }

    /** Línea de tiempo completa de una hoja. */
    public static function seguimiento(int $hojaId): array
    {
        return DB::all(self::SELECT_BANDEJA . " WHERE d.hoja_id=? AND d.estado<>'cancelado' ORDER BY d.id", [$hojaId]);
    }
}
