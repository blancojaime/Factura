from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MODALIDADES, Contrato, Empleado, Horario, UnidadOrganizacional, Usuario
from ..security import ESCRIBE, LEE
from ..services import personal as svc
from ..services.consultas import CAUSALES
from .deps import log, reprocesar

router = APIRouter(prefix="/api", tags=["personal"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class EmpleadoIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    ci: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    complemento: str = Field(default="", max_length=5, pattern=r"^[A-Za-z0-9]*$")
    expedido: str = Field(default="", max_length=4)
    nombres: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    cargo: str = ""
    unidad: str = ""
    horario_id: int | None = None
    nro_cua: str = ""
    activo: bool = True


class ContratoIn(BaseModel):
    modalidad: str
    partida: str = ""
    haber_basico: Decimal = Field(gt=0, le=1_000_000)
    bono_antiguedad: Decimal = Field(default=Decimal("0"), ge=0)
    rc_iva: Decimal = Field(default=Decimal("0"), ge=0)
    aplica_aporte: bool | None = None
    tasa_afp: Decimal | None = Field(default=None, ge=0, le=1)
    tasa_patronal: Decimal | None = Field(default=None, ge=0, le=1)
    fecha_inicio: date
    fecha_fin: date | None = None
    nro_documento: str = ""


class BajaIn(BaseModel):
    fecha: date
    causal: str


def _contrato(c: Contrato):
    return {"id": c.id, "modalidad": c.modalidad, "partida": c.partida, "haber_basico": float(c.haber_basico),
            "bono_antiguedad": float(c.bono_antiguedad), "rc_iva": float(c.rc_iva), "aplica_aporte": c.aplica_aporte,
            "tasa_afp": float(c.tasa_afp) if c.tasa_afp is not None else None,
            "tasa_patronal": float(c.tasa_patronal) if c.tasa_patronal is not None else None,
            "fecha_inicio": c.fecha_inicio.isoformat(), "fecha_fin": c.fecha_fin.isoformat() if c.fecha_fin else None,
            "fecha_baja": c.fecha_baja.isoformat() if c.fecha_baja else None, "causal_baja": c.causal_baja,
            "nro_documento": c.nro_documento}


def _emp(e: Empleado, detalle=True):
    cs = sorted(e.contratos, key=lambda c: c.fecha_inicio)
    ult = cs[-1] if cs else None
    r = {"id": e.id, "codigo": e.codigo, "ci": e.ci, "complemento": e.complemento, "expedido": e.expedido,
         "nombres": e.nombres, "apellidos": e.apellidos, "cargo": e.cargo, "unidad": e.unidad.nombre if e.unidad else "",
         "horario_id": e.horario_id, "nro_cua": e.nro_cua, "activo": e.activo,
         "modalidad": ult.modalidad if ult else None, "haber_basico": float(ult.haber_basico) if ult else None,
         "fecha_inicio": ult.fecha_inicio.isoformat() if ult else None,
         "fecha_baja": ult.fecha_baja.isoformat() if ult and ult.fecha_baja else None}
    if detalle:
        r["contratos"] = [_contrato(c) for c in cs]
    return r


def _unidad(db: Session, nombre: str):
    nombre = nombre.strip()
    if not nombre:
        return None
    x = db.execute(select(UnidadOrganizacional).where(UnidadOrganizacional.nombre == nombre)).scalars().first()
    if not x:
        x = UnidadOrganizacional(nombre=nombre)
        db.add(x)
        db.flush()
    return x


@router.get("/empleados")
def listar(q: str = "", modalidad: str = "", activo: bool | None = None, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    st = select(Empleado).order_by(Empleado.apellidos, Empleado.nombres)
    if q:
        like = f"%{q}%"
        st = st.where(or_(Empleado.nombres.ilike(like), Empleado.apellidos.ilike(like), Empleado.ci.ilike(like),
                          Empleado.codigo.ilike(like), Empleado.cargo.ilike(like)))
    if activo is not None:
        st = st.where(Empleado.activo == activo)
    res = [_emp(e, False) for e in db.execute(st).scalars().unique()]
    if modalidad:
        res = [r for r in res if r["modalidad"] == modalidad]
    return res


@router.get("/empleados/{eid}")
def obtener(eid: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    e = db.get(Empleado, eid)
    if not e:
        raise HTTPException(404, "No encontrado")
    return _emp(e)


@router.post("/empleados")
def crear(d: EmpleadoIn, c: ContratoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    if c.modalidad not in MODALIDADES:
        raise HTTPException(422, "Modalidad inválida")
    if db.execute(select(Empleado).where(or_(Empleado.codigo == d.codigo, (Empleado.ci == d.ci) & (Empleado.complemento == d.complemento)))).scalars().first():
        raise HTTPException(409, "Ya existe un empleado con ese código o C.I.")
    e = Empleado(**d.model_dump(exclude={"unidad"}), unidad=_unidad(db, d.unidad))
    db.add(e)
    db.flush()
    _nuevo_contrato(db, e, c)
    log(db, u, "CREAR_EMPLEADO", "empleado", e.id, {"ci": e.ci, "modalidad": c.modalidad})
    db.commit()
    return _emp(e)


def _nuevo_contrato(db, e, c: ContratoIn):
    if c.fecha_fin and c.fecha_fin < c.fecha_inicio:
        raise HTTPException(422, "La fecha fin es anterior al inicio")
    ct = Contrato(empleado_id=e.id, **c.model_dump(exclude={"aplica_aporte"}))
    ct.aplica_aporte = c.aplica_aporte if c.aplica_aporte is not None else c.modalidad != "CONSULTOR_LINEA"
    ct.partida = c.partida or svc.PARTIDA_DEF[c.modalidad]
    db.add(ct)
    db.flush()
    return ct


@router.put("/empleados/{eid}")
def editar(eid: int, d: EmpleadoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    e = db.get(Empleado, eid)
    if not e:
        raise HTTPException(404, "No encontrado")
    for k, v in d.model_dump(exclude={"unidad"}).items():
        setattr(e, k, v)
    e.unidad = _unidad(db, d.unidad)
    log(db, u, "EDITAR_EMPLEADO", "empleado", e.id, d.model_dump())
    db.commit()
    return _emp(e)


@router.post("/empleados/{eid}/contratos")
def agregar_contrato(eid: int, c: ContratoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    e = db.get(Empleado, eid)
    if not e or c.modalidad not in MODALIDADES:
        raise HTTPException(404, "Empleado no encontrado o modalidad inválida")
    ct = _nuevo_contrato(db, e, c)
    log(db, u, "CREAR_CONTRATO", "contrato", ct.id, c.model_dump(mode="json"))
    db.commit()
    return _contrato(ct)


@router.put("/contratos/{cid}")
def editar_contrato(cid: int, c: ContratoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    ct = db.get(Contrato, cid)
    if not ct or c.modalidad not in MODALIDADES:
        raise HTTPException(404, "Contrato no encontrado o modalidad inválida")
    antes = _contrato(ct)
    for k, v in c.model_dump(exclude={"aplica_aporte"}).items():
        setattr(ct, k, v)
    if c.aplica_aporte is not None:
        ct.aplica_aporte = c.aplica_aporte
    log(db, u, "EDITAR_CONTRATO", "contrato", ct.id, {"antes": antes, "despues": _contrato(ct)})
    db.commit()
    reprocesar(db, u, [ct.fecha_inicio])
    db.commit()
    return _contrato(ct)


@router.post("/contratos/{cid}/baja")
def baja(cid: int, b: BajaIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    ct = db.get(Contrato, cid)
    if not ct:
        raise HTTPException(404, "Contrato no encontrado")
    if b.causal not in CAUSALES:
        raise HTTPException(422, f"Causal inválida. Use: {', '.join(CAUSALES)}")
    if b.fecha < ct.fecha_inicio:
        raise HTTPException(422, "La baja es anterior al inicio del contrato")
    ct.fecha_baja, ct.causal_baja = b.fecha, b.causal
    ct.empleado.activo = False
    log(db, u, "BAJA_CONTRATO", "contrato", ct.id, {"fecha": b.fecha, "causal": b.causal})
    db.commit()
    reprocesar(db, u, [b.fecha])
    db.commit()
    return _contrato(ct)


@router.get("/personal/plantilla")
def plantilla(u: Usuario = Depends(LEE)):
    return Response(svc.plantilla_xlsx(), media_type=XLSX,
                    headers={"Content-Disposition": 'attachment; filename="plantilla_personal.xlsx"'})


@router.post("/personal/importar")
async def importar(archivo: UploadFile = File(...), u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    data = await archivo.read()
    if len(data) > 10_000_000:
        raise HTTPException(413, "Archivo demasiado grande")
    try:
        r = svc.importar_personal(db, archivo.filename or "personal.xlsx", data, u.username)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return r
