"""Acceso a SQLite: conexión robusta (WAL, claves foráneas), consultas y transacciones anidadas."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Iterator


class DatabaseError(Exception):
    pass


class Database:
    """Envoltura de una base SQLite. Los resultados son diccionarios.

    - WAL + synchronous=FULL: tolera cortes de energía sin corromper el archivo.
    - Transacciones anidadas mediante SAVEPOINT.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        self._depth = 0
        self.cn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=15)
        self.cn.row_factory = sqlite3.Row
        for p in ("PRAGMA foreign_keys=ON", "PRAGMA journal_mode=WAL", "PRAGMA synchronous=FULL",
                  "PRAGMA busy_timeout=15000", "PRAGMA temp_store=MEMORY"):
            self.cn.execute(p)

    # ------------------------------------------------------------ consultas
    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            try:
                return self.cn.execute(sql, tuple(params))
            except sqlite3.Error as ex:
                raise DatabaseError(f"{ex}\nSQL: {sql[:300]}") from ex

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        cur = self.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict | None:
        cur = self.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r else None

    def scalar(self, sql: str, params: Iterable[Any] = (), default=None):
        cur = self.execute(sql, params)
        r = cur.fetchone()
        if r is None or r[0] is None:
            return default
        return r[0]

    def insert(self, table: str, **vals) -> int:
        cols = ", ".join(f'"{c}"' for c in vals)
        qs = ", ".join("?" for _ in vals)
        cur = self.execute(f'INSERT INTO "{table}" ({cols}) VALUES ({qs})', list(vals.values()))
        return int(cur.lastrowid)

    def update(self, table: str, id_: int, **vals) -> None:
        if not vals:
            return
        sets = ", ".join(f'"{c}"=?' for c in vals)
        self.execute(f'UPDATE "{table}" SET {sets} WHERE id=?', list(vals.values()) + [id_])

    def delete(self, table: str, id_: int) -> None:
        self.execute(f'DELETE FROM "{table}" WHERE id=?', (id_,))

    def table_exists(self, name: str) -> bool:
        return self.scalar("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,), 0) > 0

    # --------------------------------------------------------- transacciones
    @contextmanager
    def tx(self) -> Iterator["Database"]:
        """Transacción (anidable). Confirma al salir y revierte ante cualquier excepción."""
        with self._lock:
            nombre = f"sp{self._depth}"
            if self._depth == 0:
                self.cn.execute("BEGIN IMMEDIATE")
            else:
                self.cn.execute(f"SAVEPOINT {nombre}")
            self._depth += 1
            try:
                yield self
            except BaseException:
                self._depth -= 1
                if self._depth == 0:
                    self.cn.execute("ROLLBACK")
                else:
                    self.cn.execute(f"ROLLBACK TO {nombre}")
                    self.cn.execute(f"RELEASE {nombre}")
                raise
            else:
                self._depth -= 1
                if self._depth == 0:
                    self.cn.execute("COMMIT")
                else:
                    self.cn.execute(f"RELEASE {nombre}")

    # ------------------------------------------------------------ utilidades
    def integrity_check(self) -> str:
        return str(self.scalar("PRAGMA integrity_check", default="?"))

    def checkpoint(self) -> None:
        try:
            self.cn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass

    def backup_to(self, dest_path: str) -> None:
        """Copia consistente en caliente (API de backup de SQLite)."""
        with self._lock:
            dst = sqlite3.connect(dest_path)
            try:
                self.cn.backup(dst)
            finally:
                dst.close()

    def vacuum(self) -> None:
        self.checkpoint()
        self.cn.execute("VACUUM")

    def close(self) -> None:
        with self._lock:
            try:
                self.checkpoint()
                self.cn.close()
            except sqlite3.Error:
                pass
