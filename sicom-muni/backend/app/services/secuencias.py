"""Correlativos con bloqueo de fila (evita duplicados en concurrencia)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Secuencia


def siguiente(db: Session, clave: str) -> int:
    fila = db.scalar(select(Secuencia).where(Secuencia.clave == clave).with_for_update())
    if fila is None:
        fila = Secuencia(clave=clave, ultimo=0)
        db.add(fila)
        db.flush()
        fila = db.scalar(select(Secuencia).where(Secuencia.clave == clave).with_for_update())
    fila.ultimo += 1
    db.flush()
    return int(fila.ultimo)


def correlativo(db: Session, prefijo: str, gestion: int | str) -> str:
    n = siguiente(db, f"{prefijo}-{gestion}")
    return f"{prefijo}-{gestion}-{n:06d}"
