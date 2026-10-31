"""Acceso a SQLite: transaccional, WAL, claves foráneas, migraciones y chequeo de integridad."""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from .schema import MIGRATIONS


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.conn = None
        self.open()

    # ---- ciclo de vida
    def open(self):
        self.conn = sqlite3.connect(str(self.path), timeout=30, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        c = self.conn
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=30000")
        self.migrate()

    def close(self):
        with self._lock:
            if self.conn is not None:
                try:
                    self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.Error:
                    pass
                self.conn.close()
                self.conn = None

    def migrate(self):
        cur = self.conn.execute("PRAGMA user_version").fetchone()[0]
        for i in range(cur, len(MIGRATIONS)):
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                for stmt in _split(MIGRATIONS[i]):
                    self.conn.execute(stmt)
                self.conn.execute(f"PRAGMA user_version={i + 1}")
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    @property
    def schema_version(self):
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    # ---- operaciones
    @contextmanager
    def tx(self):
        """Transacción atómica (anidable: sólo la externa hace COMMIT)."""
        with self._lock:
            if self.conn.in_transaction:
                yield self
                return
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            else:
                self.conn.execute("COMMIT")

    def execute(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params)

    def insert(self, table, data: dict) -> int:
        cols = ",".join(data)
        q = ",".join("?" * len(data))
        with self._lock:
            return self.conn.execute(f"INSERT INTO {table}({cols}) VALUES({q})", list(data.values())).lastrowid

    def update(self, table, data: dict, where: str, wparams=()):
        sets = ",".join(f"{k}=?" for k in data)
        with self._lock:
            self.conn.execute(f"UPDATE {table} SET {sets} WHERE {where}", list(data.values()) + list(wparams))

    def one(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def all(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def scalar(self, sql, params=(), default=None):
        r = self.one(sql, params)
        return default if r is None or r[0] is None else r[0]

    def next_number(self, clave: str, start=0) -> int:
        with self.tx():
            r = self.one("SELECT valor FROM contador WHERE clave=?", (clave,))
            n = (r[0] + 1) if r else start + 1
            self.execute("INSERT OR REPLACE INTO contador(clave,valor) VALUES(?,?)", (clave, n))
            return n

    # ---- mantenimiento
    def integrity_check(self):
        rows = [r[0] for r in self.conn.execute("PRAGMA integrity_check").fetchall()]
        fk = self.conn.execute("PRAGMA foreign_key_check").fetchall()
        return rows == ["ok"] and not fk, rows + [f"FK: {tuple(r)}" for r in fk]

    def reindex(self):
        self.conn.execute("REINDEX")
        self.conn.execute("ANALYZE")

    def compact(self):
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.conn.execute("VACUUM")

    # ---- parámetros
    def param(self, clave, default=None):
        r = self.one("SELECT valor FROM parametros WHERE clave=?", (clave,))
        return default if r is None else r[0]

    def set_param(self, clave, valor):
        self.execute("INSERT OR REPLACE INTO parametros(clave,valor) VALUES(?,?)", (clave, str(valor)))

    def param_f(self, clave, default=0.0):
        try:
            return float(self.param(clave, default))
        except (TypeError, ValueError):
            return float(default)


def _split(script):
    out, buf = [], ""
    for line in script.splitlines():
        if line.strip().startswith("--"):
            continue
        buf += line + "\n"
        if sqlite3.complete_statement(buf):
            out.append(buf.strip())
            buf = ""
    return [s for s in out if s]
