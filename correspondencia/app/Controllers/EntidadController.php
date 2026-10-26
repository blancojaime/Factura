<?php
declare(strict_types=1);
namespace App\Controllers;

use App\Core\Controller;
use App\Services\Ajustes;

/** Sirve el logo de la entidad (se imprime también en consultas públicas). */
final class EntidadController extends Controller
{
    protected array $publicas = ['logo'];

    public function logo(): void
    {
        $p = Ajustes::logoPath();
        if (!$p) { http_response_code(404); exit; }
        header('Content-Type: ' . (str_ends_with($p, '.png') ? 'image/png' : 'image/jpeg'));
        header('Cache-Control: public, max-age=86400');
        header('Content-Length: ' . filesize($p));
        readfile($p);
    }
}
