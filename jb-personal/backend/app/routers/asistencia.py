from __future__ import annotations

import json
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (AsistenciaDia, Empleado, ImportBiometrico, Liquidacion, Marca, PerfilBiometrico, Periodo,
                      Usuario)
from ..security import ESCRIBE, LEE, SOLO_ADMIN
from ..services import biometrico, proceso
from ..services.biometrico import _ident
from .deps import log

router = APIRouter(prefix="/api", tags=["asistencia"])


def _perfil_de(db: Session, perfil_id: int | None, config: str) -> tuple[dict | None, str]:
    """Perfil guardado (perfil_id) o configuración puntual (config JSON); None = autodetección."""
    if config.strip():
        try:
            return biometrico.validar_perfil(json.loads(config)), "manual"
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(422, f"Perfil inválido: {e}")
    if perfil_id:
        pf = db.get(PerfilBiometrico, perfil_id)
        if not pf:
            raise HTTPException(404, "Perfil no encontrado")
        return json.loads(pf.config), pf.nombre
    return None, ""


async def _leer(archivo: UploadFile) -> bytes:
    data = await archivo.read()
    if len(data) > 50_000_000:
        raise HTTPException(413, "Archivo demasiado grande")
    return data


@router.post("/biometrico/analizar")
async def analizar(archivo: UploadFile = File(...), orden_fecha: str = Form("dmy"), delimitador: str = Form("auto"),
                   u: Usuario = Depends(ESCRIBE)):
    """Detecta la estructura del archivo y devuelve una muestra + perfil sugerido para que el usuario lo ajuste."""
    try:
        return biometrico.analizar(archivo.filename or "marcas", await _leer(archivo), orden_fecha, delimitador)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/biometrico/probar")
async def probar(archivo: UploadFile = File(...), config: str = Form(...), u: Usuario = Depends(ESCRIBE)):
    """Aplica un perfil SIN guardar nada: devuelve las primeras marcas interpretadas y los rechazos."""
    try:
        pf = biometrico.validar_perfil(json.loads(config))
        formato, regs, rech = biometrico.parsear_con_perfil(archivo.filename or "marcas", await _leer(archivo), pf)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(422, str(e))
    return {"formato": formato, "total": len(regs), "rechazadas": len(rech), "detalle_rechazo": rech[:15],
            "ejemplo": [{"id": r.identificador, "fecha_hora": r.fecha_hora.isoformat(sep=" "), "tipo": r.tipo_evento}
                        for r in regs[:12]]}


@router.post("/biometrico/importar")
async def importar(archivo: UploadFile = File(...), orden_fecha: str = Form("dmy"), perfil_id: int | None = Form(None),
                   config: str = Form(""), u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    if orden_fecha not in ("dmy", "mdy", "ymd"):
        raise HTTPException(422, "orden_fecha debe ser dmy, mdy o ymd")
    data = await _leer(archivo)
    perfil, pnom = _perfil_de(db, perfil_id, config)
    try:
        lote = proceso.importar_biometrico(db, archivo.filename or "marcas", data, u.username, orden_fecha, perfil, pnom)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"lote": lote.id, "formato": lote.formato, "leidas": lote.leidas, "nuevas": lote.nuevas,
            "duplicadas": lote.duplicadas, "rechazadas": lote.rechazadas, "detalle_rechazo": lote.detalle_rechazo.splitlines()[:20]}


class PerfilIn(BaseModel):
    nombre: str
    marca: str = ""
    config: dict


@router.get("/biometrico/perfiles")
def perfiles(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [{"id": p.id, "nombre": p.nombre, "marca": p.marca, "config": json.loads(p.config)}
            for p in db.execute(select(PerfilBiometrico).order_by(PerfilBiometrico.nombre)).scalars()]


@router.post("/biometrico/perfiles")
def guardar_perfil(d: PerfilIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    try:
        cfg = biometrico.validar_perfil(d.config)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not d.nombre.strip():
        raise HTTPException(422, "Indique un nombre para el perfil")
    p = db.execute(select(PerfilBiometrico).where(PerfilBiometrico.nombre == d.nombre.strip())).scalars().first()
    if not p:
        p = PerfilBiometrico(nombre=d.nombre.strip())
        db.add(p)
    p.marca, p.config, p.creado_por = d.marca, json.dumps(cfg, ensure_ascii=False), u.username
    db.flush()
    log(db, u, "GUARDAR_PERFIL_BIOMETRICO", "perfil_biometrico", p.id, {"nombre": p.nombre, "marca": p.marca})
    db.commit()
    return {"id": p.id}


@router.delete("/biometrico/perfiles/{pid}")
def borrar_perfil(pid: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    p = db.get(PerfilBiometrico, pid)
    if p:
        db.delete(p)
        log(db, u, "ELIMINAR_PERFIL_BIOMETRICO", "perfil_biometrico", pid, {"nombre": p.nombre})
        db.commit()
    return {"ok": True}


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
    proceso.asegurar_actualizado(db, anio, mes, u.username)
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
    proceso.asegurar_actualizado(db, anio, mes, u.username)
    ls = db.execute(select(Liquidacion).where(Liquidacion.anio == anio, Liquidacion.mes == mes)).scalars().unique().all()
    ls.sort(key=lambda l: (ORDEN_MOD[l.modalidad], l.empleado.apellidos))
    cols = ["haber_basico", "dias_trabajados", "bono_antiguedad", "total_ganado", "aporte_laboral", "aporte_patronal", "rc_iva",
            "dias_laborables", "dias_asistidos", "faltas", "min_retraso", "nro_retrasos", "dias_justificados", "dias_descuento",
            "desc_faltas", "desc_atrasos", "desc_otros", "desc_multas", "desc_asistencia", "total_descuentos", "liquido_pagable",
            "dias_desc_faltas", "dias_desc_atrasos", "dias_desc_sin_goce", "dias_desc_exceso_consultor", "horas_permiso"]
    return [{"empleado_id": l.empleado_id, "empleado": l.empleado.nombre_completo, "ci": l.empleado.ci_completo,
             "modalidad": l.modalidad, "sancion": l.sancion, "observacion": l.observacion,
             **{c: float(getattr(l, c)) for c in cols}} for l in ls]
