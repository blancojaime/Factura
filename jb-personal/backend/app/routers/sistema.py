from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit, config
from ..db import get_db
from ..models import AuditLog, BackupRegistro, Usuario
from ..security import ESCRIBE, LEE, SOLO_ADMIN
from ..services import backup as bk
from .deps import log

router = APIRouter(prefix="/api", tags=["sistema"])


class BackupIn(BaseModel):
    password: str
    destino: str = ""         # carpeta local/USB (modo escritorio); vacío = carpeta de respaldos del sistema


@router.post("/backup")
def crear(d: BackupIn, u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    try:
        r = bk.crear_respaldo(db, d.password, u.username, "MANUAL", Path(d.destino) if d.destino else None)
    except bk.BackupError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return r


@router.get("/backup")
def listar(u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    return [{"id": b.id, "ts": b.ts.isoformat(), "archivo": Path(b.archivo).name, "sha256": b.sha256, "bytes": b.bytes,
             "usuario": b.usuario, "tipo": b.tipo} for b in db.execute(select(BackupRegistro).order_by(BackupRegistro.id.desc()).limit(100)).scalars()]


@router.get("/backup/{nombre}/descargar")
def descargar(nombre: str, u: Usuario = Depends(SOLO_ADMIN)):
    f = (config.BACKUP_DIR / Path(nombre).name)
    if not f.is_file() or not f.name.startswith("gam_backup_"):
        raise HTTPException(404, "Respaldo no encontrado")
    return FileResponse(f, filename=f.name, media_type="application/octet-stream")


@router.post("/backup/verificar")
async def verificar(archivo: UploadFile = File(...), sha256: str = Form(""), password: str = Form(""),
                    u: Usuario = Depends(SOLO_ADMIN)):
    try:
        return bk.verificar_respaldo(await archivo.read(), sha256 or None, password or None)
    except bk.BackupError as e:
        raise HTTPException(422, str(e))


@router.post("/backup/restaurar")
async def restaurar(archivo: UploadFile = File(...), sha256: str = Form(...), password: str = Form(...),
                    u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    """Restaura SQLite o PostgreSQL. Exige el SHA-256 de referencia: sin hash no se restaura."""
    username = u.username
    db.rollback()
    db.close()               # libera la transacción de autenticación (en PostgreSQL bloquearía los DROP)
    try:
        r = bk.restaurar_sqlite(await archivo.read(), sha256, password)
    except bk.BackupError as e:
        raise HTTPException(422, str(e))
    from ..db import SessionLocal
    with SessionLocal() as s:        # la bitácora conserva constancia de la restauración
        audit.registrar(s, username, "RESTAURAR_BACKUP", "backup", archivo.filename or "", {"sha256": r["sha256"]})
        s.commit()
    return r


@router.get("/auditoria")
def bitacora(limite: int = 200, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    limite = max(1, min(limite, 2000))
    return [{"id": a.id, "ts": a.ts.isoformat(sep=" "), "usuario": a.usuario, "accion": a.accion, "entidad": a.entidad,
             "entidad_id": a.entidad_id, "detalle": a.detalle[:500], "hash": a.hash[:16]}
            for a in db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(limite)).scalars()]


@router.get("/auditoria/verificar")
def verificar_bitacora(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return audit.verificar_cadena(db)
