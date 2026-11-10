from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (Entidad, EscalaSancion, Feriado, Horario, PermisoTipo, Turno, UnidadOrganizacional, Usuario)
from ..security import ESCRIBE, LEE
from ..services.proceso import exigir_abierto
from .deps import log

router = APIRouter(prefix="/api", tags=["catalogos"])


class EntidadIn(BaseModel):
    nombre: str
    sigla: str = ""
    codigo_sigep: str = ""
    direccion: str = ""
    ciudad: str = ""
    mae_nombre: str = ""
    mae_cargo: str = ""
    rrhh_nombre: str = ""
    rrhh_cargo: str = ""
    aprobador_nombre: str = ""
    aprobador_cargo: str = ""
    prefijo_cite: str = "GAM-RRHH"
    reglamento_rip: str = ""
    escala_modo: str = Field(default="MINUTOS", pattern="^(MINUTOS|CANTIDAD)$")
    factor_falta_planta: Decimal = Field(default=Decimal("2"), ge=0, le=10)
    factor_falta_consultor: Decimal = Field(default=Decimal("1"), ge=0, le=10)
    contar_salida_anticipada: bool = False
    tolerancia_cuenta_total: bool = True
    max_justificados_consultor: Decimal = Field(default=Decimal("1"), ge=0, le=31)
    tasa_afp: Decimal = Field(default=Decimal("0.1271"), ge=0, le=1)
    tasa_patronal: Decimal = Field(default=Decimal("0.1721"), ge=0, le=1)


def _ent(e: Entidad):
    return {c.name: (float(getattr(e, c.name)) if isinstance(getattr(e, c.name), Decimal) else getattr(e, c.name))
            for c in Entidad.__table__.columns}


@router.get("/entidad")
def get_entidad(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return _ent(db.get(Entidad, 1))


@router.put("/entidad")
def put_entidad(d: EntidadIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    e = db.get(Entidad, 1)
    antes = _ent(e)
    for k, v in d.model_dump().items():
        setattr(e, k, v)
    log(db, u, "EDITAR_ENTIDAD", "entidad", 1, {"antes": antes, "despues": _ent(e)})
    db.commit()
    return _ent(e)


# ------------------------------------------------------------------ horarios
class TurnoIn(BaseModel):
    nombre: str
    hora_entrada: time
    hora_salida: time


class HorarioIn(BaseModel):
    nombre: str
    es_defecto: bool = False
    activo: bool = True
    tolerancia_min: int = Field(default=10, ge=0, le=120)
    umbral_grave_min: int = Field(default=30, ge=1, le=240)
    dias_laborables: str = Field(default="01234", pattern="^[0-6]{1,7}$")
    turnos: list[TurnoIn] = Field(min_length=1, max_length=4)


def _hor(h: Horario):
    return {"id": h.id, "nombre": h.nombre, "es_defecto": h.es_defecto, "activo": h.activo, "tolerancia_min": h.tolerancia_min,
            "umbral_grave_min": h.umbral_grave_min, "dias_laborables": h.dias_laborables,
            "turnos": [{"nombre": t.nombre, "hora_entrada": t.hora_entrada.strftime("%H:%M"),
                        "hora_salida": t.hora_salida.strftime("%H:%M")} for t in h.turnos]}


def _validar_turnos(d: HorarioIn):
    prev = None
    for t in d.turnos:
        if t.hora_salida <= t.hora_entrada:
            raise HTTPException(422, f"Turno {t.nombre}: la salida debe ser posterior a la entrada")
        if prev and t.hora_entrada <= prev:
            raise HTTPException(422, "Los turnos deben estar en orden y no solaparse")
        prev = t.hora_salida


@router.get("/horarios")
def horarios(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [_hor(h) for h in db.execute(select(Horario).order_by(Horario.id)).scalars().unique()]


def _guardar(h: Horario, d: HorarioIn, db: Session):
    _validar_turnos(d)
    h.nombre, h.es_defecto, h.activo = d.nombre, d.es_defecto, d.activo
    h.tolerancia_min, h.umbral_grave_min, h.dias_laborables = d.tolerancia_min, d.umbral_grave_min, d.dias_laborables
    h.turnos.clear()
    db.flush()
    for i, t in enumerate(d.turnos, 1):
        h.turnos.append(Turno(orden=i, nombre=t.nombre, hora_entrada=t.hora_entrada, hora_salida=t.hora_salida))
    if d.es_defecto:
        for o in db.execute(select(Horario).where(Horario.id != (h.id or -1))).scalars():
            o.es_defecto = False


@router.post("/horarios")
def crear_horario(d: HorarioIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    h = Horario()
    db.add(h)
    _guardar(h, d, db)
    db.flush()
    log(db, u, "CREAR_HORARIO", "horario", h.id, d.model_dump(mode="json"))
    db.commit()
    return _hor(h)


@router.put("/horarios/{hid}")
def editar_horario(hid: int, d: HorarioIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    h = db.get(Horario, hid)
    if not h:
        raise HTTPException(404, "Horario no encontrado")
    _guardar(h, d, db)
    db.flush()
    log(db, u, "EDITAR_HORARIO", "horario", h.id, d.model_dump(mode="json"))
    db.commit()
    return _hor(h)


# ------------------------------------------------------------------ escala
class FilaEscalaIn(BaseModel):
    desde: int = Field(ge=0)
    hasta: int | None = Field(default=None, ge=0)
    dias_descuento: Decimal = Field(ge=0, le=30)
    sancion: str


@router.get("/escala/{modo}")
def get_escala(modo: str, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [{"desde": e.desde, "hasta": e.hasta, "dias_descuento": float(e.dias_descuento), "sancion": e.sancion}
            for e in db.execute(select(EscalaSancion).where(EscalaSancion.modo == modo).order_by(EscalaSancion.desde)).scalars()]


@router.put("/escala/{modo}")
def put_escala(modo: str, filas: list[FilaEscalaIn], u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    if modo not in ("MINUTOS", "CANTIDAD") or not filas:
        raise HTTPException(422, "Modo inválido o escala vacía")
    fs = sorted(filas, key=lambda f: f.desde)
    for a, b in zip(fs, fs[1:]):
        if a.hasta is None or a.hasta >= b.desde:
            raise HTTPException(422, "Los tramos de la escala no deben solaparse ni dejar tope abierto en el medio")
    db.execute(delete(EscalaSancion).where(EscalaSancion.modo == modo))
    for f in fs:
        db.add(EscalaSancion(modo=modo, **f.model_dump()))
    log(db, u, "EDITAR_ESCALA", "escala_sancion", modo, [f.model_dump(mode="json") for f in fs])
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ feriados / catálogos
class FeriadoIn(BaseModel):
    fecha: date
    descripcion: str


@router.get("/feriados")
def feriados(anio: int | None = None, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    q = select(Feriado).order_by(Feriado.fecha)
    if anio:
        q = q.where(Feriado.fecha.between(date(anio, 1, 1), date(anio, 12, 31)))
    return [{"fecha": f.fecha.isoformat(), "descripcion": f.descripcion} for f in db.execute(q).scalars()]


@router.post("/feriados")
def add_feriado(d: FeriadoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    exigir_abierto(db, d.fecha)
    f = db.get(Feriado, d.fecha)
    if f:
        f.descripcion = d.descripcion
    else:
        db.add(Feriado(fecha=d.fecha, descripcion=d.descripcion))
    log(db, u, "GUARDAR_FERIADO", "feriado", d.fecha.isoformat(), {"descripcion": d.descripcion})
    db.commit()
    return {"ok": True}


@router.delete("/feriados/{fecha}")
def del_feriado(fecha: date, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    exigir_abierto(db, fecha)
    f = db.get(Feriado, fecha)
    if f:
        db.delete(f)
        log(db, u, "ELIMINAR_FERIADO", "feriado", fecha.isoformat())
        db.commit()
    return {"ok": True}


@router.get("/unidades")
def unidades(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [{"id": x.id, "nombre": x.nombre} for x in db.execute(select(UnidadOrganizacional).order_by(UnidadOrganizacional.nombre)).scalars()]


@router.post("/unidades")
def crear_unidad(d: dict, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    nombre = str(d.get("nombre", "")).strip()
    if not nombre:
        raise HTTPException(422, "Nombre requerido")
    x = db.execute(select(UnidadOrganizacional).where(UnidadOrganizacional.nombre == nombre)).scalars().first()
    if not x:
        x = UnidadOrganizacional(nombre=nombre)
        db.add(x)
        db.flush()
        log(db, u, "CREAR_UNIDAD", "unidad_organizacional", x.id, {"nombre": nombre})
    db.commit()
    return {"id": x.id, "nombre": x.nombre}


@router.get("/permiso-tipos")
def permiso_tipos(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [{"codigo": t.codigo, "nombre": t.nombre, "categoria": t.categoria, "con_goce": t.con_goce,
             "max_dias": float(t.max_dias) if t.max_dias is not None else None, "base_legal": t.base_legal}
            for t in db.execute(select(PermisoTipo).order_by(PermisoTipo.categoria, PermisoTipo.nombre)).scalars()]
