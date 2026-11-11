"""Multas y descuentos adicionales: se descuentan en la planilla del mes y salen en TODOS los reportes."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Ajuste, Empleado, Usuario
from ..security import ESCRIBE, LEE
from ..services.proceso import exigir_abierto
from .deps import log, reprocesar

router = APIRouter(prefix="/api/ajustes", tags=["multas"])


class AjusteIn(BaseModel):
    anio: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    empleado_id: int
    tipo: str = Field(default="MULTA", pattern="^(MULTA|DESCUENTO)$")
    concepto: str = Field(min_length=3, max_length=200)
    monto: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    referencia: str = Field(default="", max_length=100)


def _a(a: Ajuste):
    return {"id": a.id, "anio": a.anio, "mes": a.mes, "empleado_id": a.empleado_id, "empleado": a.empleado.nombre_completo,
            "ci": a.empleado.ci_completo, "tipo": a.tipo, "concepto": a.concepto, "monto": float(a.monto),
            "referencia": a.referencia, "estado": a.estado}


@router.get("")
def listar(anio: int, mes: int, empleado_id: int | None = None, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    q = select(Ajuste).where(Ajuste.anio == anio, Ajuste.mes == mes).order_by(Ajuste.id)
    if empleado_id:
        q = q.where(Ajuste.empleado_id == empleado_id)
    return [_a(a) for a in db.execute(q).scalars().unique()]


@router.post("")
def crear(d: AjusteIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    if not db.get(Empleado, d.empleado_id):
        raise HTTPException(404, "Empleado no encontrado")
    exigir_abierto(db, date(d.anio, d.mes, 1))
    a = Ajuste(**d.model_dump(), creado_por=u.username)
    db.add(a)
    db.flush()
    log(db, u, "CREAR_AJUSTE", "ajuste", a.id, {"periodo": f"{d.anio}-{d.mes:02d}", "tipo": d.tipo, "monto": str(d.monto),
                                                 "concepto": d.concepto, "referencia": d.referencia})
    reprocesar(db, u, [date(d.anio, d.mes, 1)])
    db.commit()
    db.refresh(a)
    return _a(a)


@router.post("/{aid}/anular")
def anular(aid: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    a = db.get(Ajuste, aid)
    if not a or a.estado == "ANULADO":
        raise HTTPException(404, "Ajuste no encontrado o ya anulado")
    exigir_abierto(db, date(a.anio, a.mes, 1))
    a.estado = "ANULADO"
    log(db, u, "ANULAR_AJUSTE", "ajuste", a.id, {"monto": str(a.monto), "concepto": a.concepto})
    reprocesar(db, u, [date(a.anio, a.mes, 1)])
    db.commit()
    return _a(a)
