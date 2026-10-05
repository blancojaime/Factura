<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Audit, Auth, Controller, DB};

final class AdminController extends Controller
{
    protected array $roles = ['oficinas' => ['admin'], 'oficina' => ['admin'], 'usuarios' => ['admin'], 'usuario' => ['admin'], 'tipos' => ['admin'], 'tipo' => ['admin'], 'auditoria' => ['admin']];

    private function pag(string $tpl, string $titulo, array $d = []): void
    {
        $this->view($tpl, $d + ['menu' => 'admin', 'titulo' => $titulo]);
    }

    public function oficinas(): void
    {
        $this->pag('admin/oficinas', 'Oficinas', ['rows' => DB::all('SELECT o.*, p.nombre AS padre, (SELECT COUNT(*) FROM usuarios u WHERE u.oficina_id=o.id AND u.activo=1) AS n FROM oficinas o LEFT JOIN oficinas p ON p.id=o.padre_id ORDER BY o.nombre')]);
    }

    public function oficina(): void
    {
        $id = $this->inInt('id');
        $o = $id ? DB::one('SELECT * FROM oficinas WHERE id=?', [$id]) : ['id' => 0, 'nombre' => '', 'sigla' => '', 'padre_id' => null, 'activa' => 1];
        if (!$o) throw new \RuntimeException('Oficina no encontrada.');
        if ($this->esPost()) {
            $d = ['nombre' => mb_substr($this->in('nombre'), 0, 150), 'sigla' => strtoupper(mb_substr($this->in('sigla'), 0, 20)), 'padre_id' => $this->inInt('padre_id') ?: null, 'activa' => $this->in('activa') === '1' ? 1 : 0];
            if ($d['nombre'] === '' || !preg_match('/^[A-Z0-9._-]{1,20}$/', $d['sigla'])) throw new \RuntimeException('Nombre y sigla (letras/números, sin espacios) son obligatorios.');
            if (DB::val('SELECT 1 FROM oficinas WHERE sigla=? AND id<>?', [$d['sigla'], $id])) throw new \RuntimeException('Ya existe una oficina con esa sigla.');
            if ($id) { DB::update('oficinas', $id, $d); } else { $id = DB::insert('oficinas', $d); }
            Audit::log('guardar_oficina', 'oficina', $id);
            flash('Oficina guardada.');
            redirect('admin/oficinas');
        }
        $this->pag('admin/oficina', $id ? 'Editar oficina' : 'Nueva oficina', ['o' => $o, 'padres' => DB::all('SELECT id, nombre FROM oficinas WHERE id<>? ORDER BY nombre', [$id])]);
    }

    public function usuarios(): void
    {
        $this->pag('admin/usuarios', 'Usuarios', ['rows' => DB::all('SELECT u.*, o.nombre AS oficina, j.nombre AS jefe FROM usuarios u JOIN oficinas o ON o.id=u.oficina_id LEFT JOIN usuarios j ON j.id=u.jefe_id ORDER BY o.nombre, u.nombre')]);
    }

    public function usuario(): void
    {
        $id = $this->inInt('id');
        $u = $id ? DB::one('SELECT * FROM usuarios WHERE id=?', [$id]) : ['id' => 0, 'login' => '', 'nombre' => '', 'cargo' => '', 'mosca' => '', 'email' => '', 'genero' => 'M', 'oficina_id' => 0, 'jefe_id' => null, 'rol' => 'usuario', 'activo' => 1];
        if (!$u) throw new \RuntimeException('Usuario no encontrado.');
        if ($this->esPost()) {
            $d = [
                'nombre' => mb_substr($this->in('nombre'), 0, 120), 'cargo' => mb_substr($this->in('cargo'), 0, 150), 'mosca' => mb_substr($this->in('mosca'), 0, 10),
                'email' => $this->in('email'), 'genero' => $this->in('genero') === 'F' ? 'F' : 'M', 'oficina_id' => $this->inInt('oficina_id'),
                'jefe_id' => $this->inInt('jefe_id') ?: null,
                'rol' => in_array($this->in('rol'), ['admin', 'jefe', 'usuario', 'ventanilla'], true) ? $this->in('rol') : 'usuario',
                'activo' => $this->in('activo') === '1' ? 1 : 0,
            ];
            if ($d['nombre'] === '' || !DB::val('SELECT 1 FROM oficinas WHERE id=?', [$d['oficina_id']])) throw new \RuntimeException('Nombre y oficina son obligatorios.');
            if ($d['email'] !== '' && !filter_var($d['email'], FILTER_VALIDATE_EMAIL)) throw new \RuntimeException('Correo inválido.');
            if ($id && $d['jefe_id'] === $id) throw new \RuntimeException('Un usuario no puede ser su propio jefe.');
            if ($id === Auth::id() && (!$d['activo'] || $d['rol'] !== 'admin')) throw new \RuntimeException('No puede desactivarse ni quitarse el rol de administrador a sí mismo.');
            $pass = (string)($_POST['password'] ?? '');
            if ($id) {
                if ($pass !== '') { if (mb_strlen($pass) < 8) throw new \RuntimeException('La contraseña debe tener al menos 8 caracteres.'); $d['password_hash'] = password_hash($pass, PASSWORD_DEFAULT); }
                DB::update('usuarios', $id, $d);
            } else {
                $login = $this->in('login');
                if (!preg_match('/^[A-Za-z0-9_.-]{3,60}$/', $login)) throw new \RuntimeException('Usuario inválido (3-60 caracteres: letras, números, . _ -).');
                if (DB::val('SELECT 1 FROM usuarios WHERE login=?', [$login])) throw new \RuntimeException('Ese nombre de usuario ya existe.');
                if (mb_strlen($pass) < 8) throw new \RuntimeException('La contraseña debe tener al menos 8 caracteres.');
                $id = DB::insert('usuarios', $d + ['login' => $login, 'password_hash' => password_hash($pass, PASSWORD_DEFAULT)]);
            }
            Audit::log('guardar_usuario', 'usuario', $id);
            flash('Usuario guardado.');
            redirect('admin/usuarios');
        }
        $this->pag('admin/usuario', $id ? 'Editar usuario' : 'Nuevo usuario', ['u' => $u, 'oficinas' => DB::all('SELECT id, nombre FROM oficinas WHERE activa=1 ORDER BY nombre'), 'jefes' => DB::all('SELECT id, nombre, cargo FROM usuarios WHERE activo=1 AND id<>? ORDER BY nombre', [$id])]);
    }

    public function tipos(): void
    {
        $this->pag('admin/tipos', 'Tipos de documento', ['rows' => DB::all('SELECT t.*, (SELECT COUNT(*) FROM tipos_documento_oficina x WHERE x.tipo_id=t.id) AS restringido FROM tipos_documento t ORDER BY t.nombre')]);
    }

    public function tipo(): void
    {
        $id = $this->inInt('id');
        $t = $id ? DB::one('SELECT * FROM tipos_documento WHERE id=?', [$id]) : ['id' => 0, 'nombre' => '', 'prefijo' => '', 'activo' => 1];
        if (!$t) throw new \RuntimeException('Tipo no encontrado.');
        if ($this->esPost()) {
            $d = ['nombre' => mb_substr($this->in('nombre'), 0, 80), 'prefijo' => strtoupper(mb_substr($this->in('prefijo'), 0, 10)), 'activo' => $this->in('activo') === '1' ? 1 : 0];
            if ($d['nombre'] === '' || !preg_match('/^[A-Z0-9]{1,10}$/', $d['prefijo'])) throw new \RuntimeException('Nombre y prefijo (letras/números) son obligatorios.');
            if (DB::val('SELECT 1 FROM tipos_documento WHERE prefijo=? AND id<>?', [$d['prefijo'], $id])) throw new \RuntimeException('Ya existe un tipo con ese prefijo.');
            DB::tx(function () use (&$id, $d) {
                if ($id) { DB::update('tipos_documento', $id, $d); } else { $id = DB::insert('tipos_documento', $d); }
                DB::exec('DELETE FROM tipos_documento_oficina WHERE tipo_id=?', [$id]);
                foreach ($this->ids('oficinas') as $of) DB::insert('tipos_documento_oficina', ['tipo_id' => $id, 'oficina_id' => $of]);
            });
            flash('Tipo de documento guardado.');
            redirect('admin/tipos');
        }
        $sel = $id ? array_column(DB::all('SELECT oficina_id FROM tipos_documento_oficina WHERE tipo_id=?', [$id]), 'oficina_id') : [];
        $this->pag('admin/tipo', $id ? 'Editar tipo' : 'Nuevo tipo', ['t' => $t, 'oficinas' => DB::all('SELECT id, nombre FROM oficinas WHERE activa=1 ORDER BY nombre'), 'sel' => array_map('intval', $sel)]);
    }

    public function auditoria(): void
    {
        $uid = $this->inInt('usuario');
        $rows = DB::all('SELECT a.*, u.login FROM auditoria a LEFT JOIN usuarios u ON u.id=a.usuario_id' . ($uid ? ' WHERE a.usuario_id=' . $uid : '') . ' ORDER BY a.id DESC LIMIT 300');
        $this->pag('admin/auditoria', 'Auditoría', ['rows' => $rows, 'usuarios' => DB::all('SELECT id, login FROM usuarios ORDER BY login'), 'uid' => $uid]);
    }
}
