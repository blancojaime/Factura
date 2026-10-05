<?php
declare(strict_types=1);
namespace App\Core;

use PDO;

final class DB
{
    private static ?PDO $pdo = null;
    private static int $depth = 0;

    public static function connect(array $c): PDO
    {
        $dsn = sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4', $c['host'], (int)($c['port'] ?? 3306), $c['name']);
        return new PDO($dsn, $c['user'], $c['pass'], [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
    }

    public static function pdo(): PDO
    {
        return self::$pdo ??= self::connect(Config::get('db'));
    }

    public static function reset(): void { self::$pdo = null; self::$depth = 0; }

    public static function q(string $sql, array $p = []): \PDOStatement
    {
        $st = self::pdo()->prepare($sql);
        $st->execute($p);
        return $st;
    }

    public static function all(string $sql, array $p = []): array { return self::q($sql, $p)->fetchAll(); }

    public static function one(string $sql, array $p = []): ?array
    {
        $r = self::q($sql, $p)->fetch();
        return $r === false ? null : $r;
    }

    public static function val(string $sql, array $p = [])
    {
        $r = self::q($sql, $p)->fetchColumn();
        return $r === false ? null : $r;
    }

    public static function exec(string $sql, array $p = []): int { return self::q($sql, $p)->rowCount(); }

    public static function insert(string $tabla, array $datos): int
    {
        $cols = array_keys($datos);
        $sql = 'INSERT INTO `' . $tabla . '` (`' . implode('`,`', $cols) . '`) VALUES (' . implode(',', array_fill(0, count($cols), '?')) . ')';
        self::q($sql, array_values($datos));
        return (int)self::pdo()->lastInsertId();
    }

    public static function update(string $tabla, int $id, array $datos): void
    {
        $set = implode(',', array_map(fn($c) => "`$c`=?", array_keys($datos)));
        self::q("UPDATE `$tabla` SET $set WHERE id=?", [...array_values($datos), $id]);
    }

    /** Transacción con anidamiento simple. */
    public static function tx(callable $fn)
    {
        $pdo = self::pdo();
        if (self::$depth++ === 0) $pdo->beginTransaction();
        try {
            $r = $fn();
            if (--self::$depth === 0) $pdo->commit();
            return $r;
        } catch (\Throwable $e) {
            self::$depth = 0;
            if ($pdo->inTransaction()) $pdo->rollBack();
            throw $e;
        }
    }
}
