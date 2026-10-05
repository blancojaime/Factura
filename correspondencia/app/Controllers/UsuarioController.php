<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Audit, Auth, Controller, DB};

final class UsuarioController extends Controller
{
    public function password(): void
    {
        $u = Auth::user();
        if ($this->esPost()) {
            $nueva = (string)($_POST['nueva'] ?? '');
            if (!password_verify((string)($_POST['actual'] ?? ''), $u['password_hash'])) throw new \RuntimeException('La contraseña actual no es correcta.');
            if (mb_strlen($nueva) < 8) throw new \RuntimeException('La nueva contraseña debe tener al menos 8 caracteres.');
            if ($nueva !== (string)($_POST['repite'] ?? '')) throw new \RuntimeException('La confirmación no coincide.');
            if (password_verify($nueva, $u['password_hash'])) throw new \RuntimeException('La nueva contraseña debe ser distinta de la actual.');
            DB::update('usuarios', (int)$u['id'], ['password_hash' => password_hash($nueva, PASSWORD_DEFAULT), 'cambiar_clave' => 0]);
            Audit::log('cambiar_password', 'usuario', (int)$u['id']);
            flash('Contraseña actualizada.');
            redirect('dashboard/index');
        }
        $this->view('usuario/password', ['menu' => 'usuario', 'titulo' => 'Cambiar contraseña']);
    }

    public function datos(): void
    {
        $u = Auth::user();
        if ($this->esPost()) {
            $nombre = $this->in('nombre');
            if ($nombre === '') throw new \RuntimeException('El nombre es obligatorio.');
            $email = $this->in('email');
            if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) throw new \RuntimeException('Correo electrónico inválido.');
            DB::update('usuarios', (int)$u['id'], [
                'nombre' => mb_substr($nombre, 0, 120), 'cargo' => mb_substr($this->in('cargo'), 0, 150), 'mosca' => mb_substr($this->in('mosca'), 0, 10),
                'email' => $email, 'genero' => $this->in('genero') === 'F' ? 'F' : 'M',
            ]);
            flash('Datos actualizados.');
            redirect('usuario/datos');
        }
        $this->view('usuario/datos', ['menu' => 'usuario', 'titulo' => 'Cambiar mis datos', 'u' => $u]);
    }

    public function info(): void
    {
        $this->view('usuario/info', ['menu' => 'usuario', 'titulo' => 'Información del usuario', 'u' => Auth::user()]);
    }
}
