<?php
declare(strict_types=1);
namespace App\Core;

final class Csrf
{
    public static function token(): string
    {
        return $_SESSION['_csrf'] ??= bin2hex(random_bytes(32));
    }

    public static function field(): string
    {
        return '<input type="hidden" name="_csrf" value="' . e(self::token()) . '">';
    }

    public static function check(): bool
    {
        $t = $_POST['_csrf'] ?? ($_SERVER['HTTP_X_CSRF'] ?? '');
        return is_string($t) && hash_equals(self::token(), $t);
    }
}
