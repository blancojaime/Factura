"""Copias de seguridad verificadas: API de backup de SQLite + ZIP + SHA-256 (+ cifrado AES opcional)."""
import base64
import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"SIIMBAK2"
EXT = ".siimbak"


class BackupError(Exception):
    pass


def _key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390_000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def _sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup(db, dest_dir, label="manual", password=None, meta=None, extra_dir=None) -> Path:
    """Crea un respaldo consistente (sin detener el sistema). Devuelve la ruta del archivo."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(c for c in label if c.isalnum() or c in "-_")[:30] or "manual"
    out = dest_dir / f"SIIM_{stamp}_{safe}{EXT}"
    with tempfile.TemporaryDirectory() as td:
        snap = Path(td) / "siim2026.db"
        dst = sqlite3.connect(str(snap))
        try:
            with db._lock:
                db.conn.backup(dst)
        finally:
            dst.close()
        chk = sqlite3.connect(str(snap))
        try:
            ok = chk.execute("PRAGMA integrity_check").fetchone()[0]
            ver = chk.execute("PRAGMA user_version").fetchone()[0]
        finally:
            chk.close()
        if ok != "ok":
            raise BackupError("La base de datos falló la verificación de integridad; respaldo cancelado: " + str(ok))
        manifest = dict(app="SIIM2026", creado=datetime.now().isoformat(timespec="seconds"), schema=ver, sha256=_sha(snap),
                        bytes=snap.stat().st_size, cifrado=bool(password), etiqueta=label, **(meta or {}))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.write(snap, "siim2026.db")
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
        data = buf.getvalue()
    if password:
        salt = os.urandom(16)
        data = MAGIC + salt + Fernet(_key(password, salt)).encrypt(data)
    tmp = out.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, out)
    verify_backup(out, password)           # relectura inmediata
    if extra_dir:
        try:
            Path(extra_dir).mkdir(parents=True, exist_ok=True)
            shutil.copy2(out, Path(extra_dir) / out.name)
        except OSError as e:
            raise BackupError(f"Respaldo creado, pero no se pudo copiar a la ubicación externa: {e}")
    return out


def _open_zip(path, password):
    raw = Path(path).read_bytes()
    if raw.startswith(MAGIC):
        if not password:
            raise BackupError("El respaldo está cifrado: se requiere contraseña.")
        try:
            raw = Fernet(_key(password, raw[8:24])).decrypt(raw[24:])
        except InvalidToken:
            raise BackupError("Contraseña incorrecta o archivo dañado.")
    try:
        return zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise BackupError("Archivo de respaldo dañado.")


def is_encrypted(path) -> bool:
    with open(path, "rb") as f:
        return f.read(8) == MAGIC


def read_manifest(path, password=None) -> dict:
    with _open_zip(path, password) as z:
        return json.loads(z.read("manifest.json"))


def verify_backup(path, password=None) -> dict:
    try:
        with _open_zip(path, password) as z:
            man = json.loads(z.read("manifest.json"))
            blob = z.read("siim2026.db")
    except BackupError:
        raise
    except (zipfile.BadZipFile, KeyError, ValueError, OSError) as e:
        raise BackupError(f"Respaldo corrupto o ilegible: {e}")
    if hashlib.sha256(blob).hexdigest() != man["sha256"]:
        raise BackupError("La suma de verificación (SHA-256) no coincide: respaldo corrupto.")
    return man


def restore_backup(db, path, password=None, safety_dir=None):
    """Restaura sobre la BD activa. Crea antes un respaldo de seguridad y revierte si algo falla."""
    man = verify_backup(path, password)
    from .schema import MIGRATIONS
    if man["schema"] > len(MIGRATIONS):
        raise BackupError("El respaldo proviene de una versión más nueva del sistema.")
    safety = create_backup(db, safety_dir or Path(db.path).parent / "backups", label="antes-de-restaurar")
    target = Path(db.path)
    with _open_zip(path, password) as z:
        blob = z.read("siim2026.db")
    db.close()
    try:
        for suf in ("-wal", "-shm"):
            p = Path(str(target) + suf)
            if p.exists():
                p.unlink()
        tmp = target.with_suffix(".restore")
        tmp.write_bytes(blob)
        os.replace(tmp, target)
        db.open()
        ok, info = db.integrity_check()
        if not ok:
            raise BackupError("La BD restaurada no pasó la verificación: " + "; ".join(info))
    except Exception:
        # revertir
        try:
            db.close()
        except Exception:
            pass
        with _open_zip(safety, None) as z:
            Path(target).write_bytes(z.read("siim2026.db"))
        db.open()
        raise
    return man, safety


def list_backups(dir_):
    rows = []
    for p in sorted(Path(dir_).glob("*" + EXT), reverse=True):
        rows.append(dict(path=p, nombre=p.name, bytes=p.stat().st_size, fecha=datetime.fromtimestamp(p.stat().st_mtime), cifrado=is_encrypted(p)))
    return rows


def apply_retention(dir_, keep_last=30, keep_monthly=12):
    """Conserva los últimos N respaldos y el más reciente de cada mes (hasta M meses). Nunca borra 'antes-de-restaurar' recientes."""
    files = list_backups(dir_)
    keep = {f["path"] for f in files[:keep_last]}
    seen = set()
    for f in files:
        k = f["fecha"].strftime("%Y%m")
        if k not in seen and len(seen) < keep_monthly:
            seen.add(k)
            keep.add(f["path"])
    removed = []
    for f in files:
        if f["path"] not in keep:
            f["path"].unlink()
            removed.append(f["nombre"])
    return removed
