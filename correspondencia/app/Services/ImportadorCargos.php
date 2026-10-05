<?php
declare(strict_types=1);
namespace App\Services;

use App\Core\{Audit, DB};

/** Importa oficinas (unidades organizacionales) y un usuario por cargo desde un Excel (.xlsx) o CSV. */
final class ImportadorCargos
{
    private const STOP = ['DE', 'DEL', 'LA', 'LAS', 'LOS', 'EL', 'Y', 'E'];
    private const ALFABETO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';

    // ---------- Lectura ----------

    /** @return list<list<string>> filas crudas */
    public static function leer(string $ruta, string $nombre): array
    {
        $ext = strtolower(pathinfo($nombre, PATHINFO_EXTENSION));
        if ($ext === 'xlsx') return self::leerXlsx($ruta);
        if (in_array($ext, ['csv', 'txt'], true)) return self::leerCsv($ruta);
        throw new \RuntimeException('Formato no admitido. Suba un archivo Excel (.xlsx) o CSV.');
    }

    private static function leerXlsx(string $ruta): array
    {
        if (!class_exists(\ZipArchive::class)) throw new \RuntimeException('Este servidor no tiene la extensión ZIP de PHP. Guarde el Excel como CSV y súbalo.');
        $zip = new \ZipArchive();
        if ($zip->open($ruta) !== true) throw new \RuntimeException('No se pudo abrir el Excel; ¿está dañado?');
        $textos = [];
        if (($x = $zip->getFromName('xl/sharedStrings.xml')) !== false) {
            $d = new \DOMDocument(); $d->loadXML($x);
            foreach ($d->getElementsByTagName('si') as $si) {
                $t = '';
                foreach ($si->getElementsByTagName('t') as $n) $t .= $n->textContent;
                $textos[] = $t;
            }
        }
        $hoja = $zip->getFromName('xl/worksheets/sheet1.xml');
        $zip->close();
        if ($hoja === false) throw new \RuntimeException('No se encontró la primera hoja del Excel.');
        $d = new \DOMDocument(); $d->loadXML($hoja);
        $filas = [];
        foreach ($d->getElementsByTagName('row') as $row) {
            $fila = [];
            foreach ($row->getElementsByTagName('c') as $c) {
                $col = self::columna($c->getAttribute('r'));
                $t = $c->getAttribute('t');
                $v = $c->getElementsByTagName('v')->item(0);
                if ($t === 'inlineStr') { $val = $c->textContent; }
                elseif ($v === null) { $val = ''; }
                else { $val = $t === 's' ? ($textos[(int)$v->textContent] ?? '') : $v->textContent; }
                $fila[$col] = trim($val);
            }
            if ($fila) { $max = max(array_keys($fila)); $f = []; for ($i = 0; $i <= $max; $i++) $f[] = $fila[$i] ?? ''; $filas[] = $f; }
        }
        return $filas;
    }

    private static function columna(string $ref): int
    {
        preg_match('/^[A-Z]+/', $ref, $m);
        $n = 0;
        foreach (str_split($m[0] ?? 'A') as $ch) $n = $n * 26 + (ord($ch) - 64);
        return $n - 1;
    }

    private static function leerCsv(string $ruta): array
    {
        $txt = (string)file_get_contents($ruta);
        if (str_starts_with($txt, "\xEF\xBB\xBF")) $txt = substr($txt, 3);
        if (!mb_check_encoding($txt, 'UTF-8')) $txt = mb_convert_encoding($txt, 'UTF-8', 'Windows-1252');
        $sep = substr_count($txt, ';') > substr_count($txt, ',') ? ';' : ',';
        $filas = [];
        $h = fopen('php://memory', 'r+'); fwrite($h, $txt); rewind($h);
        while (($r = fgetcsv($h, 0, $sep)) !== false) $filas[] = array_map('trim', $r);
        fclose($h);
        return $filas;
    }

    // ---------- Normalización ----------

    public static function limpiar(string $s): string
    {
        return mb_strtoupper(trim(preg_replace('/\s+/u', ' ', $s)), 'UTF-8');
    }

    public static function norm(string $s): string
    {
        $s = strtr(self::limpiar($s), ['Á' => 'A', 'É' => 'E', 'Í' => 'I', 'Ó' => 'O', 'Ú' => 'U', 'Ü' => 'U', 'Ñ' => 'N']);
        return trim(preg_replace('/[^A-Z0-9 ]+/', ' ', $s));
    }

    private static function palabras(string $s): array { return array_values(array_filter(explode(' ', preg_replace('/\s+/', ' ', self::norm($s))))); }

    private static function truncada(string $u): bool
    {
        $p = self::palabras($u);
        return $p && in_array(end($p), self::STOP, true);
    }

    private static function prefijoComun(array $a, array $b): int
    {
        $n = 0;
        while ($n < min(count($a), count($b)) && $a[$n] === $b[$n]) $n++;
        return $n;
    }

    // ---------- Planificación (vista previa, sin escribir) ----------

    /** @return array{filas:list<array>,oficinas:list<array>,usuarios:list<array>,avisos:list<string>} */
    public static function planificar(array $crudas): array
    {
        $avisos = [];
        // Cabecera
        $iItem = $iUni = $iCar = null; $inicio = 0;
        foreach ($crudas as $n => $f) {
            foreach ($f as $i => $c) {
                $c = self::norm((string)$c);
                if ($c === 'ITEM') $iItem = $i;
                if (str_starts_with($c, 'UNIDAD')) $iUni = $i;
                if (str_starts_with($c, 'PUESTO') || $c === 'CARGO') $iCar = $i;
            }
            if ($iUni !== null && $iCar !== null) { $inicio = $n + 1; break; }
        }
        if ($iUni === null || $iCar === null) throw new \RuntimeException('No se encontraron las columnas "UNIDAD ORGANIZACIONAL" y "Puesto Organizacional" (o "Cargo") en la primera hoja.');
        $filas = [];
        foreach (array_slice($crudas, $inicio) as $f) {
            $u = self::limpiar((string)($f[$iUni] ?? '')); $c = self::limpiar((string)($f[$iCar] ?? ''));
            if ($u === '' || $c === '') continue;
            $item = $iItem !== null ? preg_replace('/\D/', '', (string)($f[$iItem] ?? '')) : '';
            $filas[] = ['item' => $item, 'unidad' => $u, 'cargo' => $c];
        }
        if (!$filas) throw new \RuntimeException('El archivo no tiene filas con unidad y cargo.');

        // Unidades: unir nombres truncados
        $unidades = array_values(array_unique(array_column($filas, 'unidad')));
        $mapa = [];
        foreach ($unidades as $u) {
            $mapa[$u] = $u;
            if (!self::truncada($u)) continue;
            foreach ($unidades as $v) {
                if ($v !== $u && !self::truncada($v) && self::prefijoComun(self::palabras($u), self::palabras($v)) >= 4) {
                    $mapa[$u] = $v; $avisos[] = "La unidad «{$u}» parece estar cortada; se unió a «{$v}».";
                    continue 2;
                }
            }
            foreach ($filas as $f) {   // completar usando el cargo del Secretario
                if ($f['unidad'] === $u && preg_match('/^SECRETARIO MUNICIPAL (.+)$/u', $f['cargo'], $m)) {
                    $cand = 'SECRETARÍA MUNICIPAL ' . $m[1];
                    if (str_starts_with(self::norm($cand), self::norm($u))) { $mapa[$u] = $cand; $avisos[] = "El nombre «{$u}» estaba cortado; se completó como «{$cand}» (puede editarlo luego)."; }
                    break;
                }
            }
        }
        foreach ($filas as &$f) $f['unidad'] = $mapa[$f['unidad']];
        unset($f);

        // Oficinas
        $existentes = [];
        foreach (DB::all('SELECT id, nombre, sigla FROM oficinas') as $o) $existentes[self::norm($o['nombre'])] = $o;
        $siglas = array_column(DB::all('SELECT sigla FROM oficinas'), 'sigla');
        $oficinas = [];
        foreach (array_values(array_unique(array_column($filas, 'unidad'))) as $u) {
            if (isset($existentes[self::norm($u)])) { $oficinas[] = ['nombre' => $u, 'sigla' => $existentes[self::norm($u)]['sigla'], 'existe' => true]; continue; }
            $s = self::sigla($u); $base = $s; $k = 2;
            while (in_array($s, $siglas, true)) $s = $base . $k++;
            $siglas[] = $s;
            $oficinas[] = ['nombre' => $u, 'sigla' => $s, 'existe' => false];
        }

        // Usuarios
        $jefes = []; $alcalde = null;
        foreach ($filas as $f) {
            $login = $f['item'] !== '' ? 'u' . $f['item'] : null;
            if (!$login) throw new \RuntimeException('Hay filas sin número de Ítem; se necesita para crear el usuario.');
            if (preg_match('/^ALCALDE\b/u', $f['cargo'])) $alcalde = $login;
            if (preg_match('/^SECRETARIO MUNICIPAL\b/u', $f['cargo'])) $jefes[$f['unidad']] = $login;
            if (preg_match('/^ALCALDE\b/u', $f['cargo'])) $jefes[$f['unidad']] = $login;
        }
        $usuarios = []; $vistos = [];
        foreach ($filas as $f) {
            $login = 'u' . $f['item'];
            if (isset($vistos[$login])) { $avisos[] = "El Ítem {$f['item']} está repetido; se omitió «{$f['cargo']}»."; continue; }
            $vistos[$login] = true;
            $esAlc = (bool)preg_match('/^ALCALDE\b/u', $f['cargo']);
            $esSec = (bool)preg_match('/^SECRETARIO MUNICIPAL\b/u', $f['cargo']);
            $rol = ($esAlc || $esSec) ? 'jefe' : (preg_match('/^RESPONSABLE DE ARCHIVO\b/u', $f['cargo']) ? 'ventanilla' : 'usuario');
            $jefe = $esAlc ? null : ($esSec ? $alcalde : ($jefes[$f['unidad']] ?? $alcalde));
            if ($jefe === $login) $jefe = null;
            $usuarios[] = ['item' => $f['item'], 'login' => $login, 'unidad' => $f['unidad'], 'cargo' => $f['cargo'], 'rol' => $rol, 'jefe' => $jefe,
                'existe' => (bool)DB::val('SELECT 1 FROM usuarios WHERE login=?', [$login])];
        }
        if (!$alcalde) $avisos[] = 'No se encontró un cargo "ALCALDE…": los usuarios no tendrán jefe superior asignado.';
        return ['oficinas' => $oficinas, 'usuarios' => $usuarios, 'avisos' => $avisos];
    }

    public static function sigla(string $unidad): string
    {
        $p = array_values(array_filter(self::palabras($unidad), fn($w) => !in_array($w, self::STOP, true)));
        $s = '';
        foreach ($p as $w) $s .= $w[0];
        return substr($s ?: 'OF', 0, 12);
    }

    // ---------- Aplicación ----------

    /** Crea oficinas y usuarios nuevos. Devuelve las credenciales temporales de los usuarios creados. */
    public static function aplicar(array $plan): array
    {
        return DB::tx(function () use ($plan) {
            $ids = [];
            foreach ($plan['oficinas'] as $o) {
                $ids[$o['nombre']] = $o['existe']
                    ? (int)DB::val('SELECT id FROM oficinas WHERE sigla=?', [$o['sigla']])
                    : DB::insert('oficinas', ['nombre' => mb_substr($o['nombre'], 0, 150), 'sigla' => $o['sigla'], 'activa' => 1]);
            }
            $cred = [];
            foreach ($plan['usuarios'] as $u) {
                if (DB::val('SELECT 1 FROM usuarios WHERE login=?', [$u['login']])) continue;
                $clave = self::claveTemporal();
                DB::insert('usuarios', [
                    'login' => $u['login'], 'nombre' => 'Por asignar', 'cargo' => mb_substr($u['cargo'], 0, 150), 'mosca' => '', 'oficina_id' => $ids[$u['unidad']],
                    'rol' => $u['rol'], 'password_hash' => password_hash($clave, PASSWORD_DEFAULT), 'cambiar_clave' => 1,
                ]);
                $cred[] = ['oficina' => $u['unidad'], 'cargo' => $u['cargo'], 'login' => $u['login'], 'clave' => $clave];
            }
            foreach ($plan['usuarios'] as $u) {
                if ($u['jefe']) DB::exec('UPDATE usuarios SET jefe_id=(SELECT x.id FROM (SELECT id FROM usuarios WHERE login=?) x) WHERE login=? AND jefe_id IS NULL', [$u['jefe'], $u['login']]);
            }
            Audit::log('importar_cargos', 'usuario', null, count($cred) . ' usuarios creados');
            return $cred;
        });
    }

    public static function claveTemporal(): string
    {
        $c = '';
        for ($i = 0; $i < 8; $i++) $c .= self::ALFABETO[random_int(0, strlen(self::ALFABETO) - 1)];
        return $c;
    }
}
