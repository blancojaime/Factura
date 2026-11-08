from __future__ import annotations

import json
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (Empleado, Entidad, Instructivo, InstructivoDestinatario, Permiso, PermisoTipo, Usuario)
from ..security import ESCRIBE, LEE
from ..services import pdfs
from ..services.proceso import (ReglaNegocio, exigir_abierto, formato_cite, siguiente_correlativo, validar_permiso)
from .deps import log, reprocesar

router = APIRouter(prefix="/api", tags=["permisos"])


class PermisoIn(BaseModel):
    empleado_id: int
    tipo_codigo: str
    fecha_desde: date
    fecha_hasta: date
    hora_desde: time | None = None
    hora_hasta: time | None = None
    motivo: str = ""
    doc_respaldo: str = ""
    autorizado_por: str = ""
    gestion_vacacion: str = ""
    saldo_vacacion: str = ""
    aprobar: bool = False


def _p(p: Permiso):
    return {"id": p.id, "nro_boleta": p.nro_boleta, "empleado_id": p.empleado_id, "empleado": p.empleado.nombre_completo,
            "ci": p.empleado.ci_completo, "tipo_codigo": p.tipo_codigo, "tipo": p.tipo.nombre, "categoria": p.tipo.categoria,
            "con_goce": p.tipo.con_goce, "fecha_desde": p.fecha_desde.isoformat(), "fecha_hasta": p.fecha_hasta.isoformat(),
            "hora_desde": p.hora_desde.strftime("%H:%M") if p.hora_desde else None,
            "hora_hasta": p.hora_hasta.strftime("%H:%M") if p.hora_hasta else None, "motivo": p.motivo,
            "doc_respaldo": p.doc_respaldo, "estado": p.estado, "autorizado_por": p.autorizado_por,
            "gestion_vacacion": p.gestion_vacacion, "saldo_vacacion": p.saldo_vacacion}


@router.get("/permisos")
def listar(empleado_id: int | None = None, anio: int | None = None, mes: int | None = None, estado: str = "",
           u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    q = select(Permiso).order_by(Permiso.fecha_desde.desc(), Permiso.id.desc())
    if empleado_id:
        q = q.where(Permiso.empleado_id == empleado_id)
    if anio and mes:
        from ..services.proceso import rango_mes
        ini, fin = rango_mes(anio, mes)
        q = q.where(Permiso.fecha_desde <= fin, Permiso.fecha_hasta >= ini)
    if estado:
        q = q.where(Permiso.estado == estado)
    return [_p(p) for p in db.execute(q.limit(500)).scalars().unique()]


@router.post("/permisos")
def crear(d: PermisoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    emp, tipo = db.get(Empleado, d.empleado_id), db.get(PermisoTipo, d.tipo_codigo)
    if not emp or not tipo:
        raise HTTPException(404, "Empleado o tipo de permiso inexistente")
    exigir_abierto(db, d.fecha_desde)
    exigir_abierto(db, d.fecha_hasta)
    ent = db.get(Entidad, 1)
    n = siguiente_correlativo(db, "BOLETA", d.fecha_desde.year)
    p = Permiso(nro_boleta=formato_cite(ent.prefijo_cite, "BOL", n, d.fecha_desde.year), creado_por=u.username,
                estado="APROBADO" if d.aprobar else "PENDIENTE",
                **d.model_dump(exclude={"aprobar"}))
    validar_permiso(db, p, emp, tipo)
    db.add(p)
    db.flush()
    log(db, u, "CREAR_PERMISO", "permiso", p.id, {"boleta": p.nro_boleta, "estado": p.estado, "tipo": tipo.codigo,
                                                   "empleado": emp.ci})
    if p.estado == "APROBADO":
        reprocesar(db, u, [p.fecha_desde, p.fecha_hasta])
    db.commit()
    db.refresh(p)
    return _p(p)


def _cambiar(db, u, pid, estado, accion):
    p = db.get(Permiso, pid)
    if not p:
        raise HTTPException(404, "Permiso no encontrado")
    exigir_abierto(db, p.fecha_desde)
    exigir_abierto(db, p.fecha_hasta)
    prev = p.estado
    p.estado = estado
    if estado == "APROBADO":
        validar_permiso(db, p, p.empleado, p.tipo)
    log(db, u, accion, "permiso", p.id, {"boleta": p.nro_boleta, "de": prev, "a": estado})
    reprocesar(db, u, [p.fecha_desde, p.fecha_hasta])
    db.commit()
    return _p(p)


class Autoriza(BaseModel):
    autorizado_por: str = ""


@router.post("/permisos/{pid}/aprobar")
def aprobar(pid: int, a: Autoriza | None = None, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    p = db.get(Permiso, pid)
    if p and a and a.autorizado_por:
        p.autorizado_por = a.autorizado_por
    return _cambiar(db, u, pid, "APROBADO", "APROBAR_PERMISO")


@router.post("/permisos/{pid}/rechazar")
def rechazar(pid: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    return _cambiar(db, u, pid, "RECHAZADO", "RECHAZAR_PERMISO")


@router.post("/permisos/{pid}/anular")
def anular(pid: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    return _cambiar(db, u, pid, "ANULADO", "ANULAR_PERMISO")


@router.get("/permisos/{pid}/boleta.pdf")
def boleta(pid: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    p = db.get(Permiso, pid)
    if not p:
        raise HTTPException(404, "Permiso no encontrado")
    return Response(pdfs.boleta_pdf(p, db.get(Entidad, 1)), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{p.nro_boleta.replace("/", "-")}.pdf"'})


# ------------------------------------------------------------------ instructivos
class InstructivoIn(BaseModel):
    titulo: str = Field(min_length=3, max_length=250)
    contenido: str = Field(min_length=3)
    fecha_emision: date | None = None
    todos: bool = False
    empleados: list[int] = []
    unidades: list[int] = []
    cargos: list[str] = []
    modalidades: list[str] = []


def _resolver(db: Session, d: InstructivoIn) -> list[Empleado]:
    out: dict[int, Empleado] = {}
    activos = [e for e in db.execute(select(Empleado).where(Empleado.activo == True)).scalars().unique()]  # noqa: E712
    for e in activos:
        mod = e.contratos[-1].modalidad if e.contratos else None
        if (d.todos or e.id in d.empleados or e.unidad_id in d.unidades
                or any(c.lower() in e.cargo.lower() for c in d.cargos if c.strip())
                or (mod and mod in d.modalidades)):
            out[e.id] = e
    return list(out.values())


def _i(i: Instructivo, detalle=True):
    r = {"id": i.id, "cite": i.cite, "titulo": i.titulo, "fecha_emision": i.fecha_emision.isoformat(), "estado": i.estado,
         "n_destinatarios": len(i.destinatarios),
         "notificados": sum(1 for x in i.destinatarios if x.notificacion != "PENDIENTE")}
    if detalle:
        r["contenido"] = i.contenido
        r["criterio"] = json.loads(i.criterio or "{}")
        r["destinatarios"] = [{"id": x.id, "empleado": x.empleado.nombre_completo, "cargo": x.empleado.cargo,
                               "notificacion": x.notificacion, "observacion": x.observacion,
                               "fecha_notificacion": x.fecha_notificacion.isoformat() if x.fecha_notificacion else None}
                              for x in i.destinatarios]
    return r


@router.get("/instructivos")
def listar_inst(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [_i(i, False) for i in db.execute(select(Instructivo).order_by(Instructivo.id.desc())).scalars().unique()]


@router.post("/instructivos")
def crear_inst(d: InstructivoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    dest = _resolver(db, d)
    if not dest:
        raise HTTPException(422, "Los criterios no seleccionan ningún destinatario")
    ent = db.get(Entidad, 1)
    fe = d.fecha_emision or date.today()
    n = siguiente_correlativo(db, "INSTRUCTIVO", fe.year)
    i = Instructivo(cite=formato_cite(ent.prefijo_cite, "INST", n, fe.year), gestion=fe.year, correlativo=n, titulo=d.titulo,
                    contenido=d.contenido, fecha_emision=fe, creado_por=u.username,
                    criterio=json.dumps(d.model_dump(mode="json", exclude={"titulo", "contenido", "fecha_emision"})))
    i.destinatarios = [InstructivoDestinatario(empleado_id=e.id) for e in dest]
    db.add(i)
    db.flush()
    log(db, u, "CREAR_INSTRUCTIVO", "instructivo", i.id, {"cite": i.cite, "destinatarios": len(dest)})
    db.commit()
    return _i(i)


@router.get("/instructivos/{iid}")
def get_inst(iid: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    i = db.get(Instructivo, iid)
    if not i:
        raise HTTPException(404, "No encontrado")
    return _i(i)


@router.post("/instructivos/{iid}/emitir")
def emitir(iid: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    i = db.get(Instructivo, iid)
    if not i or i.estado != "BORRADOR":
        raise HTTPException(409, "Solo se puede emitir un instructivo en BORRADOR")
    i.estado = "EMITIDO"
    log(db, u, "EMITIR_INSTRUCTIVO", "instructivo", i.id, {"cite": i.cite})
    db.commit()
    return _i(i)


@router.post("/instructivos/{iid}/anular")
def anular_inst(iid: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    i = db.get(Instructivo, iid)
    if not i or i.estado == "ANULADO":
        raise HTTPException(409, "No se puede anular")
    i.estado = "ANULADO"     # el cite no se reutiliza
    log(db, u, "ANULAR_INSTRUCTIVO", "instructivo", i.id, {"cite": i.cite})
    db.commit()
    return _i(i)


class Notif(BaseModel):
    notificacion: str = Field(pattern="^(PENDIENTE|NOTIFICADO|RECIBIDO)$")
    observacion: str = ""


@router.put("/instructivos/{iid}/destinatarios/{did}")
def notificar(iid: int, did: int, n: Notif, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    x = db.get(InstructivoDestinatario, did)
    if not x or x.instructivo_id != iid:
        raise HTTPException(404, "Destinatario no encontrado")
    if x.instructivo.estado != "EMITIDO":
        raise HTTPException(409, "El instructivo debe estar EMITIDO para registrar notificaciones")
    x.notificacion, x.observacion = n.notificacion, n.observacion
    x.fecha_notificacion = datetime.now() if n.notificacion != "PENDIENTE" else None
    log(db, u, "NOTIFICAR_INSTRUCTIVO", "instructivo", iid, {"destinatario": x.empleado.ci, "estado": n.notificacion})
    db.commit()
    return {"ok": True}


@router.get("/instructivos/{iid}/pdf")
def pdf_inst(iid: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    i = db.get(Instructivo, iid)
    if not i:
        raise HTTPException(404, "No encontrado")
    return Response(pdfs.instructivo_pdf(i, db.get(Entidad, 1)), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{i.cite.replace("/", "-")}.pdf"'})
