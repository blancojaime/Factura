<?php
declare(strict_types=1);
namespace App\Core;

abstract class Controller
{
    /** Roles requeridos por acción: ['accion' => ['admin']]. Vacío = cualquier usuario autenticado. */
    protected array $publicas = [];
    protected array $roles = [];

    protected function view(string $tpl, array $data = [], string $layout = 'layout'): void
    {
        echo View::render($tpl, $data, $layout);
    }

    protected function json($data, int $code = 200): never
    {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }

    protected function esPost(): bool { return ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST'; }

    protected function in(string $k, $d = ''): string
    {
        $v = $_POST[$k] ?? $_GET[$k] ?? $d;
        return is_string($v) ? trim($v) : (string)$d;
    }

    protected function inInt(string $k): int { return (int)($_POST[$k] ?? $_GET[$k] ?? 0); }

    protected function ids(string $k = 'ids'): array
    {
        $v = $_POST[$k] ?? $_GET[$k] ?? [];
        return array_values(array_unique(array_filter(array_map('intval', (array)$v))));
    }

    protected function abort(int $code, string $msg = ''): never
    {
        http_response_code($code);
        echo View::render('error', ['codigo' => $code, 'mensaje' => $msg ?: 'Error'], Auth::user() ? 'layout' : 'layout_simple');
        exit;
    }
}
