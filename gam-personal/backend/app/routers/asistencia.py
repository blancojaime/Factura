from __future__ import annotations

from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AsistenciaDia, Empleado, ImportBiometrico, Liquidacion, Marca, Periodo, Usuario
from ..security import ESCRIBE, LEE, SOLO_ADMIN
from ..services import proceso
from ..services.biometrico import _ident
from .deps import log

router = APIRouter(prefix="/api", tags=["asistencia"])


@router.post("/biometrico/importar")
async def importar(archivo: UploadFile = File(...), orden_fecha: str = Form("dmy"), u: Usuario = Depends(ESCRIBE),
                   db: Session = Depends(get_db)):
    if orden_fecha not in ("dmy", "mdy"):
        raise HTTPException(422, "orden_fecha debe ser dmy o mdy")
    data = await archivo.read()
    if len(data) > 50_000_000:
        raise HTTPException(413, "Archivo demasiado grande")
    try:
        lote = proceso.importar_biometrico(db, archivo.filename or "marcas", data, u.username, orden_fecha)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"lote": lote.id, "formato": lote.formato, "leidas": lote.leidas, "nuevas": lote.nuevas,
            "duplicadas": lote.duplicadas, "rechazadas": lote.rechazadas, "detalle_rechazo": lote.detalle_rechazo.splitlines()[:20]}


@router.get("/biometrico/lotes")
def lotes(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [{"id": l.id, "archivo": l.archivo, "formato": l.formato, "fecha": l.fecha.isoformat(), "usuario": l.usuario,
             "leidas": l.leidas, "nuevas": l.nuevas, "duplicadas": l.duplicadas, "rechazadas": l.rechazadas,
             "sha256": l.sha256} for l in db.execute(select(ImportBiometrico).order_by(ImportBiometrico.id.desc()).limit(100)).scalars()]


@router.get("/biometrico/no-reconocidos/{anio}/{mes}")
def no_reconocidos(anio: int, mes: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    """Identificadores del reloj sin empleado asociado (para corregir códigos)."""
    ini, fin = proceso.rango_mes(anio, mes)
    conocidos = {_ident(e.codigo) for e in db.execute(select(Empleado)).scalars().unique()}
    cuenta = defaultdict(int)
    for (ident,) in db.execute(select(Marca.identificador).where(
            Marca.fecha_hora >= ini, Marca.fecha_hora < date(fin.year + (fin.month == 12), fin.month % 12 + 1, 1))):
        if _ident(ident) not in conocidos:
            cuenta[ident] += 1
    return [{"identificador": k, "marcas": v} for k, v in sorted(cuenta.items())]


@router.get("/marcas/{anio}/{mes}")
def marcas(anio: int, mes: int, identificador: str = "", u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    ini, fin = proceso.rango_mes(anio, mes)
    q = select(Marca).where(Marca.fecha_hora >= ini, Marca.fecha_hora < date(fin.year + (fin.month == 12), fin.month % 12 + 1, 1))
    if identificador:
        q = q.where(Marca.identificador == identificador)
    return [{"id": m.id, "identificador": m.identificador, "fecha_hora": m.fecha_hora.isoformat(sep=" "),
             "tipo": m.tipo_evento, "metodo": m.metodo, "dispositivo": m.dispositivo}
            for m in db.execute(q.order_by(Marca.fecha_hora).limit(2000)).scalars()]


# ------------------------------------------------------------------ periodos
@router.get("/periodos")
def periodos(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [{"anio": p.anio, "mes": p.mes, "estado": p.estado, "procesado_en": p.procesado_en.isoformat() if p.procesado_en else None,
             "cerrado_por": p.cerrado_por} for p in db.execute(select(Periodo).order_by(Periodo.anio.desc(), Periodo.mes.desc())).scalars()]


@router.post("/periodos/{anio}/{mes}/procesar")
def procesar(anio: int, mes: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    if not (1 <= mes <= 12 and 2000 <= anio <= 2100):
        raise HTTPException(422, "Periodo inválido")
    r = proceso.procesar_periodo(db, anio, mes, u.username)
    db.commit()
    return r


@router.post("/periodos/{anio}/{mes}/cerrar")
def cerrar(anio: int, mes: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    proceso.cerrar_periodo(db, anio, mes, u.username)
    db.commit()
    return {"estado": "CERRADO"}


class Reapertura(BaseModel):
    motivo: str


@router.post("/periodos/{anio}/{mes}/reabrir")
def reabrir(anio: int, mes: int, d: Reapertura, u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    proceso.reabrir_periodo(db, anio, mes, u.username, d.motivo)
    db.commit()
    return {"estado": "ABIERTO"}


@router.get("/asistencia/{anio}/{mes}")
def asistencia(anio: int, mes: int, empleado_id: int | None = None, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    ini, fin = proceso.rango_mes(anio, mes)
    q = select(AsistenciaDia).where(AsistenciaDia.fecha.between(ini, fin)).order_by(AsistenciaDia.fecha)
    if empleado_id:
        q = q.where(AsistenciaDia.empleado_id == empleado_id)
    return [{"empleado_id": a.empleado_id, "empleado": a.empleado.nombre_completo, "fecha": a.fecha.isoformat(),
             "estado": a.estado, "marcas": a.marcas, "min_retraso": a.min_retraso, "falta": float(a.falta),
             "justificado": float(a.justificado), "observacion": a.observacion}
            for a in db.execute(q).scalars().unique()]


@router.get("/liquidacion/{anio}/{mes}")
def liquidacion(anio: int, mes: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    from ..services.consultas import ORDEN_MOD
    ls = db.execute(select(Liquidacion).where(Liquidacion.anio == anio, Liquidacion.mes == mes)).scalars().unique().all()
    ls.sort(key=lambda l: (ORDEN_MOD[l.modalidad], l.empleado.apellidos))
    cols = ["haber_basico", "dias_trabajados", "bono_antiguedad", "total_ganado", "aporte_laboral", "aporte_patronal", "rc_iva",
            "dias_laborables", "dias_asistidos", "faltas", "min_retraso", "nro_retrasos", "dias_justificados", "dias_descuento",
            "desc_faltas", "desc_atrasos", "desc_otros", "desc_asistencia", "total_descuentos", "liquido_pagable"]
    return [{"empleado_id": l.empleado_id, "empleado": l.empleado.nombre_completo, "ci": l.empleado.ci_completo,
             "modalidad": l.modalidad, "sancion": l.sancion, "observacion": l.observacion,
             **{c: float(getattr(l, c)) for c in cols}} for l in ls]
