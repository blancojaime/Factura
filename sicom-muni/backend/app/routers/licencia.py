"""Estado y activacion de la licencia (publico: debe funcionar antes de iniciar sesion)."""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ip_cliente
from ..services import auditoria, licencia

router = APIRouter(prefix="/licencia", tags=["licencia"])


class ActivarIn(BaseModel):
    texto: str = Field(min_length=20, max_length=20000)


@router.get("")
def ver_estado(db: Session = Depends(get_db)):
    return licencia.estado(db, forzar=True)


@router.post("")
def activar(datos: ActivarIn, request: Request, db: Session = Depends(get_db)):
    e = licencia.activar(db, datos.texto)
    auditoria.registrar(db, None, "LICENCIA_ACTIVADA", "parametros_institucionales", None, None,
                        {"licencia_id": e["licencia_id"], "entidad": e["entidad"], "vence": e["vence"]}, ip_cliente(request))
    db.commit()
    return e
