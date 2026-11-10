from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import licencia
from ..db import get_db
from ..models import Usuario
from ..security import LEE, SOLO_ADMIN

router = APIRouter(prefix="/api/licencia", tags=["licencia"])


class Activacion(BaseModel):
    codigo: str


@router.get("")
def ver(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    e = licencia.estado(db)
    db.commit()
    return e


@router.post("/activar")
def activar(d: Activacion, u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    try:
        e = licencia.activar(db, d.codigo, u.username)
    except licencia.LicenciaError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return e
