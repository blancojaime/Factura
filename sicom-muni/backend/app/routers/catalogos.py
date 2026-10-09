"""Partidas presupuestarias y Catalogo CHB (consulta obligatoria del solicitante)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ip_cliente, requiere_roles, usuario_actual
from ..enums import Rol
from ..models import CatalogoCHB, PartidaPresupuestaria, Usuario
from ..schemas import CatalogoIn, CatalogoOut, ConsultaCHBOut, PartidaIn, PartidaOut
from ..services import auditoria, validador_chb

router = APIRouter(tags=["catalogos"])


# ---------------- partidas
@router.get("/partidas", response_model=list[PartidaOut])
def listar_partidas(gestion: int | None = None, q: str | None = None, db: Session = Depends(get_db),
                    _: Usuario = Depends(usuario_actual)):
    consulta = select(PartidaPresupuestaria).order_by(PartidaPresupuestaria.codigo_partida)
    if gestion:
        consulta = consulta.where(PartidaPresupuestaria.gestion == gestion)
    if q:
        from sqlalchemy import func, or_
        consulta = consulta.where(or_(PartidaPresupuestaria.codigo_partida.like(f"{q}%"),
                                      func.lower(PartidaPresupuestaria.descripcion).like(f"%{q.lower()}%")))
    return list(db.scalars(consulta.limit(200)))


@router.post("/partidas", response_model=PartidaOut, status_code=status.HTTP_201_CREATED)
def crear_partida(datos: PartidaIn, request: Request, db: Session = Depends(get_db),
                  u: Usuario = Depends(requiere_roles(Rol.PRESUPUESTO))):
    p = PartidaPresupuestaria(**datos.model_dump(), monto_aprobado=datos.saldo_disponible)
    db.add(p)
    try:
        db.flush()
    except Exception:  # noqa: BLE001 - violacion de unicidad de la estructura
        db.rollback()
        raise HTTPException(409, "Ya existe esa partida con la misma estructura programática")
    auditoria.registrar(db, u.id, "PARTIDA_CREADA", "partidas_presupuestarias", p.id, None,
                        {"codigo": p.codigo_partida, "saldo": str(p.saldo_disponible)}, ip_cliente(request))
    db.commit()
    return p


# ---------------- catalogo CHB
@router.get("/catalogo-chb", response_model=list[CatalogoOut])
def buscar_catalogo(q: str = Query("", max_length=100), db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return validador_chb.buscar_catalogo(db, q)


@router.get("/catalogo-chb/consulta/{codigo}", response_model=ConsultaCHBOut)
def consultar_codigo(codigo: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    cat = validador_chb.consultar_codigo(db, codigo)
    if cat is None:
        return ConsultaCHBOut(codigo_unspsc=codigo, en_catalogo=False,
                              mensaje="Sin coincidencia en el Catálogo CHB: se exigirá justificación de la compra")
    return ConsultaCHBOut(codigo_unspsc=codigo, en_catalogo=True, descripcion_bien=cat.descripcion_bien,
                          unidad_medida=cat.unidad_medida, precio_referencial_nacional=cat.precio_referencial_nacional,
                          mensaje=validador_chb.MSG_COMPRA_CHB)


@router.post("/catalogo-chb", response_model=CatalogoOut, status_code=status.HTTP_201_CREATED)
def crear_catalogo(datos: CatalogoIn, request: Request, db: Session = Depends(get_db),
                   u: Usuario = Depends(requiere_roles(Rol.ADMIN))):
    if db.scalar(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == datos.codigo_unspsc)):
        raise HTTPException(409, "El código UNSPSC ya existe en el catálogo")
    c = CatalogoCHB(**datos.model_dump())
    db.add(c)
    db.flush()
    auditoria.registrar(db, u.id, "CATALOGO_CHB_CREADO", "catalogo_chb", c.id, None, {"codigo": c.codigo_unspsc}, ip_cliente(request))
    db.commit()
    return c


@router.put("/catalogo-chb/{cid}", response_model=CatalogoOut)
def actualizar_catalogo(cid: uuid.UUID, datos: CatalogoIn, request: Request, db: Session = Depends(get_db),
                        u: Usuario = Depends(requiere_roles(Rol.ADMIN))):
    c = db.get(CatalogoCHB, cid)
    if c is None:
        raise HTTPException(404, "No encontrado")
    antes = {"descripcion": c.descripcion_bien, "activo": c.activo}
    for k, v in datos.model_dump().items():
        setattr(c, k, v)
    db.flush()
    auditoria.registrar(db, u.id, "CATALOGO_CHB_ACTUALIZADO", "catalogo_chb", c.id, antes,
                        {"descripcion": c.descripcion_bien, "activo": c.activo}, ip_cliente(request))
    db.commit()
    return c
