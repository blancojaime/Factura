<?php
declare(strict_types=1);
namespace App\Core;

final class Router
{
    public static function run(): void
    {
        header('X-Frame-Options: SAMEORIGIN');
        header('X-Content-Type-Options: nosniff');
        header('Referrer-Policy: same-origin');
        header("Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; img-src 'self' data:; frame-ancestors 'self'");

        if (!Config::installed()) {
            header('Location: ' . base_path() . '/install.php');
            exit;
        }
        Auth::start();

        $r = (string)($_GET['r'] ?? '');
        if ($r === '') $r = Auth::user() ? 'dashboard/index' : 'auth/login';
        if (!preg_match('#^([a-z]+)/([a-z_]+)$#', $r, $m)) self::noEncontrado();
        [, $modulo, $accion] = $m;
        $clase = 'App\\Controllers\\' . ucfirst($modulo) . 'Controller';
        if (!class_exists($clase) || !method_exists($clase, $accion)) self::noEncontrado();
        $rm = new \ReflectionMethod($clase, $accion);
        if (!$rm->isPublic() || $rm->getDeclaringClass()->getName() !== $clase) self::noEncontrado();

        $c = new $clase();
        $publica = (new \ReflectionProperty($clase, 'publicas'))->getValue($c);
        $roles = (new \ReflectionProperty($clase, 'roles'))->getValue($c);

        if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST' && !Csrf::check()) {
            http_response_code(419);
            echo View::render('error', ['codigo' => 419, 'mensaje' => 'La sesión expiró o el formulario no es válido. Recargue la página e intente de nuevo.'], 'layout_simple');
            return;
        }
        if (!in_array($accion, $publica, true)) {
            if (!Auth::user()) {
                flash('Inicie sesión para continuar.', 'warn');
                redirect('auth/login');
            }
            if (Auth::user()['cambiar_clave'] && !in_array($r, ['usuario/password', 'auth/salir'], true)) {
                flash('Por seguridad debe cambiar su contraseña temporal antes de continuar.', 'warn');
                redirect('usuario/password');
            }
            if (isset($roles[$accion]) && !Auth::es(...$roles[$accion])) {
                http_response_code(403);
                echo View::render('error', ['codigo' => 403, 'mensaje' => 'No tiene permiso para esta acción.']);
                return;
            }
        }
        try {
            $c->$accion();
        } catch (\PDOException $e) {
            throw $e;
        } catch (\RuntimeException $e) {
            // Errores de negocio: se muestran al usuario.
            flash($e->getMessage(), 'error');
            $volver = $_SERVER['HTTP_REFERER'] ?? '';
            redirect($volver && parse_url($volver, PHP_URL_HOST) === ($_SERVER['HTTP_HOST'] ?? '') ? $volver : 'dashboard/index');
        }
    }

    private static function noEncontrado(): never
    {
        http_response_code(404);
        echo View::render('error', ['codigo' => 404, 'mensaje' => 'Página no encontrada.'], Auth::user() ? 'layout' : 'layout_simple');
        exit;
    }
}
