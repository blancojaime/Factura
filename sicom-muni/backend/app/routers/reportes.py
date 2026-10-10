"""Reportes de gestion."""
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles
from ..enums import Rol
from ..models import ContratacionMenor, PartidaPresupuestaria, PreventivoC31, Usuario

router = APIRouter(prefix="/reportes", tags=["reportes"])
roles_gestion = requiere_roles(Rol.PRESUPUESTO, Rol.RPA, Rol.CONTRATACIONES, Rol.ADMIN)


@router.get("/presupuesto")
def ejecucion_presupuestaria(gestion: int | None = None, db: Session = Depends(get_db), _: Usuario = Depends(roles_gestion)):
    consulta = select(PartidaPresupuestaria).order_by(PartidaPresupuestaria.codigo_partida)
    if gestion:
        consulta = consulta.where(PartidaPresupuestaria.gestion == gestion)
    activos = dict(db.execute(select(PreventivoC31.partida_id, func.sum(PreventivoC31.importe)).where(
        PreventivoC31.estado == "ACTIVO").group_by(PreventivoC31.partida_id)).all())
    filas = []
    for p in db.scalars(consulta):
        comprometido = Decimal(activos.get(p.id) or 0)
        filas.append({"codigo_partida": p.codigo_partida, "descripcion": p.descripcion, "gestion": p.gestion,
                      "aprobado": str(p.monto_aprobado), "saldo_disponible": str(p.saldo_disponible),
                      "preventivo_activo": str(comprometido)})
    return filas


@router.get("/contrataciones")
def resumen_contrataciones(db: Session = Depends(get_db), _: Usuario = Depends(roles_gestion)):
    filas = db.execute(select(ContratacionMenor.estado, func.count(), func.coalesce(func.sum(
        ContratacionMenor.monto_referencial_total), 0)).group_by(ContratacionMenor.estado)).all()
    return [{"estado": e, "cantidad": n, "monto_referencial": str(m)} for e, n, m in filas]
