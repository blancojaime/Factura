"""Respaldo cifrado y restauración con verificación de integridad SHA-256.

Formato del archivo  gam_backup_AAAAMMDD_HHMMSS.sql.enc :
  MAGIC(8) | salt(16) | nonce(12) | AES-256-GCM(ciphertext+tag)      (clave = scrypt(contraseña, salt))
  El texto plano es un script SQL (SQLite: iterdump; PostgreSQL: pg_dump).
  Se escribe además  <archivo>.sha256  con el hash del archivo cifrado y se guarda en la tabla backup_registro.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session

from .. import audit, config
from ..db import engine
from ..models import BackupRegistro

MAGIC = b"GAMBKP01"


class BackupError(Exception):
    pass


def _clave(pw: str, salt: bytes) -> bytes:
    return hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 15, r=8, p=1, dklen=32, maxmem=2 ** 28)


def cifrar(plano: bytes, pw: str) -> bytes:
    salt, nonce = os.urandom(16), os.urandom(12)
    return MAGIC + salt + nonce + AESGCM(_clave(pw, salt)).encrypt(nonce, plano, MAGIC)


def descifrar(blob: bytes, pw: str) -> bytes:
    if blob[:8] != MAGIC:
        raise BackupError("El archivo no es un respaldo válido de este sistema")
    salt, nonce, ct = blob[8:24], blob[24:36], blob[36:]
    try:
        return AESGCM(_clave(pw, salt)).decrypt(nonce, ct, MAGIC)
    except InvalidTag:
        raise BackupError("Contraseña incorrecta o archivo alterado/corrupto")


def _dump_sqlite() -> bytes:
    path = engine.url.database
    con = sqlite3.connect(path)
    try:
        return "\n".join(con.iterdump()).encode("utf-8")
    finally:
        con.close()


def _pg_args():
    u = engine.url
    env = {**os.environ, "PGPASSWORD": u.password or ""}      # la clave NO va en la línea de comandos
    args = ["-h", u.host or "localhost", "-p", str(u.port or 5432), "-U", u.username or "postgres", "-d", u.database]
    return args, env


def _dump_pg() -> bytes:
    if not shutil.which("pg_dump"):
        raise BackupError("pg_dump no está instalado/en PATH")
    args, env = _pg_args()
    r = subprocess.run(["pg_dump", "--no-owner", "--clean", "--if-exists", *args], capture_output=True, env=env)
    if r.returncode:
        raise BackupError("pg_dump: " + r.stderr.decode(errors="replace")[:300])
    return r.stdout


def restaurar_pg(blob: bytes, sha_esperado: str | None, password: str) -> dict:
    """psql en UNA transacción (todo o nada). Requiere psql en PATH y permisos de DDL."""
    if not shutil.which("psql"):
        raise BackupError("psql no está instalado/en PATH")
    info = verificar_respaldo(blob, sha_esperado, password)
    sql = descifrar(blob, password)
    args, env = _pg_args()
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "restore.sql"
        f.write_bytes(sql)
        r = subprocess.run(["psql", "-v", "ON_ERROR_STOP=1", "--single-transaction", *args, "-f", str(f)],
                           capture_output=True, env=env, timeout=600)
    if r.returncode:
        raise BackupError("psql: " + r.stderr.decode(errors="replace")[:400])
    engine.dispose()
    return {**info, "restaurado": True}


def crear_respaldo(db: Session, password: str, usuario: str, tipo: str = "MANUAL", destino: Path | None = None) -> dict:
    if len(password) < 8:
        raise BackupError("La contraseña de cifrado debe tener al menos 8 caracteres")
    plano = _dump_pg() if engine.dialect.name == "postgresql" else _dump_sqlite()
    blob = cifrar(plano, password)
    carpeta = Path(destino) if destino else config.BACKUP_DIR
    carpeta.mkdir(parents=True, exist_ok=True)
    f = carpeta / f"gam_backup_{datetime.now():%Y%m%d_%H%M%S}.sql.enc"
    f.write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    Path(str(f) + ".sha256").write_text(f"{sha}  {f.name}\n")
    db.add(BackupRegistro(archivo=str(f), sha256=sha, bytes=len(blob), usuario=usuario, tipo=tipo))
    audit.registrar(db, usuario, "BACKUP", "backup", f.name, {"sha256": sha, "bytes": len(blob), "tipo": tipo})
    return {"archivo": f.name, "ruta": str(f), "sha256": sha, "bytes": len(blob)}


def verificar_respaldo(blob: bytes, sha_esperado: str | None, password: str | None = None) -> dict:
    sha = hashlib.sha256(blob).hexdigest()
    if sha_esperado and sha.lower() != sha_esperado.strip().lower().split()[0]:
        raise BackupError(f"Falla de integridad SHA-256: esperado {sha_esperado[:16]}…, calculado {sha[:16]}…")
    if password is not None:
        descifrar(blob, password)
    return {"sha256": sha, "integridad": "OK" if sha_esperado else "SIN_HASH_DE_REFERENCIA", "descifrado": password is not None}


def restaurar_sqlite(blob: bytes, sha_esperado: str | None, password: str) -> dict:
    """Valida hash, descifra y reconstruye la base. Se hace una copia de seguridad previa del archivo actual."""
    if engine.dialect.name == "postgresql":
        return restaurar_pg(blob, sha_esperado, password)
    info = verificar_respaldo(blob, sha_esperado, password)
    sql = descifrar(blob, password).decode("utf-8")
    path = Path(engine.url.database)
    tmp = Path(tempfile.mkdtemp()) / "restore.db"
    src = sqlite3.connect(tmp)
    try:
        src.executescript(sql)
        if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BackupError("La base restaurada no pasa PRAGMA integrity_check")
        # copia de seguridad previa del estado actual (API de backup en línea: segura con conexiones abiertas)
        previa = Path(str(path) + f".antes_de_restaurar_{datetime.now():%Y%m%d_%H%M%S}")
        cur, bak = sqlite3.connect(path, timeout=30), sqlite3.connect(previa)
        try:
            cur.backup(bak)
        finally:
            bak.close()
            cur.close()
        dst = sqlite3.connect(path, timeout=30)
        try:
            src.backup(dst)               # sobrescribe el contenido de la base en uso
        finally:
            dst.close()
    except sqlite3.Error as e:
        raise BackupError(f"No se pudo restaurar: {e}")
    finally:
        src.close()
        shutil.rmtree(tmp.parent, ignore_errors=True)
    return {**info, "restaurado": True, "copia_previa": previa.name}
