<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\{Auth, Controller};

final class AuthController extends Controller
{
    protected array $publicas = ['login'];

    public function login(): void
    {
        if (Auth::user()) redirect('dashboard/index');
        $error = '';
        if ($this->esPost()) {
            $error = Auth::login($this->in('login'), (string)($_POST['password'] ?? '')) ?? '';
            if ($error === '') redirect('dashboard/index');
        }
        $this->view('auth/login', ['error' => $error, 'login' => $this->in('login')], 'layout_simple');
    }

    public function salir(): void
    {
        if (!$this->esPost()) redirect('dashboard/index');
        Auth::logout();
        redirect('auth/login');
    }
}
