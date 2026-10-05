<?php
declare(strict_types=1);
namespace App\Core;

final class View
{
    public static function render(string $tpl, array $data = [], string $layout = 'layout'): string
    {
        $contenido = self::partial($tpl, $data);
        if ($layout === '') return $contenido;
        return self::partial('_' . $layout, $data + ['contenido' => $contenido]);
    }

    public static function partial(string $tpl, array $data = []): string
    {
        $file = ROOT . '/app/Views/' . $tpl . '.php';
        if (!is_file($file)) throw new \RuntimeException("Vista no encontrada: $tpl");
        extract($data, EXTR_SKIP);
        ob_start();
        include $file;
        return (string)ob_get_clean();
    }
}
